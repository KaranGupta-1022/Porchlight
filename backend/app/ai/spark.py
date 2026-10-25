"""Grounded Spark prompts for nudges, editable drafts, and voice invite parsing."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, Field, ValidationError

from app.ai import provider
from app.models import Nudge, ParsedInvite


DEVELOPER_RULES = """You write for Porchlight, an app that helps neighbors meet in person.
Use ONLY the provided facts (names, interests, availability, cluster). Never invent facts about a person.
First steps must be low-pressure, public, and brief: a wave, a hello, or a short walk.
Never suggest entering someone's home or sharing an address.
Messages are warm and plain, at most three sentences, with no emojis unless the requested tone allows.
Output valid JSON matching the requested schema exactly. No markdown fences."""


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _member(value: Any) -> dict[str, Any]:
    member = _dict(value)
    return {k: member[k] for k in
            ("display_name", "interests", "availability", "cluster_id")
            if k in member}


def _json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _validate(text: str, model: type, keys: set[str]) -> Any:
    value = _json_object(text)
    if set(value) != keys:
        raise ValueError("unexpected JSON fields")
    return model.model_validate(value)


def _ask_json(messages: list[dict[str, str]], feature: str, fallback: dict[str, Any],
              model: type, keys: set[str], max_tokens: int = 500) -> tuple[Any, bool]:
    fallback_text = json.dumps(fallback, ensure_ascii=False)
    result = provider.complete(messages, feature=feature, fallback=fallback_text,
                               max_tokens=max_tokens, reasoning_effort="minimal")
    try:
        return _validate(str(result.value), model, keys), result.degraded
    except (ValueError, ValidationError, TypeError):
        if provider.ai_mode() == "live" and not result.degraded:
            retry_messages = [*messages, {"role": "developer", "content":
                                            "Return only valid JSON matching the requested schema exactly."}]
            retry = provider.complete(retry_messages, feature=feature,
                                      fallback=fallback_text, max_tokens=max_tokens,
                                      reasoning_effort="minimal")
            try:
                return _validate(str(retry.value), model, keys), retry.degraded
            except (ValueError, ValidationError, TypeError):
                pass
        return model.model_validate(fallback), True


def _nudge_fallback(you: dict[str, Any], candidate: dict[str, Any],
                    gap: dict[str, Any], mode: str) -> dict[str, Any]:
    canned = provider.fixture("nudge")
    name = str(candidate.get("display_name", "a neighbor"))
    cluster = str(gap.get("name", "this part of the community"))
    shared = sorted(set(you.get("interests", [])) & set(candidate.get("interests", [])))
    interests = " and ".join(shared[:2]) if shared else "a neighborhood connection"
    common_time = sorted(set(you.get("availability", [])) &
                         set(candidate.get("availability", [])))
    availability = (f" You are both free {common_time[0].replace('-', ' ')}."
                    if common_time else "")
    canned["headline"] = f"You haven't met anyone on {cluster} yet"
    canned["why"] = f"{name} also likes {interests}.{availability}" if shared else f"{name} lives near {cluster}.{availability}"
    canned["first_step"] = ("Invite them to a short walk in a public place."
                            if mode == "invite" else
                            "A wave and a hello in a public place is enough.")
    canned["cta"] = "Draft an invite" if mode == "invite" else "Draft a hello"
    canned["draft_message"] = (f"Hi {name}! I noticed we both like {interests}. "
                               "Would you like to take a short walk this week?"
                               if shared else f"Hi {name}! Would you like to say hello sometime this week?")
    return canned


def make_nudge(you: Any, candidate: Any, components: Mapping[str, float],
               gap_cluster: Any, mode: str = "small_ask") -> tuple[Nudge, bool]:
    you_facts = _member(you)
    candidate_facts = _member(candidate)
    gap = _dict(gap_cluster)
    fallback = _nudge_fallback(you_facts, candidate_facts, gap, mode)
    request = {"you": you_facts, "candidate": candidate_facts,
               "components": dict(components), "gap":
               {k: gap[k] for k in ("name", "size", "reach", "gap_score") if k in gap},
               "mode": mode,
               "schema": {k: "string" for k in Nudge.model_fields}}
    messages = [{"role": "developer", "content": DEVELOPER_RULES},
                {"role": "user", "content": "Create one grounded, low-pressure nudge. "
                 + json.dumps(request, ensure_ascii=False)}]
    return _ask_json(messages, "nudge", fallback, Nudge, set(Nudge.model_fields))


class DraftJSON(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


def draft_message(you: Any, recipient: Any, context: str = "",
                  tone: str = "casual") -> tuple[str, bool]:
    you_facts = _member(you)
    recipient_facts = _member(recipient)
    name = str(recipient_facts.get("display_name", "there"))
    shared = sorted(set(you_facts.get("interests", [])) &
                    set(recipient_facts.get("interests", [])))
    if shared:
        fallback = {"text": f"Hi {name}! I noticed we both like {shared[0]}. "
                            "Want to say hello sometime this week?"}
    else:
        fallback = {"text": f"Hi {name}! Want to say hello sometime this week?"}
    # The fixture sets the structure and serves as a no-key baseline; dynamic facts
    # avoid mentioning Priya when another fictional resident is selected.
    fallback = {**provider.fixture("draft"), **fallback}
    request = {"you": you_facts, "recipient": recipient_facts,
               "context_from_user": context[:500], "tone": tone,
               "schema": {"text": "string, at most three sentences"}}
    messages = [{"role": "developer", "content": DEVELOPER_RULES},
                {"role": "user", "content": "Draft an editable first message. "
                 + json.dumps(request, ensure_ascii=False)}]
    parsed, degraded = _ask_json(messages, "draft", fallback, DraftJSON, {"text"}, 500)
    if len(re.split(r"[.!?]+", parsed.text.strip())) - 1 > 3:
        return fallback["text"], True
    return parsed.text, degraded


def parse_invite(transcript: str, you: Any, now: datetime) -> tuple[ParsedInvite, bool]:
    fallback = provider.fixture("parse_invite")
    request = {"transcript": transcript[:1000], "host": _member(you),
               "now": now.isoformat(),
               "schema": {"title": "string", "activity": "string",
                          "starts_at": "ISO datetime", "capacity": "integer 1..100",
                          "place_hint": "public place, no exact address",
                          "confidence": "number 0..1"}}
    messages = [{"role": "developer", "content": DEVELOPER_RULES},
                {"role": "user", "content": "Parse the voice post into a draft invite. "
                 "Use only stated details; keep uncertain fields conservative. "
                 + json.dumps(request, ensure_ascii=False)}]
    return _ask_json(messages, "parse_invite", fallback, ParsedInvite,
                     set(ParsedInvite.model_fields))
