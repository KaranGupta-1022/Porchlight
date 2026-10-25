"""Generate the two fictional, repeatable demo communities.

Run ``python -m seed.generate_seed`` from ``backend``. The fixed anchor date and
local RNG make the JSON byte-for-byte stable across runs.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


SEED_DIR = Path(__file__).resolve().parent
ANCHOR = date(2026, 10, 24)
CENTRAL = timezone(timedelta(hours=-5))
INTERESTS = [
    "dogs", "board games", "gardening", "running", "cooking", "live music",
    "chess", "kids", "bikes", "coffee", "film", "climbing", "books",
]
SLOTS = [
    "mon-evening", "tue-evening", "wed-evening", "thu-evening",
    "fri-evening", "sat-morning", "sat-afternoon", "sun-afternoon",
]


def polygon(lat: float, lng: float, height: float, width: float) -> dict:
    """A small GeoJSON street segment or building section."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [round(lng - width / 2, 6), round(lat - height / 2, 6)],
            [round(lng + width / 2, 6), round(lat - height / 2, 6)],
            [round(lng + width / 2, 6), round(lat + height / 2, 6)],
            [round(lng - width / 2, 6), round(lat + height / 2, 6)],
            [round(lng - width / 2, 6), round(lat - height / 2, 6)],
        ]],
    }


def cluster(community_id: str, slug: str, name: str, lat: float, lng: float,
            height: float, width: float) -> dict:
    return {
        "id": f"{community_id}-{slug}",
        "community_id": community_id,
        "name": name,
        "polygon": polygon(lat, lng, height, width),
        "center_lat": lat,
        "center_lng": lng,
    }


def member(rng: random.Random, community_id: str, name: str, cluster_data: dict,
           *, interests: list[str] | None = None,
           availability: list[str] | None = None,
           demo: bool = False, emoji: str | None = None) -> dict:
    slug = "you" if demo else name.lower().replace(" ", "-")
    lat = cluster_data["center_lat"] + rng.uniform(-0.00019, 0.00019)
    lng = cluster_data["center_lng"] + rng.uniform(-0.00016, 0.00016)
    return {
        "id": f"{community_id}-{slug}",
        "community_id": community_id,
        "cluster_id": cluster_data["id"],
        "display_name": name,
        "emoji_avatar": emoji or rng.choice(["🙂", "😎", "🌻", "🐕", "☕", "🎲", "🚲", "📚"]),
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "unit_label": f"Fictional residence {slug}",
        "interests": interests or rng.sample(INTERESTS, 2 + rng.randrange(2)),
        "availability": availability or rng.sample(SLOTS, 2 + rng.randrange(2)),
        "verified": True,
        "is_demo_user": demo,
    }


def distance_km(a: dict, b: dict) -> float:
    dy = (a["lat"] - b["lat"]) * 111.2
    dx = (a["lng"] - b["lng"]) * 96.3
    return math.hypot(dx, dy)


def compatibility(a: dict, b: dict) -> float:
    interests = len(set(a["interests"]) & set(b["interests"])) / max(
        1, len(set(a["interests"]) | set(b["interests"])))
    schedule = len(set(a["availability"]) & set(b["availability"])) / max(
        1, len(set(a["availability"]) | set(b["availability"])))
    proximity = 1 / (1 + distance_km(a, b))
    return 0.45 * interests + 0.25 * schedule + 0.30 * proximity


def generate_hangouts(rng: random.Random, members: list[dict], known_ids: list[str],
                      *, priya_id: str | None = None) -> list[dict]:
    """Sample an organic graph, then pin the demo user's six/five known edges."""
    community_id = members[0]["community_id"]
    you = next(m for m in members if m["is_demo_user"])
    other = [m for m in members if not m["is_demo_user"]]
    result: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add_pair(a: dict, b: dict, count: int) -> None:
        pair = tuple(sorted((a["id"], b["id"])))
        if pair in seen:
            return
        seen.add(pair)
        for i in range(count):
            days_ago = rng.randint(1, 60)
            result.append({
                "id": f"{community_id}-hangout-{len(result) + 1:03d}",
                "a_id": a["id"],
                "b_id": b["id"],
                "date": (ANCHOR - timedelta(days=days_ago)).isoformat(),
                "kind": rng.choice(["walk", "coffee", "board games", "chat", "garden swap"]),
            })

    by_id = {m["id"]: m for m in members}
    for known_id in known_ids:
        add_pair(you, by_id[known_id], 1 + rng.randrange(3))

    for i, a in enumerate(other):
        for b in other[i + 1:]:
            score = compatibility(a, b)
            if rng.random() < 0.015 + 0.09 * score:
                add_pair(a, b, 1 + int(score > 0.52) + int(rng.random() < 0.16))

    if priya_id:
        # A warm path to a known neighbor boosts Priya's bridge score.
        add_pair(by_id[priya_id], by_id[known_ids[0]], 1)
    return result


