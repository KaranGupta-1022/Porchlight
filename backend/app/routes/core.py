"""P0 API routes for the fictional, single-user Porchlight demo."""

from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..ai import provider, spark, voice
from ..db import get_connection, public_invite, public_member, reset_demo
from ..graph import bridge_candidates, build_graph, find_gaps, reach
from ..models import (
    CommunitiesResponse, CreateInviteRequest, DraftRequest, DraftResponse, Gap,
    GapsResponse, HangoutRequest, HangoutResponse, HealthResponse, Invite,
    MapResponse, NudgeResponse, ReachResponse, ResetResponse, SendDraftRequest,
    SentDraftResponse, UsageResponse, VoiceInviteResponse,
)


router = APIRouter(prefix="/api")
PRIVATE_LOCATION_PATTERN = re.compile(
    r"(?:\b\d{1,5}\s+(?:[A-Za-z0-9-]+\s+){0,3}"
    r"(?:St(?:reet)?|Ave(?:nue)?|Rd|Road|Dr(?:ive)?|Ln|Lane|Blvd|Court|Ct)\b)"
    r"|(?:\b\d{1,5}\s+(?:(?:N|S|E|W|NE|NW|SE|SW)\.?\s+)?"
    r"[A-Za-z][A-Za-z0-9'-]{2,}\b)"
    r"|(?:#\s*\d+\b)|(?:\b(?:apt|apartment|unit|suite)\s*[#-]?\s*\w+\b)",
    re.IGNORECASE,
)


def _fetch_community(connection: sqlite3.Connection, community_id: str) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM communities WHERE id = ?", (community_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Community not found")
    return dict(row)


