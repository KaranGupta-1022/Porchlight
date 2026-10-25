"""The complete P0 loop in mock mode with no API key or external delivery."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_connection  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_MODE", "mock")
    monkeypatch.setenv("PORCHLIGHT_DB_PATH", str(tmp_path / "porchlight.db"))
    monkeypatch.setenv("MINILM_MODEL_DIR", str(tmp_path / "missing-minilm"))
    with TestClient(app) as test_client:
        yield test_client


def test_map_reach_gaps_and_location_safety(client: TestClient) -> None:
    assert client.get("/api/health").json()["ai_mode"] == "mock"
    communities = client.get("/api/communities").json()["communities"]
    assert [item["id"] for item in communities] == ["hydepark", "quarry"]
    map_response = client.get("/api/communities/hydepark/map")
    assert map_response.status_code == 200
    map_data = map_response.json()
    assert len(map_data["members"]) == 40
    assert len(map_data["invites"]) == 7
    assert "unit_label" not in str(map_data)
    assert "exact_location" not in str(map_data)
    with get_connection() as connection:
        raw = connection.execute("SELECT * FROM members WHERE id = 'hydepark-priya'").fetchone()
        public = next(m for m in map_data["members"] if m["id"] == raw["id"])
        assert (public["lat"], public["lng"]) != (raw["lat"], raw["lng"])
    reach = client.get("/api/communities/hydepark/reach").json()
    assert (reach["met"], reach["total"]) == (6, 39)
    duval = next(row for row in reach["clusters"] if row["name"] == "Duval St")
    assert (duval["met"], duval["total"], duval["ratio"]) == (0, 6, 0.0)
    assert client.get("/api/communities/hydepark/gaps").json()["gaps"][0]["name"] == "Duval St"
    assert client.get("/api/communities/quarry/gaps").json()["gaps"][0]["name"] == "South Wing"


def test_nudge_draft_human_send_and_mark_met(client: TestClient) -> None:
    nudge = client.get("/api/communities/hydepark/nudge?mode=small_ask")
    assert nudge.status_code == 200
    assert nudge.json()["candidate"]["display_name"] == "Priya"
    assert nudge.json()["gap"]["name"] == "Duval St"
    draft = client.post("/api/drafts", json={
        "community_id": "hydepark", "to_id": "hydepark-priya",
        "context": "dog walk", "tone": "casual",
    })
    assert draft.status_code == 200
    draft_data = draft.json()
    assert draft_data["to_member"]["display_name"] == "Priya"
    assert client.get("/api/communities/hydepark/reach").json()["met"] == 6
    sent = client.post(f"/api/drafts/{draft_data['id']}/send",
                       json={"final_text": "Hi Priya! Walk the block with me?"})
    assert sent.status_code == 200
    assert sent.json()["final_text"] == "Hi Priya! Walk the block with me?"
    assert client.post(f"/api/drafts/{draft_data['id']}/send",
                       json={"final_text": "again"}).status_code == 409
    hangout = client.post("/api/hangouts", json={
        "community_id": "hydepark", "member_id": "hydepark-priya", "kind": "walk",
    })
    assert hangout.status_code == 200
    before, after = hangout.json()["before"], hangout.json()["after"]
    assert (before["met"], after["met"]) == (6, 7)
    assert next(row for row in after["clusters"] if row["name"] == "Duval St")["ratio"] == 0.1667
    assert hangout.json()["edge"]["hangout_count"] == 1


def test_voice_is_preview_until_human_posts_then_reset(client: TestClient) -> None:
    original = client.get("/api/communities/hydepark/map").json()["invites"]
    preview = client.post("/api/voice/invite", data={"community_id": "hydepark"},
                          files={"audio": ("sample.webm", b"fake-audio", "audio/webm")})
    assert preview.status_code == 200
    parsed = preview.json()["parsed"]
    assert parsed["title"]
    assert len(client.get("/api/communities/hydepark/map").json()["invites"]) == len(original)
    posted = client.post("/api/invites", json={
        "community_id": "hydepark", "title": parsed["title"],
        "activity": parsed["activity"], "starts_at": parsed["starts_at"],
        "capacity": parsed["capacity"], "place_hint": parsed["place_hint"],
        "source": "voice",
    })
    assert posted.status_code == 200
    assert posted.json()["source"] == "voice"
    assert "exact_location" not in posted.json()
    assert len(client.get("/api/communities/hydepark/map").json()["invites"]) == len(original) + 1
    assert client.post("/api/demo/reset").json() == {"reset": True}
    assert len(client.get("/api/communities/hydepark/map").json()["invites"]) == len(original)


def test_docs_validation_cors_and_missing_resources(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/api/health", "/api/communities", "/api/communities/{community_id}/map",
                 "/api/communities/{community_id}/reach",
                 "/api/communities/{community_id}/gaps",
                 "/api/communities/{community_id}/nudge", "/api/drafts",
                 "/api/drafts/{draft_id}/send", "/api/hangouts",
                 "/api/voice/invite", "/api/invites", "/api/demo/reset", "/api/usage"):
        assert path in paths
    assert client.get("/docs").status_code == 200
    assert client.get("/api/communities/unknown/map").status_code == 404
    assert client.post("/api/drafts/no-such-draft/send", json={"final_text": "hello"}).status_code == 404
    assert client.post("/api/drafts", json={
        "community_id": "hydepark", "to_id": "hydepark-priya", "tone": "invalid",
    }).status_code == 422
    assert client.post("/api/invites", json={
        "community_id": "hydepark", "title": "Board games", "activity": "board games",
        "starts_at": "2026-10-30T18:00:00-05:00", "capacity": 4,
        "place_hint": "123 Avenue G",
    }).status_code == 422
    assert client.get("/api/health", headers={"Origin": "https://not-porchlight.example"}).headers.get(
        "access-control-allow-origin") is None
    usage = client.get("/api/usage")
    assert usage.status_code == 200
    assert usage.json()["cost_cap_usd"] == 40.0


@pytest.mark.parametrize("field,address", [
    ("place_hint", "101 W 43rd Street"),
    ("title", "500 E 6th St"),
    ("activity", "1800 Duval"),
])
def test_invite_rejects_numbered_street_addresses(
    client: TestClient, field: str, address: str,
) -> None:
    payload = {
        "community_id": "hydepark", "title": "Board games", "activity": "board games",
        "starts_at": "2026-10-30T18:00:00-05:00", "capacity": 4,
        "place_hint": "near Avenue G",
    }
    payload[field] = address
    response = client.post("/api/invites", json=payload)
    assert response.status_code == 422