def invite(community_id: str, slug: str, host_id: str, title: str, activity: str,
           starts_at: str, capacity: int, lat: float, lng: float,
           place_hint: str, exact_location: str, requires_approval: bool = True) -> dict:
    return {
        "id": f"{community_id}-{slug}", "community_id": community_id,
        "host_id": host_id, "title": title, "activity": activity,
        "starts_at": starts_at, "capacity": capacity,
        "lat": lat, "lng": lng, "exact_location": exact_location,
        "place_hint": place_hint, "requires_approval": requires_approval,
        "status": "open", "source": "manual",
    }


def status(community_id: str, slug: str, member_id: str, text: str, until: str) -> dict:
    return {"id": f"{community_id}-status-{slug}", "member_id": member_id,
            "text": text, "until": until}


def build_hydepark(rng: random.Random) -> dict:
    cid = "hydepark"
    community = {"id": cid, "name": "Hyde Park", "kind": "neighborhood",
                 "center_lat": 30.305, "center_lng": -97.728, "zoom": 16}
    specs = [
        ("avenue-g", "Avenue G", 30.2995, -97.7325, 0.0018, 0.00045),
        ("avenue-f", "Avenue F", 30.3022, -97.7350, 0.0018, 0.00045),
        ("speedway", "Speedway", 30.3050, -97.7385, 0.0018, 0.00045),
        ("43rd", "43rd St", 30.3085, -97.7420, 0.00045, 0.0018),
        ("duval", "Duval St", 30.3004, -97.7271, 0.0024, 0.00045),
    ]
    clusters = [cluster(cid, *s) for s in specs]
    groups = [
        ["Marcus", "Elena", "Nora", "Caleb", "Tessa", "Owen", "Amara", "Felix"],
        ["Mina", "Jules", "Ravi", "Leah", "Theo", "Wren", "Iris", "Noah"],
        ["Samira", "Leo", "Cora", "Milo", "Ada", "Finn", "Lena", "Zoe"],
        ["Avery", "Juno", "Dev", "Mae", "Otis", "Nia", "Ezra", "Rose", "Benji"],
        ["Priya", "Sofia", "Dara", "Kian", "Luca", "Bela"],
    ]
    you = member(rng, cid, "You", clusters[0], interests=["dogs", "coffee", "board games", "gardening"],
                 availability=["wed-evening", "thu-evening", "sat-morning"], demo=True, emoji="🏡")
    members = [you]
    for group, cl in zip(groups, clusters):
        for name in group:
            if name == "Priya":
                members.append(member(rng, cid, name, cl,
                    interests=["dogs", "coffee", "board games", "gardening"],
                    availability=["wed-evening", "thu-evening", "sat-morning"], emoji="🐕"))
            else:
                members.append(member(rng, cid, name, cl))
    known = [f"{cid}-{name.lower()}" for name in ["Marcus", "Elena", "Mina", "Jules", "Samira", "Leo"]]
    hangouts = generate_hangouts(rng, members, known, priya_id=f"{cid}-priya")
    invites = [
        invite(cid, "boardgames", f"{cid}-marcus", "Porch board games", "board games", "2026-10-30T18:00:00-05:00", 4, 30.2995, -97.7325, "near Avenue G", "Fictional porch G-1"),
        invite(cid, "blockparty", f"{cid}-elena", "Saturday block party", "block party", "2026-10-31T17:00:00-05:00", 18, 30.2997, -97.7327, "Avenue G block", "Fictional Avenue G common area"),
        invite(cid, "dogwalk", f"{cid}-priya", "Evening dog walk", "dog walk", "2026-10-29T18:00:00-05:00", 6, 30.3004, -97.7271, "near Duval St", "Fictional Duval meeting corner"),
        invite(cid, "garden", f"{cid}-mina", "Garden swap", "gardening", "2026-10-28T11:00:00-05:00", 8, 30.3022, -97.7350, "near Avenue F", "Fictional garden F-2"),
        invite(cid, "coffee", f"{cid}-jules", "Coffee and chess", "chess", "2026-10-27T10:00:00-05:00", 5, 30.3021, -97.7352, "Avenue F corner", "Fictional cafe F-3"),
        invite(cid, "bikeride", f"{cid}-samira", "Easy bike loop", "bikes", "2026-10-28T17:30:00-05:00", 8, 30.3050, -97.7385, "near Speedway", "Fictional bike rack S-1"),
        invite(cid, "music", f"{cid}-avery", "Backyard acoustic hour", "live music", "2026-10-30T19:00:00-05:00", 10, 30.3085, -97.7420, "near 43rd St", "Fictional patio 43-1"),
    ]
    statuses = [
        status(cid, "nora", f"{cid}-nora", "Free for a short walk", "2026-10-30T20:00:00-05:00"),
        status(cid, "priya", f"{cid}-priya", "Free for a dog walk", "2026-10-29T19:00:00-05:00"),
        status(cid, "milo", f"{cid}-milo", "Up for coffee", "2026-10-28T18:00:00-05:00"),
        status(cid, "juno", f"{cid}-juno", "Free for a garden swap", "2026-10-30T14:00:00-05:00"),
    ]
    return {"community": community, "clusters": clusters, "members": members,
            "hangouts": hangouts, "invites": invites, "rsvps": [], "statuses": statuses,
            "drafts": [], "api_usage": []}


