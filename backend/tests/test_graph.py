"""Checks for the graph's demo story and guide formulas."""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph import (  # noqa: E402
    bridge_candidates,
    build_graph,
    edge_strength,
    find_gaps,
    reach,
)


def _seed(name: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "seed" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_edge_strength_uses_exact_30_day_exponential() -> None:
    today = date(2026, 10, 24)
    assert math.isclose(edge_strength([today], today), 1.0)
    assert math.isclose(edge_strength([date(2026, 9, 24)], today), math.exp(-1))
    assert math.isclose(edge_strength([today, date(2026, 9, 24)], today),
                        1 + math.exp(-1))


def test_planted_reach_and_gap_order() -> None:
    for name, expected_gap, expected_met in (
        ("hydepark", "Duval St", 6), ("quarry", "South Wing", 5)
    ):
        seed = _seed(name)
        graph = build_graph(seed["members"], seed["hangouts"], date(2026, 10, 24))
        you_id = f"{name}-you"
        stats = reach(graph, seed["members"], you_id, clusters=seed["clusters"])
        assert stats["met"] == expected_met
        gap = next(c for c in stats["clusters"] if c["name"] == expected_gap)
        assert gap["met"] == 0 and gap["ratio"] == 0
        assert find_gaps(graph, seed["members"], seed["clusters"], you_id)[0]["name"] == expected_gap


def test_hangout_adds_line_strength_and_reach() -> None:
    seed = _seed("hydepark")
    before_graph = build_graph(seed["members"], seed["hangouts"], date(2026, 10, 24))
    before = reach(before_graph, seed["members"], "hydepark-you", clusters=seed["clusters"])
    seed["hangouts"].append({
        "id": "new", "a_id": "hydepark-you", "b_id": "hydepark-priya",
        "date": "2026-10-24", "kind": "walk",
    })
    after_graph = build_graph(seed["members"], seed["hangouts"], date(2026, 10, 24))
    after = reach(after_graph, seed["members"], "hydepark-you", clusters=seed["clusters"])
    assert before["met"] == 6 and after["met"] == 7
    duval = next(c for c in after["clusters"] if c["name"] == "Duval St")
    assert duval["met"] == 1 and math.isclose(duval["ratio"], 1 / 6, abs_tol=0.0001)
    assert after_graph["hydepark-you"]["hydepark-priya"]["strength"] == 1.0


def test_priya_is_top_bridge_candidate_and_met_neighbors_are_excluded() -> None:
    seed = _seed("hydepark")
    graph = build_graph(seed["members"], seed["hangouts"], date(2026, 10, 24))
    candidates = bridge_candidates(graph, seed["members"], seed["clusters"],
                                   "hydepark-you", limit=40)
    assert candidates[0]["member_id"] == "hydepark-priya"
    assert len(candidates) == 33
    met = set(graph.neighbors("hydepark-you"))
    assert not met.intersection(item["member_id"] for item in candidates)
    assert math.isclose(candidates[0]["components"]["score"], 1.0)
