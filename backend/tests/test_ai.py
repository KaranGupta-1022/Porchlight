"""Mock AI contracts, defensive parsing, and cost accounting."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from app.ai import provider, spark, voice
from app.db import get_connection, reset_demo


YOU = {"display_name": "You", "interests": ["dogs", "coffee"],
       "availability": ["wed-evening"], "cluster_id": "avenue-g"}
PRIYA = {"display_name": "Priya", "interests": ["dogs", "coffee"],
         "availability": ["wed-evening"], "cluster_id": "duval"}
GAP = {"name": "Duval St", "size": 8, "reach": 0, "gap_score": 1.0}


def test_mock_contracts_without_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    nudge, degraded = spark.make_nudge(YOU, PRIYA, {"interest": 1}, GAP)
    assert not degraded
    assert "Priya" in nudge.why
    assert "your place" not in nudge.first_step.lower()
    draft, degraded = spark.draft_message(YOU, PRIYA)
    assert not degraded and "Priya" in draft
    transcript, degraded = voice.transcribe(b"", "audio/webm")
    assert not degraded and "board games" in transcript
    parsed, degraded = spark.parse_invite(transcript, YOU,
                                          datetime(2026, 10, 24, tzinfo=timezone.utc))
    assert not degraded and parsed.capacity == 4


def test_invalid_json_retried_once_then_fallback(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    calls = []

    def invalid(messages, **kwargs):
        calls.append(messages)
        return provider.ProviderResult("not JSON")

    monkeypatch.setattr(provider, "complete", invalid)
    nudge, degraded = spark.make_nudge(YOU, PRIYA, {}, GAP)
    assert degraded and nudge.headline
    assert len(calls) == 2
    assert "Return only valid JSON" in calls[1][-1]["content"]


def test_fenced_json_is_accepted(monkeypatch):
    monkeypatch.setenv("AI_MODE", "live")
    canned = provider.fixture("nudge")
    import json

    monkeypatch.setattr(provider, "complete", lambda *a, **k:
                        provider.ProviderResult("```json\n" + json.dumps(canned) + "\n```"))
    result, degraded = spark.make_nudge(YOU, PRIYA, {}, GAP)
    assert not degraded and result.headline == canned["headline"]


def test_cost_cap_returns_degraded_without_call(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("COST_CAP_USD", "0")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "demo.db"))
    result = provider.complete([{"role": "user", "content": "hello"}],
                               feature="nudge", fallback="offline")
    assert result.degraded and result.value == "offline"
    assert provider.usage_summary().cost_cap_usd == 0


def test_demo_reset_preserves_spend(monkeypatch, tmp_path):
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "demo.db"))
    reset_demo()
    provider._record("nudge", "test-model", usd=0.75)
    reset_demo()
    assert provider.total_spend() == 0.75


def test_live_response_is_metered_then_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("META_MODEL_API_KEY", "unit-test-only")
    monkeypatch.setenv("COST_CAP_USD", "40")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "demo.db"))
    reset_demo()
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15.0 and kwargs["max_retries"] == 0
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="five words from Spark today"))],
                usage=SimpleNamespace(model_dump=lambda: {
                    "prompt_tokens": 100, "completion_tokens": 20}),
            )

    import openai
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    messages = [{"role": "user", "content": "five words"}]
    first = provider.complete(messages, feature="smoke", fallback="offline", max_tokens=40)
    second = provider.complete(messages, feature="smoke", fallback="offline", max_tokens=40)
    assert len(calls) == 1
    assert first.value == second.value and not second.degraded
    summary = provider.usage_summary()
    assert summary.by_feature[0].cache_hits == 1
    assert summary.by_feature[0].calls == 2
    assert summary.total_usd > 0
    with get_connection() as conn:
        ids = [row[0] for row in conn.execute("SELECT id FROM api_usage")]
    assert all(UUID(value).version == 4 for value in ids)


def test_voice_uses_documented_batch_request_and_audio_meter(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_MODE", "live")
    monkeypatch.setenv("META_MODEL_API_KEY", "unit-test-only")
    monkeypatch.setenv("COST_CAP_USD", "40")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "demo.db"))
    reset_demo()
    monkeypatch.setattr(provider, "_wav_bytes", lambda _: (b"wav-data", 10.0))
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"transcript": "Walk the dogs at six", "audioDurationMs": 10_000}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["timeout"] == 15.0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            requests.append((url, kwargs))
            return FakeResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", FakeClient)
    first = provider.transcribe(b"browser-audio", "audio/webm")
    second = provider.transcribe(b"browser-audio", "audio/webm")
    assert first.value == second.value == "Walk the dogs at six"
    assert len(requests) == 1
    url, options = requests[0]
    assert url.endswith("/asr/transcribe")
    assert options["files"]["request"][2] == "application/json"
    assert options["files"]["audio"][2] == "audio/wav"
    assert provider.usage_summary().by_feature[0].cache_hits == 1
    assert provider.usage_summary().total_usd == 0.0005


def test_mock_ai_routes_work_without_key(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    with TestClient(app) as client:
        nudge = client.get("/api/communities/hydepark/nudge")
        assert nudge.status_code == 200, nudge.text
        target = nudge.json()["candidate"]["id"]
        draft = client.post("/api/drafts", json={"community_id": "hydepark", "to_id": target})
        assert draft.status_code == 200, draft.text
        assert draft.json()["text"]
        voice_preview = client.post(
            "/api/voice/invite", data={"community_id": "hydepark"},
            files={"audio": ("sample.webm", b"mock-only", "audio/webm")},
        )
        assert voice_preview.status_code == 200, voice_preview.text
        assert voice_preview.json()["parsed"]["capacity"] == 4
        assert client.get("/api/usage").json()["total_usd"] == 0