def build_quarry(rng: random.Random) -> dict:
    cid = "quarry"
    community = {"id": cid, "name": "The Quarry Lofts", "kind": "apartments",
                 "center_lat": 30.287, "center_lng": -97.745, "zoom": 18}
    specs = [
        ("north", "North Wing", 30.28722, -97.74523, 0.00025, 0.00032),
        ("south", "South Wing", 30.28677, -97.74521, 0.00025, 0.00032),
        ("floor5", "Floor 5", 30.28702, -97.74479, 0.00025, 0.00030),
        ("rooftop", "Rooftop crew", 30.28728, -97.74476, 0.00023, 0.00028),
    ]
    clusters = [cluster(cid, *s) for s in specs]
    groups = [
        ["Anika", "Cole", "Rhea", "Tobin", "Belle", "Nikhil", "Paz", "Yara"],
        ["Imani", "Hugo", "Dina", "Ren", "Kim", "Sasha", "Eli", "Bea"],
        ["Ari", "Cass", "Mira", "Tariq", "Penny", "Gus", "Nell"],
        ["Maren", "Sol", "Kit", "Uma", "June", "Ash"],
    ]
    you = member(rng, cid, "You", clusters[0], interests=["gaming", "cooking", "film", "study groups"],
                 availability=["wed-evening", "fri-evening", "sat-afternoon"], demo=True, emoji="🏢")
    members = [you]
    apartment_interests = ["study groups", "climbing", "gaming", "cooking", "film", "books", "coffee", "running"]
    for group, cl in zip(groups, clusters):
        for name in group:
            interests = rng.sample(apartment_interests, 2 + rng.randrange(2))
            if name == "Imani":
                interests = ["gaming", "cooking", "film", "study groups"]
            members.append(member(rng, cid, name, cl, interests=interests,
                availability=["wed-evening", "fri-evening", "sat-afternoon"] if name == "Imani" else None))
    known = [f"{cid}-{name.lower()}" for name in ["Anika", "Cole", "Rhea", "Ari", "Cass"]]
    hangouts = generate_hangouts(rng, members, known)
    invites = [
        invite(cid, "study", f"{cid}-anika", "Courtyard study break", "study group", "2026-10-28T16:00:00-05:00", 8, 30.2870, -97.7450, "courtyard", "Fictional Quarry courtyard"),
        invite(cid, "sunset", f"{cid}-maren", "Rooftop sunset", "rooftop meetup", "2026-10-29T18:15:00-05:00", 10, 30.2873, -97.7448, "rooftop common space", "Fictional rooftop deck"),
        invite(cid, "bookswap", f"{cid}-imani", "Laundry-room book swap", "book swap", "2026-10-27T19:00:00-05:00", 7, 30.2868, -97.7452, "South Wing common area", "Fictional laundry room S"),
        invite(cid, "movie", f"{cid}-ari", "Floor 5 movie night", "film", "2026-10-30T20:00:00-05:00", 7, 30.2870, -97.7448, "Floor 5 lounge", "Fictional Floor 5 lounge"),
    ]
    statuses = [
        status(cid, "cole", f"{cid}-cole", "Free for a study break", "2026-10-29T18:00:00-05:00"),
        status(cid, "imani", f"{cid}-imani", "Up for a quick game", "2026-10-29T21:00:00-05:00"),
        status(cid, "maren", f"{cid}-maren", "Around for sunset", "2026-10-30T19:00:00-05:00"),
    ]
    return {"community": community, "clusters": clusters, "members": members,
            "hangouts": hangouts, "invites": invites, "rsvps": [], "statuses": statuses,
            "drafts": [], "api_usage": []}


def generate(output_dir: Path = SEED_DIR) -> tuple[Path, Path]:
    rng = random.Random(42)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = output_dir / "hydepark.json", output_dir / "quarry.json"
    for path, data in zip(paths, [build_hydepark(rng), build_quarry(rng)]):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


if __name__ == "__main__":
    for path in generate():
        print(path)
