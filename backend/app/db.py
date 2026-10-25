"""SQLite storage and the single public member serializer for the demo."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping


BACKEND_DIR = Path(__file__).resolve().parents[1]
SEED_DIR = BACKEND_DIR / "seed"
DEFAULT_DB_PATH = BACKEND_DIR / "porchlight.db"

SCHEMA = """
CREATE TABLE communities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('neighborhood', 'apartments')),
    center_lat REAL NOT NULL,
    center_lng REAL NOT NULL,
    zoom INTEGER NOT NULL
);
CREATE TABLE clusters (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id),
    name TEXT NOT NULL,
    polygon TEXT NOT NULL
);
CREATE TABLE members (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id),
    cluster_id TEXT NOT NULL REFERENCES clusters(id),
    display_name TEXT NOT NULL,
    emoji_avatar TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    unit_label TEXT NOT NULL,
    interests TEXT NOT NULL,
    availability TEXT NOT NULL,
    verified INTEGER NOT NULL,
    is_demo_user INTEGER NOT NULL
);
CREATE TABLE hangouts (
    id TEXT PRIMARY KEY,
    a_id TEXT NOT NULL REFERENCES members(id),
    b_id TEXT NOT NULL REFERENCES members(id),
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    CHECK (a_id <> b_id)
);
CREATE TABLE invites (
    id TEXT PRIMARY KEY,
    community_id TEXT NOT NULL REFERENCES communities(id),
    host_id TEXT NOT NULL REFERENCES members(id),
    title TEXT NOT NULL,
    activity TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    exact_location TEXT NOT NULL,
    place_hint TEXT NOT NULL,
    requires_approval INTEGER NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('manual', 'voice', 'muse'))
);
CREATE TABLE rsvps (
    id TEXT PRIMARY KEY,
    invite_id TEXT NOT NULL REFERENCES invites(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    status TEXT NOT NULL CHECK (status IN ('going', 'waitlist', 'pending_approval', 'cancelled')),
    position INTEGER,
    UNIQUE (invite_id, member_id)
);
CREATE TABLE statuses (
    id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL REFERENCES members(id),
    text TEXT NOT NULL,
    until TEXT NOT NULL
);
CREATE TABLE drafts (
    id TEXT PRIMARY KEY,
    from_id TEXT NOT NULL REFERENCES members(id),
    to_id TEXT NOT NULL REFERENCES members(id),
    nudge_json TEXT NOT NULL,
    draft_text TEXT NOT NULL,
    final_text TEXT,
    sent_at TEXT
);
CREATE TABLE api_usage (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    feature TEXT NOT NULL,
    model TEXT NOT NULL,
    in_tokens INTEGER NOT NULL,
    out_tokens INTEGER NOT NULL,
    seconds_audio REAL NOT NULL,
    usd REAL NOT NULL,
    cached INTEGER NOT NULL
);
CREATE INDEX idx_members_community ON members(community_id);
CREATE INDEX idx_hangouts_a ON hangouts(a_id);
CREATE INDEX idx_hangouts_b ON hangouts(b_id);
CREATE INDEX idx_invites_community ON invites(community_id);
CREATE INDEX idx_rsvps_invite_status ON rsvps(invite_id, status);
"""

DROP_ORDER = (
    "api_usage", "drafts", "statuses", "rsvps", "invites", "hangouts",
    "members", "clusters", "communities",
)


def database_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path or os.getenv("PORCHLIGHT_DB_PATH", DEFAULT_DB_PATH))


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def _insert_seed(connection: sqlite3.Connection, seed: dict[str, Any]) -> None:
    c = seed["community"]
    connection.execute(
        "INSERT INTO communities VALUES (?, ?, ?, ?, ?, ?)",
        (c["id"], c["name"], c["kind"], c["center_lat"], c["center_lng"], c["zoom"]),
    )
    for row in seed["clusters"]:
        connection.execute(
            "INSERT INTO clusters VALUES (?, ?, ?, ?)",
            (row["id"], row["community_id"], row["name"], json.dumps(row["polygon"])),
        )
    for row in seed["members"]:
        connection.execute(
            "INSERT INTO members VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["id"], row["community_id"], row["cluster_id"], row["display_name"],
             row["emoji_avatar"], row["lat"], row["lng"], row["unit_label"],
             json.dumps(row["interests"]), json.dumps(row["availability"]),
             int(row["verified"]), int(row["is_demo_user"])),
        )
    for row in seed["hangouts"]:
        connection.execute(
            "INSERT INTO hangouts VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["a_id"], row["b_id"], row["date"], row["kind"]),
        )
    for row in seed["invites"]:
        connection.execute(
            "INSERT INTO invites VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["id"], row["community_id"], row["host_id"], row["title"],
             row["activity"], row["starts_at"], row["capacity"], row["lat"],
             row["lng"], row["exact_location"], row["place_hint"],
             int(row["requires_approval"]), row["status"], row["source"]),
        )
    for row in seed.get("rsvps", []):
        connection.execute(
            "INSERT INTO rsvps VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["invite_id"], row["member_id"], row["status"], row["position"]),
        )
    for row in seed["statuses"]:
        connection.execute(
            "INSERT INTO statuses VALUES (?, ?, ?, ?)",
            (row["id"], row["member_id"], row["text"], row["until"]),
        )
    for row in seed.get("drafts", []):
        connection.execute(
            "INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row["id"], row["from_id"], row["to_id"], json.dumps(row["nudge_json"]),
             row["draft_text"], row.get("final_text"), row.get("sent_at")),
        )
    for row in seed.get("api_usage", []):
        connection.execute(
            "INSERT INTO api_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["id"], row["ts"], row["feature"], row["model"], row["in_tokens"],
             row["out_tokens"], row["seconds_audio"], row["usd"], int(row["cached"])),
        )


def reset_demo(db_path: str | Path | None = None) -> None:
    """Drop and reseed both communities. Called at app startup and by demo reset."""
    seeds = [json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))
             for name in ("hydepark", "quarry")]
    with closing(get_connection(db_path)) as connection:
        with connection:
            for table in DROP_ORDER:
                connection.execute(f"DROP TABLE IF EXISTS {table}")
            connection.executescript(SCHEMA)
            for seed in seeds:
                _insert_seed(connection, seed)


def fuzz_coordinates(lat: float, lng: float, stable_id: str) -> tuple[float, float]:
    """Snap to an approximately 100 m grid with ID-stable jitter below 10 m."""
    lat_step = 100 / 111_200
    lng_step = 100 / 96_300  # longitude scale near 30 degrees north
    digest = hashlib.blake2b(stable_id.encode("utf-8"), digest_size=8).digest()
    lat_jitter = ((int.from_bytes(digest[:4], "big") / 0xFFFFFFFF) - 0.5) * 0.00014
    lng_jitter = ((int.from_bytes(digest[4:], "big") / 0xFFFFFFFF) - 0.5) * 0.00016
    return (round(round(lat / lat_step) * lat_step + lat_jitter, 6),
            round(round(lng / lng_step) * lng_step + lng_jitter, 6))


def _data(row: Mapping[str, Any] | sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def public_member(row: Mapping[str, Any] | sqlite3.Row) -> dict[str, Any]:
    """Only route by which a database member becomes an API member response."""
    m = _data(row)
    lat, lng = fuzz_coordinates(float(m["lat"]), float(m["lng"]), m["id"])
    interests = m["interests"]
    availability = m["availability"]
    return {
        "id": m["id"], "community_id": m["community_id"],
        "cluster_id": m["cluster_id"], "display_name": m["display_name"],
        "emoji_avatar": m["emoji_avatar"], "lat": lat, "lng": lng,
        "interests": json.loads(interests) if isinstance(interests, str) else interests,
        "availability": json.loads(availability) if isinstance(availability, str) else availability,
        "verified": bool(m["verified"]), "is_demo_user": bool(m["is_demo_user"]),
    }


def public_invite(row: Mapping[str, Any] | sqlite3.Row, going_count: int = 0) -> dict[str, Any]:
    """Public invite fields; the host's exact location stays in SQLite."""
    item = _data(row)
    lat, lng = fuzz_coordinates(float(item["lat"]), float(item["lng"]), item["id"])
    return {
        "id": item["id"], "community_id": item["community_id"],
        "host_id": item["host_id"], "title": item["title"],
        "activity": item["activity"], "starts_at": item["starts_at"],
        "capacity": item["capacity"], "going_count": going_count,
        "lat": lat, "lng": lng, "place_hint": item["place_hint"],
        "requires_approval": bool(item["requires_approval"]),
        "status": item["status"], "source": item["source"],
    }
