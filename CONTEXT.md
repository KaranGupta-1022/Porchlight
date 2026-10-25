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

The guide lists base URL https://api.meta.ai/v1 and an OpenAI-compatible SDK. H1 is deferred by the human, so no Meta call has been made and account model availability/credit remain unconfirmed. H2 workshop answers were supplied by the human on 2026-10-24:

1. A true Muse connector needs OAuth-shaped trust and would make judges authenticate. Build a standalone agent using the Meta Model API for a frictionless demo, after G2. The guide's Spark function-calling fallback is the intended in-app path.
2. Voice supports live and static uploads. Use a short uploaded file for this sprint. Official Meta docs specify WAV for the batch endpoint; convert browser audio to WAV before upload.
3. Use `muse-spark-1.3-contributor` for this fictional-data demo. The human reports $0.10/M input and $0.20/M output and warns that thinking tokens count as output; use low reasoning. Meta's official [pricing page](https://dev.meta.ai/docs/pricing-rate-limits) confirms prices and notes Contributor content may train future Meta models. No real personal data will be sent.
4. Workshop reported 3,000 RPM and 4M TPM, but Meta's official pricing page lists **150 RPM and 3M TPM for the Contributor model**. Use the model-specific official limit.
5. Favor one or two flawless core tools over breadth.
6. Skip Facebook Graph API; use fictional seed data.

Meta's [speech-to-text documentation](https://dev.meta.ai/docs/speech-to-text), fetched 2026-10-24, confirms Path A: `POST https://api.meta.ai/v1/asr/transcribe` with `Authorization: Bearer <key>` and multipart parts `request` (JSON: `{"mode":"PUSH_TO_TALK","model":"muse-voice-transcribe-1.0","audioEncoding":"WAV"}`) and `audio` (WAV). Convert browser audio with ffmpeg to mono 16-bit PCM WAV at 24 kHz. Default JSON response includes `transcript` and `audioDurationMs`. Voice pricing on that page is $0.18/hour = $0.003/minute. Keep all network calls in `ai/provider.py`.