def _fetch_member(connection: sqlite3.Connection, member_id: str,
                  community_id: str | None = None) -> sqlite3.Row:
    if community_id is None:
        row = connection.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    else:
        row = connection.execute(
            "SELECT * FROM members WHERE id = ? AND community_id = ?",
            (member_id, community_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return row


def _demo_user(connection: sqlite3.Connection, community_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM members WHERE community_id = ? AND is_demo_user = 1",
        (community_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Demo user not found")
    return row


def _clusters(connection: sqlite3.Connection, community_id: str) -> list[dict[str, Any]]:
    return [
        {"id": row["id"], "community_id": row["community_id"],
         "name": row["name"], "polygon": json.loads(row["polygon"])}
        for row in connection.execute(
            "SELECT * FROM clusters WHERE community_id = ? ORDER BY rowid",
            (community_id,),
        )
    ]


def _graph_state(connection: sqlite3.Connection, community_id: str):
    rows = connection.execute(
        "SELECT * FROM members WHERE community_id = ? ORDER BY rowid",
        (community_id,),
    ).fetchall()
    members = []
    for row in rows:
        member = dict(row)
        member["interests"] = json.loads(member["interests"])
        member["availability"] = json.loads(member["availability"])
        member["verified"] = bool(member["verified"])
        member["is_demo_user"] = bool(member["is_demo_user"])
        members.append(member)
    hangouts = [dict(row) for row in connection.execute(
        """SELECT h.* FROM hangouts AS h
           JOIN members AS a ON a.id = h.a_id
           WHERE a.community_id = ? ORDER BY h.rowid""",
        (community_id,),
    )]
    clusters = _clusters(connection, community_id)
    graph = build_graph(members, hangouts)
    return graph, members, clusters, hangouts


def _reach(connection: sqlite3.Connection, community_id: str) -> dict[str, Any]:
    graph, members, clusters, _ = _graph_state(connection, community_id)
    you = _demo_user(connection, community_id)
    return reach(graph, members, you["id"], community_id=community_id, clusters=clusters)


def _edge_rows(hangouts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[date]] = defaultdict(list)
    for row in hangouts:
        key = tuple(sorted((row["a_id"], row["b_id"])))
        grouped[key].append(date.fromisoformat(row["date"][:10]))
    today = date.today()
    return [
        {"a_id": a, "b_id": b,
         "strength": round(sum(math.exp(-(today - when).days / 30) for when in dates), 4),
         "hangout_count": len(dates)}
        for (a, b), dates in sorted(grouped.items())
    ]


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {"status": "ok", "ai_mode": provider.ai_mode(),
            "spend_usd": provider.total_spend()}


@router.get("/communities", response_model=CommunitiesResponse)
def communities() -> dict[str, Any]:
    with closing(get_connection()) as connection:
        rows = connection.execute("SELECT * FROM communities ORDER BY rowid").fetchall()
        return {"communities": [dict(row) for row in rows]}


@router.get("/communities/{community_id}/map", response_model=MapResponse)
def community_map(community_id: str) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        community = _fetch_community(connection, community_id)
        clusters = _clusters(connection, community_id)
        members = [public_member(row) for row in connection.execute(
            "SELECT * FROM members WHERE community_id = ? ORDER BY rowid", (community_id,)
        )]
        invite_rows = connection.execute(
            """SELECT i.*, COUNT(r.id) AS going_count FROM invites AS i
               LEFT JOIN rsvps AS r ON r.invite_id = i.id AND r.status = 'going'
               WHERE i.community_id = ? GROUP BY i.id ORDER BY i.rowid""",
            (community_id,),
        ).fetchall()
        invites = [public_invite(row, row["going_count"]) for row in invite_rows]
        statuses = [dict(row) for row in connection.execute(
            """SELECT s.* FROM statuses AS s JOIN members AS m ON m.id = s.member_id
               WHERE m.community_id = ? ORDER BY s.rowid""",
            (community_id,),
        )]
        _, _, _, hangouts = _graph_state(connection, community_id)
        return {"community": community, "clusters": clusters, "members": members,
                "invites": invites, "statuses": statuses,
                "edges": _edge_rows(hangouts)}


@router.get("/communities/{community_id}/reach", response_model=ReachResponse)
def community_reach(community_id: str) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, community_id)
        return _reach(connection, community_id)


@router.get("/communities/{community_id}/gaps", response_model=GapsResponse)
def community_gaps(community_id: str) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, community_id)
        graph, members, clusters, _ = _graph_state(connection, community_id)
        you = _demo_user(connection, community_id)
        return {"community_id": community_id,
                "gaps": find_gaps(graph, members, clusters, you["id"])}


@router.get("/communities/{community_id}/nudge", response_model=NudgeResponse)
def community_nudge(community_id: str,
                    mode: Literal["small_ask", "invite"] = "small_ask") -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, community_id)
        graph, members, clusters, _ = _graph_state(connection, community_id)
        you = _demo_user(connection, community_id)
        gaps = find_gaps(graph, members, clusters, you["id"])
        candidates = bridge_candidates(graph, members, clusters, you["id"], gaps=gaps, limit=3)
        if not candidates:
            raise HTTPException(status_code=404, detail="No bridge candidate available")
        selected = candidates[0]
        person = _fetch_member(connection, selected["member_id"], community_id)
        gap = next((g for g in gaps if g["cluster_id"] == person["cluster_id"]),
                   gaps[0] if gaps else None)
        if gap is None:
            raise HTTPException(status_code=404, detail="No gap available")
        public_you = public_member(you)
        public_candidate = public_member(person)
        nudge, degraded = spark.make_nudge(public_you, public_candidate,
                                           selected["components"], gap, mode=mode)
        return {"candidate": public_candidate, "components": selected["components"],
                "gap": gap, "nudge": nudge, "degraded": degraded}


@router.post("/drafts", response_model=DraftResponse)
def create_draft(request: DraftRequest) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, request.community_id)
        you = _demo_user(connection, request.community_id)
        recipient = _fetch_member(connection, request.to_id, request.community_id)
        if recipient["id"] == you["id"]:
            raise HTTPException(status_code=422, detail="Cannot draft a message to yourself")
        public_to = public_member(recipient)
        text, degraded = spark.draft_message(
            public_member(you), public_to, context=request.context, tone=request.tone)
        draft_id = f"draft-{uuid.uuid4().hex[:12]}"
        with connection:
            connection.execute(
                """INSERT INTO drafts
                   (id, from_id, to_id, nudge_json, draft_text, final_text, sent_at)
                   VALUES (?, ?, ?, ?, ?, NULL, NULL)""",
                (draft_id, you["id"], recipient["id"],
                 json.dumps({"context": request.context, "tone": request.tone}), text),
            )
        return {"id": draft_id, "to_member": public_to,
                "text": text, "degraded": degraded}


