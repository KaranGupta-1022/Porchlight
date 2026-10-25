"""Reach, gaps, and bridge scoring over a seeded connection graph."""

from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

import networkx as nx


_interest_vectors: dict[str, tuple[float, ...]] = {}
_embedding_mode = "overlap"


def _as_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return dict(row)


def _list(value: Any) -> list[str]:
    return json.loads(value) if isinstance(value, str) else list(value)


def _polygon(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else value


def _by_id(members: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {m["id"]: _as_dict(m) for m in members}


def edge_strength(hangout_dates: list[date], today: date,
                  half_life_days: float = 30) -> float:
    """The guide's 30-day exponential decay (30 is the time constant)."""
    return sum(math.exp(-(today - day).days / half_life_days)
               for day in hangout_dates)


def build_graph(members: Sequence[Mapping[str, Any]],
                hangouts: Sequence[Mapping[str, Any]],
                today: date | None = None) -> nx.Graph:
    """Build weighted edges. Dates are evaluated once for a consistent response."""
    today = today or date.today()
    graph = nx.Graph()
    graph.graph["today"] = today
    for row in members:
        member = _as_dict(row)
        graph.add_node(member["id"], member=member)
    grouped: dict[tuple[str, str], list[date]] = defaultdict(list)
    for row in hangouts:
        item = _as_dict(row)
        day = item["date"]
        if isinstance(day, str):
            day = date.fromisoformat(day)
        grouped[tuple(sorted((item["a_id"], item["b_id"])))].append(day)
    for (a_id, b_id), dates in grouped.items():
        graph.add_edge(a_id, b_id, strength=edge_strength(dates, today),
                       hangout_count=len(dates), dates=dates)
    return graph


def reach(graph: nx.Graph, members: Sequence[Mapping[str, Any]], you_id: str,
          community_id: str | None = None,
          clusters: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Counts unique neighbors met, excluding the demo user from denominators."""
    people = [_as_dict(m) for m in members]
    you = next(m for m in people if m["id"] == you_id)
    community_id = community_id or you["community_id"]
    others = [m for m in people if m["community_id"] == community_id
              and m["id"] != you_id]
    met_ids = set(graph.neighbors(you_id)) if you_id in graph else set()
    met = sum(m["id"] in met_ids for m in others)
    names = {c["id"]: c["name"] for c in (clusters or [])}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for member in others:
        groups[member["cluster_id"]].append(member)
    if clusters is not None:
        cluster_ids = [c["id"] for c in clusters if c["community_id"] == community_id]
    else:
        cluster_ids = sorted(groups)
    cluster_rows = []
    for cluster_id in cluster_ids:
        group = groups[cluster_id]
        cluster_met = sum(m["id"] in met_ids for m in group)
        cluster_rows.append({
            "cluster_id": cluster_id, "name": names.get(cluster_id, cluster_id),
            "met": cluster_met, "total": len(group),
            "ratio": round(cluster_met / len(group), 4) if group else 0.0,
        })
    return {
        "community_id": community_id, "met": met, "total": len(others),
        "ratio": round(met / len(others), 4) if others else 0.0,
        "clusters": cluster_rows,
    }


def _centroid(cluster: Mapping[str, Any]) -> tuple[float, float]:
    ring = _polygon(cluster["polygon"])["coordinates"][0]
    vertices = ring[:-1] if ring[0] == ring[-1] else ring
    return (sum(point[1] for point in vertices) / len(vertices),
            sum(point[0] for point in vertices) / len(vertices))


def _distance_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    return math.hypot((a_lat - b_lat) * 111.2, (a_lng - b_lng) * 96.3)


def find_gaps(graph: nx.Graph, members: Sequence[Mapping[str, Any]],
              clusters: Sequence[Mapping[str, Any]], you_id: str) -> list[dict[str, Any]]:
    """Rank seeded clusters with Reach below 25% and at least three members."""
    people = _by_id(members)
    you = people[you_id]
    cluster_reach = {c["cluster_id"]: c for c in
                     reach(graph, members, you_id, clusters=clusters)["clusters"]}
    results = []
    for cluster in clusters:
        if cluster["community_id"] != you["community_id"]:
            continue
        info = cluster_reach[cluster["id"]]
        size = info["total"]
        ratio = info["ratio"]
        if ratio >= 0.25 or size < 3:
            continue
        lat, lng = _centroid(cluster)
        proximity_weight = 1 / (1 + _distance_km(you["lat"], you["lng"], lat, lng))
        results.append({
            "cluster_id": cluster["id"], "name": cluster["name"],
            "size": size, "reach": ratio,
            "gap_score": round(size * (1 - ratio) * proximity_weight, 4),
        })
    return sorted(results, key=lambda row: (-row["gap_score"], row["cluster_id"]))


def prime_interest_embeddings(members: Sequence[Mapping[str, Any]],
                              model_dir: str | Path | None = None) -> bool:
    """Load cached MiniLM once. No model download happens in this module."""
    global _embedding_mode
    model_name = str(model_dir or os.getenv("MINILM_MODEL_DIR", "sentence-transformers/all-MiniLM-L6-v2"))
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, local_files_only=True)
        people = [_as_dict(member) for member in members]
        texts = [", ".join(_list(member["interests"])) for member in people]
        vectors = model.encode(texts, normalize_embeddings=True)
        _interest_vectors.clear()
        _interest_vectors.update({member["id"]: tuple(float(n) for n in vector)
                                  for member, vector in zip(people, vectors)})
        _embedding_mode = "minilm"
        return True
    except (OSError, RuntimeError, ImportError, ValueError):
        _interest_vectors.clear()
        _embedding_mode = "overlap"
        return False


def embedding_mode() -> str:
    return _embedding_mode


def _interest_sim(a: dict[str, Any], b: dict[str, Any]) -> float:
    if a["id"] in _interest_vectors and b["id"] in _interest_vectors:
        va, vb = _interest_vectors[a["id"]], _interest_vectors[b["id"]]
        return max(0.0, min(1.0, sum(x * y for x, y in zip(va, vb))))
    first, second = set(_list(a["interests"])), set(_list(b["interests"]))
    return len(first & second) / len(first | second) if first | second else 0.0


def _schedule_overlap(a: dict[str, Any], b: dict[str, Any]) -> float:
    first, second = set(_list(a["availability"])), set(_list(b["availability"]))
    return len(first & second) / len(first | second) if first | second else 0.0


def bridge_candidates(graph: nx.Graph, members: Sequence[Mapping[str, Any]],
                      clusters: Sequence[Mapping[str, Any]], you_id: str,
                      gaps: Sequence[Mapping[str, Any]] | None = None,
                      limit: int = 3) -> list[dict[str, Any]]:
    """Rank unmet neighbors with the guide's 0.40/0.25/0.20/0.15 weights."""
    people = _by_id(members)
    you = people[you_id]
    met_ids = set(graph.neighbors(you_id)) if you_id in graph else set()
    if gaps is None:
        gaps = find_gaps(graph, members, clusters, you_id)
    top_gap_id = gaps[0]["cluster_id"] if gaps else None
    scored = []
    for candidate in people.values():
        if candidate["community_id"] != you["community_id"]:
            continue
        if candidate["id"] == you_id or candidate["id"] in met_ids:
            continue
        candidate_neighbors = set(graph.neighbors(candidate["id"]))
        components = {
            "interest_sim": _interest_sim(you, candidate),
            "schedule_overlap": _schedule_overlap(you, candidate),
            "gap_bonus": float(candidate["cluster_id"] == top_gap_id),
            "warm_path": float(bool(met_ids & candidate_neighbors)),
        }
        components["score"] = (
            0.40 * components["interest_sim"]
            + 0.25 * components["schedule_overlap"]
            + 0.20 * components["gap_bonus"]
            + 0.15 * components["warm_path"]
        )
        scored.append({"member_id": candidate["id"], "components": components})
    return sorted(scored, key=lambda item: (-item["components"]["score"],
                                            item["member_id"]))[:limit]
