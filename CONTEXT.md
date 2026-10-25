# Porchlight — context for coding sessions (read first)

Thesis: show people the neighbors they've reached and the ones they haven't,
then let Muse make the next hello easy.

Hard rules:
- Only build what's in the current scope tier. P0 before P1 before P2.
- All AI calls go through backend/app/ai/provider.py (mock/live/cache/cost meter).
  Never call the Meta API from anywhere else. Never from the frontend.
- The AI drafts messages; the human always sends. Never auto-send.
- Locations are fuzzed to block level. Exact addresses only after host approval.
- One schema for both communities. Differences live in seed files only.
- Prefer boring, working code over clever code. No new dependencies without a reason.

## Data contracts

The complete Pydantic response and request schemas are reproduced below from backend/app/models.py. Keep changes in both places synchronized.

```python
"""Shared REST contracts for the demo. Public models never contain home addresses."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Community(BaseModel):
    id: str
    name: str
    kind: Literal["neighborhood", "apartments"]
    center_lat: float
    center_lng: float
    zoom: int


class CommunitiesResponse(BaseModel):
    communities: list[Community]


class Cluster(BaseModel):
    id: str
    community_id: str
    name: str
    polygon: dict[str, Any]


class PublicMember(BaseModel):
    id: str
    community_id: str
    cluster_id: str
    display_name: str
    emoji_avatar: str
    lat: float
    lng: float
    interests: list[str]
    availability: list[str]
    verified: bool
    is_demo_user: bool


class Edge(BaseModel):
    a_id: str
    b_id: str
    strength: float
    hangout_count: int


class Invite(BaseModel):
    id: str
    community_id: str
    host_id: str
    title: str
    activity: str
    starts_at: datetime
    capacity: int
    going_count: int = 0
    lat: float
    lng: float
    place_hint: str
    requires_approval: bool
    status: str
    source: Literal["manual", "voice", "muse"]


class MemberStatus(BaseModel):
    id: str
    member_id: str
    text: str
    until: datetime


class MapResponse(BaseModel):
    community: Community
    clusters: list[Cluster]
    members: list[PublicMember]
    invites: list[Invite]
    statuses: list[MemberStatus]
    edges: list[Edge]


class ClusterReach(BaseModel):
    cluster_id: str
    name: str
    met: int
    total: int
    ratio: float


class ReachResponse(BaseModel):
    community_id: str
    met: int
    total: int
    ratio: float
    clusters: list[ClusterReach]


class Gap(BaseModel):
    cluster_id: str
    name: str
    size: int
    reach: float
    gap_score: float


class GapsResponse(BaseModel):
    community_id: str
    gaps: list[Gap]


class Nudge(BaseModel):
    headline: str
    why: str
    first_step: str
    cta: str
    draft_message: str


class NudgeResponse(BaseModel):
    candidate: PublicMember
    components: dict[str, float]
    gap: Gap
    nudge: Nudge
    degraded: bool = False


class DraftRequest(BaseModel):
    community_id: str
    to_id: str
    context: str = ""
    tone: Literal["casual", "warmer", "shorter"] = "casual"


class DraftResponse(BaseModel):
    id: str
    to_member: PublicMember
    text: str
    degraded: bool = False


class SendDraftRequest(BaseModel):
    final_text: str = Field(min_length=1, max_length=1000)


class SentDraftResponse(BaseModel):
    id: str
    final_text: str
    sent_at: datetime


class HangoutRequest(BaseModel):
    community_id: str
    member_id: str
    kind: str = "walk"


class HangoutResponse(BaseModel):
    edge: Edge
    before: ReachResponse
    after: ReachResponse


class ParsedInvite(BaseModel):
    title: str
    activity: str
    starts_at: datetime
    capacity: int = Field(ge=1, le=100)
    place_hint: str
    confidence: float = Field(ge=0, le=1)


class VoiceInviteResponse(BaseModel):
    transcript: str
    parsed: ParsedInvite
    degraded: bool = False


class CreateInviteRequest(BaseModel):
    community_id: str
    title: str
    activity: str
    starts_at: datetime
    capacity: int = Field(ge=1, le=100)
    place_hint: str
    requires_approval: bool = True
    source: Literal["manual", "voice", "muse"] = "manual"


class JoinResponse(BaseModel):
    rsvp_id: str
    status: Literal["going", "waitlist", "pending_approval"]
    position: int | None = None


class CancelResponse(BaseModel):
    cancelled: bool
    promoted_rsvp_id: str | None = None


class ApproveResponse(BaseModel):
    rsvp_id: str
    status: Literal["going"]
    exact_location: str


class ResetResponse(BaseModel):
    reset: bool


class UsageFeature(BaseModel):
    feature: str
    usd: float
    calls: int
    cache_hits: int


class UsageResponse(BaseModel):
    total_usd: float
    cost_cap_usd: float
    by_feature: list[UsageFeature]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    ai_mode: Literal["mock", "live"]
    spend_usd: float

```

## API routes

| Method | Route | Request | Response model | Purpose |
|---|---|---|---|---|
| GET | `/api/health` | — | `HealthResponse` | Liveness, mode, spend |
| GET | `/api/communities` | — | `CommunitiesResponse` | List A and B |
| GET | `/api/communities/{id}/map` | — | `MapResponse` | Map data, fuzzed members and pins |
| GET | `/api/communities/{id}/reach` | — | `ReachResponse` | Overall and cluster Reach |
| GET | `/api/communities/{id}/gaps` | — | `GapsResponse` | Ranked unreached clusters |
| GET | `/api/communities/{id}/nudge` | `?mode=small_ask\|invite` | `NudgeResponse` | Candidate and Spark nudge |
| POST | `/api/drafts` | `DraftRequest` | `DraftResponse` | Generate an editable first message |
| POST | `/api/drafts/{id}/send` | `SendDraftRequest` | `SentDraftResponse` | Human records edited send; no delivery |
| POST | `/api/hangouts` | `HangoutRequest` | `HangoutResponse` | Mark as met, edge and Reach delta |
| POST | `/api/voice/invite` | multipart: `community_id`, `audio` | `VoiceInviteResponse` | Transcript and parsed preview |
| POST | `/api/invites` | `CreateInviteRequest` | `Invite` | Human confirms a voice preview or creates manually |
| POST | `/api/invites/{id}/join` | — | `JoinResponse` | Join or waitlist (P1) |
| POST | `/api/invites/{id}/cancel` | — | `CancelResponse` | Leave and promote (P1) |
| POST | `/api/rsvps/{id}/approve` | — | `ApproveResponse` | Host approves; location only in this response (P1) |
| POST | `/api/demo/reset` | — | `ResetResponse` | Reseed both communities |
| GET | `/api/usage` | — | `UsageResponse` | Spend by feature and cache hits |

## Meta API facts and workshop answers

The guide lists base URL https://api.meta.ai/v1 and an OpenAI-compatible SDK. Confirmed account model ID, speech-to-text format/protocol, pricing, limits, and Muse connector path are pending H1/H2. No Meta call has been made. Workshop answers: pending.

