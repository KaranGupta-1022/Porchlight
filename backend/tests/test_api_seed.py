"""Phase 2 seed, reseed, and public location safety checks."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_connection, public_invite, public_member, reset_demo  # noqa: E402
from seed.generate_seed import generate  # noqa: E402


def _met_ids(connection, community_id: str) -> set[str]:
    you = connection.execute(
        "SELECT id FROM members WHERE community_id = ? AND is_demo_user = 1",
        (community_id,),
    ).fetchone()
    return {
        row[0] for row in connection.execute(
            """SELECT CASE WHEN a_id = ? THEN b_id ELSE a_id END
               FROM hangouts WHERE a_id = ? OR b_id = ?""",
            (you["id"], you["id"], you["id"]),
        )
    }


def test_generator_matches_committed_seed(tmp_path: Path) -> None:
    for generated in generate(tmp_path):
        committed = Path(__file__).resolve().parents[1] / "seed" / generated.name
        assert generated.read_bytes() == committed.read_bytes()
    hydepark = json.loads((tmp_path / "hydepark.json").read_text(encoding="utf-8"))
    quarry = json.loads((tmp_path / "quarry.json").read_text(encoding="utf-8"))
    assert len(hydepark["members"]) == 40
    assert len(quarry["members"]) == 30
    assert len(hydepark["invites"]) == 7
    assert len(quarry["invites"]) == 4


def test_planted_gap_ranks_first_under_guide_formula() -> None:
    seed_dir = Path(__file__).resolve().parents[1] / "seed"
    for filename, expected in [("hydepark.json", "Duval St"),
                               ("quarry.json", "South Wing")]:
        seed = json.loads((seed_dir / filename).read_text(encoding="utf-8"))
        you = next(m for m in seed["members"] if m["is_demo_user"])
        met = {
            h["b_id"] if h["a_id"] == you["id"] else h["a_id"]
            for h in seed["hangouts"]
            if you["id"] in (h["a_id"], h["b_id"])
        }
        scores = []
        for cluster in seed["clusters"]:
            people = [m for m in seed["members"]
                      if m["cluster_id"] == cluster["id"] and not m["is_demo_user"]]
            count = len(people)
            reach = sum(m["id"] in met for m in people) / count
            if reach >= 0.25 or count < 3:
                continue
            corners = cluster["polygon"]["coordinates"][0][:-1]
            lat = sum(point[1] for point in corners) / len(corners)
            lng = sum(point[0] for point in corners) / len(corners)
            distance = math.hypot((lat - you["lat"]) * 111.2,
                                  (lng - you["lng"]) * 96.3)
            scores.append((count * (1 - reach) / (1 + distance), cluster["name"]))
        assert max(scores)[1] == expected


def test_reset_restores_seed_and_planted_gaps(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    reset_demo(db_path)
    with get_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM communities").fetchone()[0] == 2
        assert len(_met_ids(connection, "hydepark")) == 6
        assert len(_met_ids(connection, "quarry")) == 5
        for community_id, gap_name in [("hydepark", "Duval St"),
                                       ("quarry", "South Wing")]:
            met = _met_ids(connection, community_id)
            gap = connection.execute(
                "SELECT id FROM clusters WHERE community_id = ? AND name = ?",
                (community_id, gap_name),
            ).fetchone()
            gap_members = connection.execute(
                "SELECT id FROM members WHERE cluster_id = ?", (gap["id"],)
            ).fetchall()
            assert gap_members
            assert all(row["id"] not in met for row in gap_members)
        connection.execute("DELETE FROM statuses WHERE id = 'hydepark-status-nora'")
    reset_demo(db_path)
    with get_connection(db_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM statuses WHERE id = 'hydepark-status-nora'"
        ).fetchone()[0] == 1


def test_public_serializers_hide_private_locations(tmp_path: Path) -> None:
    db_path = tmp_path / "demo.db"
    reset_demo(db_path)
    with get_connection(db_path) as connection:
        member = connection.execute(
            "SELECT * FROM members WHERE id = 'hydepark-priya'"
        ).fetchone()
        first = public_member(member)
        assert first == public_member(member)
        assert "unit_label" not in first
        assert "lat" in first and "lng" in first
        assert (first["lat"], first["lng"]) != (member["lat"], member["lng"])
        assert first["interests"] == ["dogs", "coffee", "board games", "gardening"]
        invite = connection.execute(
            "SELECT * FROM invites WHERE id = 'hydepark-dogwalk'"
        ).fetchone()
        public = public_invite(invite)
        assert "exact_location" not in public
        assert (public["lat"], public["lng"]) != (invite["lat"], invite["lng"])
