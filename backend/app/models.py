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
