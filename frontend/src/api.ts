export type Community = { id: string; name: string; kind: 'neighborhood' | 'apartments'; center_lat: number; center_lng: number; zoom: number }
export type PublicMember = { id: string; community_id: string; cluster_id: string; display_name: string; emoji_avatar: string; lat: number; lng: number; interests: string[]; availability: string[]; verified: boolean; is_demo_user: boolean }
export type Cluster = { id: string; community_id: string; name: string; polygon: { type: 'Polygon'; coordinates: number[][][] } }
export type Edge = { a_id: string; b_id: string; strength: number; hangout_count: number }
export type Invite = { id: string; community_id: string; host_id: string; title: string; activity: string; starts_at: string; capacity: number; going_count: number; lat: number; lng: number; place_hint: string; requires_approval: boolean; status: string; source: 'manual' | 'voice' | 'muse' }
export type MemberStatus = { id: string; member_id: string; text: string; until: string }
export type MapData = { community: Community; clusters: Cluster[]; members: PublicMember[]; invites: Invite[]; statuses: MemberStatus[]; edges: Edge[] }
export type ClusterReach = { cluster_id: string; name: string; met: number; total: number; ratio: number }
export type Reach = { community_id: string; met: number; total: number; ratio: number; clusters: ClusterReach[] }
export type Gap = { cluster_id: string; name: string; size: number; reach: number; gap_score: number }
export type NudgeResponse = { candidate: PublicMember; components: Record<string, number>; gap: Gap; nudge: { headline: string; why: string; first_step: string; cta: string; draft_message: string }; degraded: boolean }
export type DraftResponse = { id: string; to_member: PublicMember; text: string; degraded: boolean }
export type ParsedInvite = { title: string; activity: string; starts_at: string; capacity: number; place_hint: string; confidence: number }
export type VoiceInviteResponse = { transcript: string; parsed: ParsedInvite; degraded: boolean }
export type HangoutResponse = { edge: Edge; before: Reach; after: Reach }

const base = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, init)
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch { /* Keep the status message. */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

function json<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

export const api = {
  communities: () => request<{ communities: Community[] }>('/api/communities'),
  map: (id: string) => request<MapData>(`/api/communities/${encodeURIComponent(id)}/map`),
  reach: (id: string) => request<Reach>(`/api/communities/${encodeURIComponent(id)}/reach`),
  gaps: (id: string) => request<{ community_id: string; gaps: Gap[] }>(`/api/communities/${encodeURIComponent(id)}/gaps`),
  nudge: (id: string, mode: 'small_ask' | 'invite') => request<NudgeResponse>(`/api/communities/${encodeURIComponent(id)}/nudge?mode=${mode}`),
  draft: (body: { community_id: string; to_id: string; context: string; tone: 'casual' | 'warmer' | 'shorter' }) => json<DraftResponse>('/api/drafts', body),
  send: (id: string, final_text: string) => json<{ id: string; final_text: string; sent_at: string }>(`/api/drafts/${encodeURIComponent(id)}/send`, { final_text }),
  hangout: (community_id: string, member_id: string) => json<HangoutResponse>('/api/hangouts', { community_id, member_id, kind: 'neighbor hello' }),
  voice: (community_id: string, audio: Blob) => {
    const form = new FormData()
    form.append('community_id', community_id)
    const extension = audio.type.includes('mp4') ? 'm4a' : audio.type.includes('ogg') ? 'ogg' : 'webm'
    form.append('audio', audio, `porchlight-voice.${extension}`)
    return request<VoiceInviteResponse>('/api/voice/invite', { method: 'POST', body: form })
  },
  invite: (body: { community_id: string; title: string; activity: string; starts_at: string; capacity: number; place_hint: string; requires_approval: boolean; source: 'voice' }) => json<Invite>('/api/invites', body),
  reset: () => request<{ reset: boolean }>('/api/demo/reset', { method: 'POST' }),
}
