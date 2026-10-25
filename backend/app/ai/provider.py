"""Single gateway for Meta calls, caching, fallback, and usage accounting."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import sqlite3
import subprocess
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from contextlib import closing
from importlib.metadata import PackageNotFoundError, version
from urllib.parse import urlsplit

from dotenv import load_dotenv

from app.db import get_connection
from app.models import UsageFeature, UsageResponse


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env", override=False)
LOG = logging.getLogger(__name__)
_CATALOG_DIAGNOSTIC_DONE = False
_CATALOG_DIAGNOSTIC_LOCK = Lock()


@dataclass(frozen=True)
class ProviderResult:
    value: Any
    degraded: bool = False
    usage: dict[str, Any] | None = None


def ai_mode() -> str:
    return "live" if os.getenv("AI_MODE", "mock").lower() == "live" else "mock"


def cost_cap() -> float:
    try:
        return max(0.0, min(float(os.getenv("COST_CAP_USD", "40")), 40.0))
    except ValueError:
        return 40.0


def _price(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _usage_db() -> sqlite3.Connection:
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS api_usage (
        id TEXT PRIMARY KEY, ts TEXT NOT NULL, feature TEXT NOT NULL,
        model TEXT NOT NULL, in_tokens INTEGER NOT NULL, out_tokens INTEGER NOT NULL,
        seconds_audio REAL NOT NULL, usd REAL NOT NULL, cached INTEGER NOT NULL)"""
    )
    conn.commit()
    return conn


def _record(feature: str, model: str, *, in_tokens: int = 0,
            out_tokens: int = 0, seconds_audio: float = 0.0,
            usd: float = 0.0, cached: bool = False) -> None:
    with closing(_usage_db()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO api_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), datetime.now(timezone.utc).isoformat(), feature,
                 model, in_tokens, out_tokens, seconds_audio, usd, int(cached)),
            )


def total_spend() -> float:
    with closing(_usage_db()) as conn:
        row = conn.execute("SELECT COALESCE(SUM(usd), 0) FROM api_usage").fetchone()
    return float(row[0])