@router.post("/drafts/{draft_id}/send", response_model=SentDraftResponse)
def send_draft(draft_id: str, request: SendDraftRequest) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        draft = connection.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft not found")
        if draft["sent_at"] is not None:
            raise HTTPException(status_code=409, detail="Draft already sent")
        sent_at = datetime.now(timezone.utc).isoformat()
        with connection:
            connection.execute(
                "UPDATE drafts SET final_text = ?, sent_at = ? WHERE id = ? AND sent_at IS NULL",
                (request.final_text, sent_at, draft_id),
            )
        return {"id": draft_id, "final_text": request.final_text, "sent_at": sent_at}


@router.post("/hangouts", response_model=HangoutResponse)
def mark_hangout(request: HangoutRequest) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, request.community_id)
        you = _demo_user(connection, request.community_id)
        other = _fetch_member(connection, request.member_id, request.community_id)
        if other["id"] == you["id"]:
            raise HTTPException(status_code=422, detail="Cannot mark yourself as met")
        before = _reach(connection, request.community_id)
        with connection:
            connection.execute(
                "INSERT INTO hangouts (id, a_id, b_id, date, kind) VALUES (?, ?, ?, ?, ?)",
                (f"hangout-{uuid.uuid4().hex[:12]}", you["id"], other["id"],
                 date.today().isoformat(), request.kind),
            )
        after = _reach(connection, request.community_id)
        dates = [row["date"] for row in connection.execute(
            """SELECT date FROM hangouts
               WHERE (a_id = ? AND b_id = ?) OR (a_id = ? AND b_id = ?)""",
            (you["id"], other["id"], other["id"], you["id"]),
        )]
        strength = sum(math.exp(-(date.today() - date.fromisoformat(d[:10])).days / 30)
                       for d in dates)
        return {"edge": {"a_id": you["id"], "b_id": other["id"],
                         "strength": round(strength, 4), "hangout_count": len(dates)},
                "before": before, "after": after}


@router.post("/voice/invite", response_model=VoiceInviteResponse)
async def voice_invite(community_id: str = Form(...), audio: UploadFile = File(...)) -> dict[str, Any]:
    with closing(get_connection()) as connection:
        _fetch_community(connection, community_id)
        you = public_member(_demo_user(connection, community_id))
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Audio file is empty")
    transcript, voice_degraded = voice.transcribe(audio_bytes, audio.content_type or "application/octet-stream")
    parsed, parse_degraded = spark.parse_invite(transcript, you, datetime.now(timezone.utc))
    return {"transcript": transcript, "parsed": parsed,
            "degraded": voice_degraded or parse_degraded}


@router.post("/invites", response_model=Invite)
def create_invite(request: CreateInviteRequest) -> dict[str, Any]:
    if any(PRIVATE_LOCATION_PATTERN.search(value)
           for value in (request.title, request.activity, request.place_hint)):
        raise HTTPException(status_code=422, detail="Use block-level locations in public fields")
    with closing(get_connection()) as connection:
        _fetch_community(connection, request.community_id)
        you = _demo_user(connection, request.community_id)
        invite_id = f"invite-{uuid.uuid4().hex[:12]}"
        item = {
            "id": invite_id, "community_id": request.community_id,
            "host_id": you["id"], "title": request.title,
            "activity": request.activity, "starts_at": request.starts_at.isoformat(),
            "capacity": request.capacity, "lat": you["lat"], "lng": you["lng"],
            "exact_location": "Fictional host location, shared after approval",
            "place_hint": request.place_hint,
            "requires_approval": int(request.requires_approval),
            "status": "open", "source": request.source,
        }
        with connection:
            connection.execute(
                """INSERT INTO invites
                   (id, community_id, host_id, title, activity, starts_at, capacity,
                    lat, lng, exact_location, place_hint, requires_approval, status, source)
                   VALUES (:id, :community_id, :host_id, :title, :activity, :starts_at,
                           :capacity, :lat, :lng, :exact_location, :place_hint,
                           :requires_approval, :status, :source)""",
                item,
            )
        return public_invite(item)


@router.post("/demo/reset", response_model=ResetResponse)
def reset() -> dict[str, bool]:
    reset_demo()
    return {"reset": True}


@router.get("/usage", response_model=UsageResponse)
def usage() -> UsageResponse:
    return provider.usage_summary()
