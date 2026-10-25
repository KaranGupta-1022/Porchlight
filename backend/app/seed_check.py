"""Print the initial Reach story for both seeded communities."""

from __future__ import annotations

import json
import math

from .db import get_connection, reset_demo


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dy = (lat1 - lat2) * 111.2
    dx = (lng1 - lng2) * 96.3
    return math.hypot(dx, dy)


def report() -> dict[str, list[dict]]:
    reset_demo()
    all_rows: dict[str, list[dict]] = {}
    with get_connection() as connection:
        communities = connection.execute("SELECT * FROM communities ORDER BY id").fetchall()
        for community in communities:
            you = connection.execute(
                "SELECT * FROM members WHERE community_id = ? AND is_demo_user = 1",
                (community["id"],),
            ).fetchone()
            if you is None:
                raise AssertionError(f"Missing demo user in {community['id']}")
            met_ids = {
                row["other_id"] for row in connection.execute(
                    """SELECT CASE WHEN a_id = ? THEN b_id ELSE a_id END AS other_id
                       FROM hangouts WHERE a_id = ? OR b_id = ?""",
                    (you["id"], you["id"], you["id"]),
                )
            }
            rows = []
            for cluster in connection.execute(
                "SELECT * FROM clusters WHERE community_id = ? ORDER BY name",
                (community["id"],),
            ):
                people = connection.execute(
                    "SELECT id FROM members WHERE cluster_id = ? AND is_demo_user = 0",
                    (cluster["id"],),
                ).fetchall()
                total = len(people)
                met = sum(person["id"] in met_ids for person in people)
                reach = met / total if total else 0.0
                corners = json.loads(cluster["polygon"])["coordinates"][0][:-1]
                lat = sum(point[1] for point in corners) / len(corners)
                lng = sum(point[0] for point in corners) / len(corners)
                gap_score = total * (1 - reach) / (1 + _distance_km(
                    you["lat"], you["lng"], lat, lng))
                rows.append({"name": cluster["name"], "met": met, "total": total,
                             "reach": round(reach, 4), "gap_score": round(gap_score, 4)})
            all_rows[community["id"]] = rows
    return all_rows


if __name__ == "__main__":
    for community_id, rows in report().items():
        print(f"{community_id}:")
        for row in rows:
            print(f"  {row['name']}: {row['met']}/{row['total']} "
                  f"({row['reach']:.0%}), gap score {row['gap_score']:.3f}")
        gap = "Duval St" if community_id == "hydepark" else "South Wing"
        assert next(row for row in rows if row["name"] == gap)["reach"] == 0.0