def usage_summary() -> UsageResponse:
    with closing(_usage_db()) as conn:
        rows = conn.execute(
            "SELECT feature, SUM(usd), COUNT(*), SUM(cached) "
            "FROM api_usage GROUP BY feature ORDER BY feature"
        ).fetchall()
    return UsageResponse(
        total_usd=total_spend(), cost_cap_usd=cost_cap(),
        by_feature=[UsageFeature(feature=r[0], usd=float(r[1]), calls=int(r[2]),
                                 cache_hits=int(r[3])) for r in rows],
    )


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _cache_path(model: str, messages: list[dict[str, Any]],
                params: dict[str, Any]) -> Path:
    key = json.dumps({"model": model, "messages": messages, "params": params},
                     sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    cache_dir = Path(os.getenv("AI_CACHE_DIR", ROOT / "backend" / "cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{digest}.json"


def _read_cache(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(path: Path, value: dict[str, Any]) -> None:
    temp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _fallback(feature: str, model: str, fallback: Any,
              path: Path | None = None) -> ProviderResult:
    cached = _read_cache(path) if path else None
    if cached is not None:
        _record(feature, model, cached=True)
        return ProviderResult(cached["value"], degraded=True, usage=cached.get("usage"))
    return ProviderResult(fallback, degraded=True)


def _reserve_estimate(messages: list[dict[str, Any]], max_tokens: int) -> float:
    # Conservative enough to avoid crossing the cap for ordinary demo prompts.
    chars = len(json.dumps(messages, default=str))
    input_tokens = max(1, chars // 3)
    return (input_tokens * _price("PRICE_IN_PER_M", 0.10)
            + max_tokens * _price("PRICE_OUT_PER_M", 0.20)) / 1_000_000


def _expected_meta_base(value: str) -> bool:
    """Check the configured endpoint without exposing its URL in logs."""
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return False
    return (parsed.scheme == "https" and parsed.hostname == "api.meta.ai"
            and parsed.path.rstrip("/") == "/v1" and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment)


def _quoted(value: str) -> bool:
    return len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')


def _sdk_version() -> str:
    try:
        return version("openai")
    except PackageNotFoundError:
        return "unavailable"


def _chat_path_expected(error: Exception) -> bool | None:
    url = getattr(getattr(error, "request", None), "url", None)
    if url is None:
        return None
    try:
        return urlsplit(str(url)).path.rstrip("/") == "/v1/chat/completions"
    except ValueError:
        return False


def _model_not_found_code(error: Exception) -> bool | None:
    code = getattr(error, "code", None)
    if code is None:
        body = getattr(error, "body", None)
        if isinstance(body, dict):
            nested = body.get("error")
            code = nested.get("code") if isinstance(nested, dict) else body.get("code")
    return code == "model_not_found" if isinstance(code, str) else None


def _log_model_catalog_once(client: Any) -> None:
    """Probe model access once after a Spark 404; never log catalog contents."""
    global _CATALOG_DIAGNOSTIC_DONE
    with _CATALOG_DIAGNOSTIC_LOCK:
        if _CATALOG_DIAGNOSTIC_DONE:
            return
        _CATALOG_DIAGNOSTIC_DONE = True
    try:
        catalog = client.models.list()
        ids = {item.id for item in catalog.data if isinstance(getattr(item, "id", None), str)}
        LOG.warning(
            "Meta model catalog status=ok contributor_listed=%s standard_listed=%s",
            "muse-spark-1.3-contributor" in ids, "muse-spark-1.3" in ids,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        LOG.warning(
            "Meta model catalog status=%s contributor_listed=unknown "
            "standard_listed=unknown error_class=%s",
            status if isinstance(status, int) else "unknown", type(exc).__name__,
        )


def complete(messages: list[dict[str, Any]], *, feature: str,
             fallback: str, max_tokens: int = 300,
             model: str | None = None,
             reasoning_effort: str = "minimal") -> ProviderResult:
    """Return raw Spark text. A caller may validate JSON and retry once."""
    raw_model = model or os.getenv("MUSE_SPARK_MODEL", "muse-spark-1.3-contributor")
    model = raw_model.strip()
    params: dict[str, Any] = {"max_tokens": max_tokens,
                              "reasoning_effort": reasoning_effort}
    path = _cache_path(model, messages, params)
    if ai_mode() == "mock":
        return ProviderResult(fallback)
    cached = _read_cache(path)
    if cached is not None:
        _record(feature, model, cached=True)
        return ProviderResult(cached["value"], usage=cached.get("usage"))
    if total_spend() + _reserve_estimate(messages, max_tokens) >= cost_cap():
        LOG.warning("Meta cost cap reached for %s", feature)
        return _fallback(feature, model, fallback, path)
    key = os.getenv("META_MODEL_API_KEY", "").strip()
    if not key:
        LOG.warning("Meta key unavailable for %s", feature)
        return _fallback(feature, model, fallback, path)
    client = None
    try:
        from openai import OpenAI

        base_url = os.getenv("META_API_BASE", "https://api.meta.ai/v1").strip()
        client = OpenAI(api_key=key,
                        base_url=base_url,
                        timeout=15.0, max_retries=0)
        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
        value = response.choices[0].message.content or ""
        usage_obj = response.usage
        usage = usage_obj.model_dump() if usage_obj is not None else {}
        if usage.get("prompt_tokens") is None or usage.get("completion_tokens") is None:
            # Keep the cap conservative if a compatible endpoint omits usage.
            usage = {**usage,
                     "prompt_tokens": max(1, len(json.dumps(messages)) // 3),
                     "completion_tokens": max_tokens,
                     "estimated": True}
        in_tokens = int(usage["prompt_tokens"])
        out_tokens = int(usage["completion_tokens"])
        usd = (in_tokens * _price("PRICE_IN_PER_M", 0.10)
               + out_tokens * _price("PRICE_OUT_PER_M", 0.20)) / 1_000_000
        _record(feature, model, in_tokens=in_tokens, out_tokens=out_tokens, usd=usd)
        if not value.strip():
            LOG.warning("Meta returned no visible text for %s", feature)
            return _fallback(feature, model, fallback, path)
        _write_cache(path, {"value": value, "usage": usage})
        return ProviderResult(value, usage=usage)
    except Exception as exc:
        if getattr(exc, "status_code", None) == 404:
            LOG.warning(
                "Meta Spark HTTP 404 feature=%s model_expected=%s "
                "model_outer_whitespace=%s model_quote_wrapped=%s base_expected=%s "
                "chat_path_expected=%s sdk_version=%s key_present=%s "
                "model_not_found_code=%s",
                feature, model == "muse-spark-1.3-contributor",
                raw_model != model, _quoted(model),
                _expected_meta_base(os.getenv("META_API_BASE", "https://api.meta.ai/v1")),
                _chat_path_expected(exc), _sdk_version(),
                bool(key), _model_not_found_code(exc),
            )
            if client is not None:
                _log_model_catalog_once(client)
        else:
            LOG.warning("Meta request failed for %s: %s", feature, type(exc).__name__)
        return _fallback(feature, model, fallback, path)


def _wav_bytes(audio_bytes: bytes) -> tuple[bytes, float]:
    """Convert browser audio to 24 kHz mono 16-bit PCM WAV with ffmpeg."""
    pcm = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-ac", "1", "-ar", "24000", "-acodec", "pcm_s16le", "-f", "s16le", "pipe:1"],
        input=audio_bytes, capture_output=True, timeout=15, check=True,
    ).stdout
    if not pcm:
        raise ValueError("empty converted audio")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24_000)
        wav.writeframes(pcm)
    return output.getvalue(), len(pcm) / 48_000


def transcribe(audio_bytes: bytes, mime_type: str) -> ProviderResult:
    """Batch Muse Voice request. Network and price accounting remain here."""
    fallback = fixture("transcript")["transcript"]
    model = "muse-voice-transcribe-1.0"
    if ai_mode() == "mock":
        return ProviderResult(fallback)
    # Voice caching is keyed by a content digest, the model, and conversion params.
    digest = hashlib.sha256(audio_bytes).hexdigest()
    path = _cache_path(model, [{"audio_sha256": digest}],
                       {"audioEncoding": "WAV", "mime_type": mime_type})
    cached = _read_cache(path)
    if cached is not None:
        _record("voice", model, cached=True)
        return ProviderResult(cached["value"], usage=cached.get("usage"))
    key = os.getenv("META_MODEL_API_KEY", "").strip()
    if not key or total_spend() >= cost_cap():
        LOG.warning("Voice unavailable or cost cap reached")
        return _fallback("voice", model, fallback, path)
    try:
        wav, seconds = _wav_bytes(audio_bytes)
        estimated = seconds / 60 * _price("PRICE_VOICE_PER_MIN", 0.003)
        if total_spend() + estimated >= cost_cap():
            return _fallback("voice", model, fallback, path)
        import httpx

        request = {"mode": "PUSH_TO_TALK", "model": model, "audioEncoding": "WAV"}
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                os.getenv("META_API_BASE", "https://api.meta.ai/v1").rstrip("/")
                + "/asr/transcribe",
                headers={"Authorization": f"Bearer {key}"},
                files={"request": (None, json.dumps(request), "application/json"),
                       "audio": ("recording.wav", wav, "audio/wav")},
            )
            response.raise_for_status()
            data = response.json()
        transcript = str(data["transcript"]).strip()
        if not transcript:
            raise ValueError("empty transcript")
        billed_seconds = float(data.get("audioDurationMs", seconds * 1000)) / 1000
        usd = billed_seconds / 60 * _price("PRICE_VOICE_PER_MIN", 0.003)
        _record("voice", model, seconds_audio=billed_seconds, usd=usd)
        usage = {"audioDurationMs": data.get("audioDurationMs")}
        _write_cache(path, {"value": transcript, "usage": usage})
        return ProviderResult(transcript, usage=usage)
    except Exception as exc:
        LOG.warning("Voice request failed: %s", type(exc).__name__)
        return _fallback("voice", model, fallback, path)
