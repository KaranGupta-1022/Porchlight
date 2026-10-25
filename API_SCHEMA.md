# Porchlight REST contract

`backend/app/models.py` defines every response. All coordinates in responses are block-level coordinates. `PublicMember` is the only member serializer and never contains `unit_label` or an address. Both communities use the same shapes. All times are ISO 8601 with timezone offsets.

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

IDs are opaque strings. A missing community, member, draft, invite, or RSVP returns 404. Invalid input returns 422. The demo user for each community is the seeded `is_demo_user` member; routes use that user until real auth exists. `POST /api/voice/invite` returns a preview so the human can edit or discard it before `POST /api/invites`. This resolves the guide's confirm-step requirement without auto-posting.

## Examples

`GET /api/health`

```json
{"status":"ok","ai_mode":"mock","spend_usd":0.0}
```

`GET /api/communities`

```json
{"communities":[{"id":"hydepark","name":"Hyde Park","kind":"neighborhood","center_lat":30.305,"center_lng":-97.728,"zoom":16},{"id":"quarry","name":"The Quarry Lofts","kind":"apartments","center_lat":30.287,"center_lng":-97.745,"zoom":18}]}
```

`GET /api/communities/hydepark/map` (representative excerpt)

```json
{"community":{"id":"hydepark","name":"Hyde Park","kind":"neighborhood","center_lat":30.305,"center_lng":-97.728,"zoom":16},"clusters":[{"id":"hydepark-duval","community_id":"hydepark","name":"Duval St","polygon":{"type":"Polygon","coordinates":[[[-97.728,30.303],[-97.727,30.303],[-97.727,30.306],[-97.728,30.303]]]}}],"members":[{"id":"hydepark-priya","community_id":"hydepark","cluster_id":"hydepark-duval","display_name":"Priya","emoji_avatar":"🐕","lat":30.305,"lng":-97.727,"interests":["dogs","coffee"],"availability":["wed-evening"],"verified":true,"is_demo_user":false}],"invites":[{"id":"hydepark-dogwalk","community_id":"hydepark","host_id":"hydepark-priya","title":"Evening dog walk","activity":"dog walk","starts_at":"2026-10-29T18:00:00-05:00","capacity":6,"going_count":2,"lat":30.305,"lng":-97.727,"place_hint":"near Duval St","requires_approval":true,"status":"open","source":"manual"}],"statuses":[],"edges":[{"a_id":"hydepark-you","b_id":"hydepark-marcus","strength":1.2,"hangout_count":2}]}
```

`GET /api/communities/hydepark/reach`

```json
{"community_id":"hydepark","met":6,"total":39,"ratio":0.1538,"clusters":[{"cluster_id":"hydepark-duval","name":"Duval St","met":0,"total":6,"ratio":0.0}]}
```

`GET /api/communities/hydepark/gaps`

```json
{"community_id":"hydepark","gaps":[{"cluster_id":"hydepark-duval","name":"Duval St","size":6,"reach":0.0,"gap_score":5.2}]}
```

`GET /api/communities/hydepark/nudge?mode=small_ask` (candidate is a complete `PublicMember` as above)

```json
{"candidate":{"id":"hydepark-priya","community_id":"hydepark","cluster_id":"hydepark-duval","display_name":"Priya","emoji_avatar":"🐕","lat":30.305,"lng":-97.727,"interests":["dogs","coffee"],"availability":["wed-evening"],"verified":true,"is_demo_user":false},"components":{"interest_sim":0.83,"schedule_overlap":0.5,"gap_bonus":1.0,"warm_path":0.0,"score":0.657},"gap":{"cluster_id":"hydepark-duval","name":"Duval St","size":6,"reach":0.0,"gap_score":5.2},"nudge":{"headline":"You haven't met anyone on Duval St yet","why":"Priya also likes dogs and coffee, and you're both free on weekday evenings.","first_step":"A wave and a hello on a public dog walk is enough.","cta":"Draft a hello","draft_message":"Hi Priya! I walk my dog near Duval too. Want to loop the block together this week?"},"degraded":false}
```

`POST /api/drafts` with `{"community_id":"hydepark","to_id":"hydepark-priya","context":"dog walk","tone":"casual"}`

```json
{"id":"draft-1","to_member":{"id":"hydepark-priya","community_id":"hydepark","cluster_id":"hydepark-duval","display_name":"Priya","emoji_avatar":"🐕","lat":30.305,"lng":-97.727,"interests":["dogs","coffee"],"availability":["wed-evening"],"verified":true,"is_demo_user":false},"text":"Hi Priya! Want to take a short walk this week?","degraded":false}
```

`POST /api/drafts/draft-1/send` with `{"final_text":"Hi Priya! Walk this week?"}`

```json
{"id":"draft-1","final_text":"Hi Priya! Walk this week?","sent_at":"2026-10-24T16:30:00-05:00"}
```

`POST /api/hangouts` with `{"community_id":"hydepark","member_id":"hydepark-priya","kind":"dog walk"}`

```json
{"edge":{"a_id":"hydepark-you","b_id":"hydepark-priya","strength":1.0,"hangout_count":1},"before":{"community_id":"hydepark","met":6,"total":39,"ratio":0.1538,"clusters":[{"cluster_id":"hydepark-duval","name":"Duval St","met":0,"total":6,"ratio":0.0}]},"after":{"community_id":"hydepark","met":7,"total":39,"ratio":0.1795,"clusters":[{"cluster_id":"hydepark-duval","name":"Duval St","met":1,"total":6,"ratio":0.1667}]}}
```

`POST /api/voice/invite` with audio upload

```json
{"transcript":"Anyone want to play board games near Avenue G this Friday at six? Four spots.","parsed":{"title":"Board games this Friday","activity":"board games","starts_at":"2026-10-30T18:00:00-05:00","capacity":4,"place_hint":"near Avenue G","confidence":0.94},"degraded":false}
```

`POST /api/invites` with `{"community_id":"hydepark","title":"Board games this Friday","activity":"board games","starts_at":"2026-10-30T18:00:00-05:00","capacity":4,"place_hint":"near Avenue G","source":"voice"}` returns an `Invite` as in the map response.

`POST /api/invites/hydepark-dogwalk/join`

```json
{"rsvp_id":"rsvp-1","status":"waitlist","position":2}
```

`POST /api/invites/hydepark-dogwalk/cancel`

```json
{"cancelled":true,"promoted_rsvp_id":"rsvp-2"}
```

`POST /api/rsvps/rsvp-2/approve`

```json
{"rsvp_id":"rsvp-2","status":"going","exact_location":"Shared with this approved RSVP only"}
```

`POST /api/demo/reset`

```json
{"reset":true}
```

`GET /api/usage`

```json
{"total_usd":0.0042,"cost_cap_usd":40.0,"by_feature":[{"feature":"nudge","usd":0.0042,"calls":2,"cache_hits":1}]}
```
