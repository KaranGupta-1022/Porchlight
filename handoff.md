# Porchlight — handoff

_Last updated: 2026-10-25 01:05 America/Chicago by lead/session 2_
_Current phase: 6, 9 — live Voice and P0 deployment | Gates passed: G1 ☑ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
G1 passed and local live Priya nudge/draft pass. The deployed mock loop and CORS pass. Render is live, but hosted Spark nudge and invite parsing raise `NotFoundError` (404), so both use fallbacks. Two-phone Voice UI worked and Render billed two Voice calls ($0.000268). H10 config check is pending; G2 remains open.

## Next up (do these in order)
1. Human checks Render Environment `MUSE_SPARK_MODEL=muse-spark-1.3-contributor`, `META_API_BASE=https://api.meta.ai/v1`, and privately compares the Meta key with local `.env` (H10). Render Logs showed `NotFoundError` for nudge and parse_invite; official Meta docs say 404 means model ID typo or model unavailable to the team. Correct any mismatch and redeploy; do not request/display the key.
2. Re-run the three hosted live Spark loops with reset and cache-hit checks only after the cause is fixed; inspect `/api/usage`. Complete H6 phone voice test and deployed UI check. Stay in P0 until G2 passes.
3. After G2, continue G2→P1→P2 in guide scope order if event time permits.

## In progress (exact state)
- Task: Diagnose hosted Spark 404. `.tools/deployed_live_probe.py` stopped on run-1 nudge `degraded=true` and final reset 200; a second nudge also degraded. Render Logs show `Meta request failed for nudge: NotFoundError` and `parse_invite: NotFoundError`; neither metered Spark. Human completed H6 on two phones; hosted usage has two Voice calls. H10 Render configuration check pending. CORS and mock loops pass; H9 approved.
- Continuity note: context was compacted while the agents were editing. The seed vector artifact and production requirements are committed in `aafa773`; graph loader is committed in `1ff53d7`; AI and devops changes remain uncommitted and require review before committing.
- Files touched since last commit: `backend/app/ai/provider.py`, `backend/app/ai/spark.py`, `backend/tests/test_ai.py`, `scripts/smoke_spark.py` (AI agent editing); `DEPLOY.md`, `render.yaml`, `backend/Dockerfile` (devops); `handoff.md`. Vercel correction and context update are committed in `42d51fb`.
- State: Mock backend at `http://127.0.0.1:8000` serves `/api/health` and `/docs` (200). G1 live smoke returned visible text and usage. Live Priya nudge and draft both generated non-degraded grounded text using `reasoning_effort=minimal` and 500 tokens. The prior draft 300-token limit truncated JSON after 267–274 reasoning tokens; a targeted 500-token draft passed. Fresh local mock TestClient health 200 with `torch_loaded=False`. Frontend 390×844 home render reviewed; production build passes outside sandbox. QA privacy fix passes and `.dockerignore` excludes `.env`/`.env.*`. Docker daemon unavailable.
- Last command run + result: hosted `/api/usage` total $0.000268 from two Voice calls, no Spark calls; Render Logs show `NotFoundError` for nudge and parse_invite. Human reports Voice post worked on two phones. Hosted live nudge degraded twice, first three-run script stopped safely and reset 200. Prior mock CORS/prep checks pass; local tests 28 passed and frontend build passed.

## Completed
| Phase | Task | Verified by | Commit |
|---|---|---|---|
| 1 | Bootstrap, shared contracts, mock fixtures, design prompts | File checks; JSON parse; Python import pending runtime | `ad81c57` |
| 2 | Deterministic A/B seeds, SQLite reseed, public serializers | Seed check; 4 focused tests passed | `744f1fb` |
| 3 | P0 mock API routes, public serializers, spend-preserving reset | HTTP app checks; 21-test backend suite | `54ac736` |
| 4 | Reach, gaps, bridge scoring with local MiniLM | 4 graph tests; actual MiniLM loaded and ranked Priya first | `f32914a` |
| 5–6 | Mock and live-capable Spark/Voice provider, cache, cap, batch WAV upload | 21-test suite; real ffmpeg WAV conversion. Live Voice pending H6. | `ab1c365` |
| 9 (local prep) | Dockerfile, build-time MiniLM, ffmpeg, deployment notes | File review; container build pending Docker daemon. Full mock API loop passed locally. | `400d444` |
| 0 (G1) | Live Spark smoke returns text and usage | `AI_MODE=live` `scripts/smoke_spark.py`; `/api/usage` read | `50a3977` |
| 5 (live) | Minimal reasoning and 500-token JSON budget produce grounded nudge and editable draft | Live Priya nudge and draft non-degraded; full backend suite 28 passed | `50a3977` |
| 3 (QA fix) | Reject numbered exact addresses in invite title, activity, and place hint | 3 focused privacy cases; 24-test backend suite | `c57a09f` |
| 9 (QA fix) | Exclude local `.env` secrets from backend Docker build context | `.dockerignore` inspected; Docker build pending daemon | `8999870` |
| 5 (samples) | Ten fictional mock prompt/output pairs for nudges, drafts, and invite parsing | QA checked seed facts, safety wording, numbering, and JSON | `eeb176a` |
| 8 (implementation) | Vite React frontend, map, sheets, editable composer, voice preview, Reach animation, A/B toggle | `npm.cmd run build` passed; 390×844 home screenshot reviewed; Vite `/api` proxy passed | `fc308c6` |
| 9 (deployment instructions) | Exact Cloud Run source-deploy and Vercel commands, env sequence | Official platform docs checked; H5/H9 pending | `a2d6e9e` |
| 9 (Render prep) | Generated normalized MiniLM vectors for 70 seeded residents and slim runtime requirements | Re-ran local generator; validated 70 vectors at 384 dimensions, matching seed hashes/interests | `aafa773` |
| 4/9 (Render graph) | Load seeded MiniLM vectors without Torch at runtime; reject stale artifacts | Full backend suite 28 passed; seed check passed; graph tests block model imports | `1ff53d7` |
| 9 (Render deployment) | Render Free Blueprint, slim Dockerfile, Vercel setup instructions | YAML/static checks, local health 200 without Torch; hosted build pending | `3eb6ea3` |
| 9 (publication prep) | Pushed P0 source to GitHub for Render/Vercel imports | `git push origin main` succeeded to `50a3977`; `.env` untracked/ignored | `50a3977` |
| 9 (hosted mock check) | Render/Vercel URLs, CORS, both communities, A core loop and voice pin/reset | Public health/HTML 200; CORS preflight 200; `.tools/deployed_mock_probe.py` passed; Quarry map/gap/nudge passed | host config, no code commit |

## Scope tier checklist
P0: [ ] map+pins [ ] graph overlay [ ] gaps+reach [ ] spark nudge+draft [ ] voice-to-pin [ ] A/B toggle [ ] mark-as-met updates reach [ ] deployed + reset
P1: [ ] muse connector (path: __) [ ] join/waitlist [ ] low-pressure mode [ ] eval [ ] safety layer
P2: [ ] muse image assets [ ] (roadmap items untouched by design)

## Human gates
| Gate | Status (open/done/skipped) | Notes |
|---|---|---|
| H1 | done; existing key explicitly accepted | Initial H1 and G1 passed. The human's 2026-10-25 IDE context exposed the Meta key value in chat. The human expressly declined rotation and authorized continued use of the existing key. Never reproduce the value; check only variable presence on Render before live mode. |
| H2 | done | Six workshop answers recorded in `CONTEXT.md`. Official Contributor limits correct the workshop's standard-model limits. |
| H3 | done | Five supplied JPG mockups converted to the exact PNG filenames. Frontend must match them. |
| H5 | done | Human signed in, created projects, and supplied Render/Vercel HTTPS URLs. Backend is now live; CORS is fixed. CLI/browser automation remains unavailable; external HTTP checks work outside sandbox. |
| H6 | done (UI path) | Human reported Voice post worked on two phones. Hosted Voice transcribed twice and billed; Spark `parse_invite` used fallback due 404, so the fully live AI voice-to-pin G2 criterion remains open. |
| H9 | approved | Human explicitly approved pushing Porchlight commits to GitHub origin and publishing the demo on Render Free and Vercel Hobby. No GCP, custom domain, or paid tier. |
| H10 | open (config check) | Human supplied Render Logs showing `NotFoundError` for nudge and parse_invite. Asked them to verify Spark model ID, base URL, and key matching local `.env` privately; no secrets requested. |

## Decisions & deviations from the guide
| When | Decision | Why |
|---|---|---|
| 2026-10-24 | Use existing initialized repo and existing Git identity. | Repo is already initialized. |
| 2026-10-24 | `/api/voice/invite` returns a transcript and parsed preview; human posts through `/api/invites`. | The guide requires a confirm step before posting. |
| 2026-10-24 | Add `python-multipart` to requirements. | FastAPI requires it for the Phase 6 audio upload route. |
| 2026-10-24 | Install Python locally in ignored `.tools/`, not through system Chocolatey. | Python is absent, and Chocolatey cannot write its system package directory without admin access. |
| 2026-10-24 | Use Voice Path A: batch upload to `/v1/asr/transcribe` after ffmpeg conversion to 24 kHz mono PCM WAV. | Confirmed in Meta's official speech-to-text documentation. H4 is unnecessary. |
| 2026-10-24 | Set Spark defaults to `muse-spark-1.3-contributor`, $0.10/M input, $0.20/M output; voice $0.003/min. | H2 workshop answers and Meta's official pricing pages. This updates the Phase 1 example after bootstrap. All residents are fictional; Contributor mode may use data for training. |
| 2026-10-24 | Use Meta's model-specific Contributor limits (150 RPM, 3M TPM). | The workshop's 3,000 RPM/4M TPM applies to the standard model, per Meta's pricing page. |
| 2026-10-24 | Preserve `api_usage` across Reset demo and same-file startup reseed. | Otherwise the $40 cap can be bypassed by pressing Reset. Ephemeral host cold starts still need a durable ledger or a documented limitation. |
| 2026-10-24 | Prepare Cloud Run/Render deployment artifacts but keep `AI_MODE=mock` until H1/G1. | H1 was deferred by the human; no live spend or unsupported live claim. Docker daemon and `gcloud`/`vercel` CLIs are unavailable in this shell. |
| 2026-10-24 | Reject public invite text containing numbered street locations, including suffix-free street names. | QA found an exact-address leak through title/activity/place_hint. Conservative filtering can reject some numbered descriptions; privacy takes precedence. |
| 2026-10-24 | Exclude `.env` and `.env.*` from the backend Docker build context. | QA found that remote builders otherwise receive local secrets even when Dockerfile COPY is explicit. |
| 2026-10-25 | Use Meta documented `reasoning_effort=minimal` for G1 smoke and product JSON calls, with 500 completion tokens for nudge/draft/parse; include reasoning in cache keys. | Default or low reasoning and 180–300 token caps left too little visible output. Live Priya nudge and draft passed with the higher budget. Source: https://dev.meta.ai/docs/reasoning. |
| 2026-10-24 | Select Cloud Run `us-central1` / `porchlight-api` and Vercel `porchlight-ui`, with zero minimum instances and no custom domain. | Phase 9 calls for a public HTTPS backend/frontend; this keeps the demo path simple and avoids optional paid resources. Deployment itself awaits H5/H9. |
| 2026-10-24 | Hold deployment after the human's H5/H9 reply. | The human asked whether the agent can log in; AGENTS.md prohibits agent credential entry. Continue local P0 checks until the human signs in and explicitly approves public deployment/cost. |
| 2026-10-24 | Switch backend host from Cloud Run to Render Free and keep Vercel Hobby for the frontend. | Human has no GCP free credits and requested Render/Vercel. The guide permits Render. Official Render docs say Free web services spin down after 15 idle minutes and lose local SQLite/cache on restart; warm `/api/health` before demos and run cache-hit checks consecutively. No paid tier is authorized. |
| 2026-10-24 | Cancel optional gcloud CLI download and remove its partial ignored archive. | GCP is no longer the selected host; download was still in progress and no credentials were used. |
| 2026-10-25 | Precompute MiniLM interest vectors for fictional seed residents and load them without Torch in Render Free runtime; trim production dependencies and skip Docker build-time MiniLM download. | Official Render Free plan has 512 MB RAM / 0.1 CPU (https://render.com/docs/compute-plans). Local Torch/MiniLM process reserved roughly 1.5 GB, likely exceeding free RAM. Precomputed normalized vectors preserve the guide's MiniLM interest similarity for fixed fictional seeds; this is a Phase 4/9 implementation deviation to keep P0 working on the chosen free host. |
| 2026-10-25 | Continue using the existing Meta key after its value appeared in IDE context. | The human explicitly replied that it was fine to use the key. Do not quote or record its value. |

## Meta API facts confirmed
Human confirmed H1 and `.env` contains the key and `muse-spark-1.3-contributor`. G1 passed: Spark returned visible text and a usage object. Live Priya nudge and draft now return non-degraded generated text with minimal reasoning and 500 tokens. H2 answers choose the standalone Meta API agent path and skip Graph API. Meta docs confirm Contributor pricing $0.10/M input, $0.20/M output, 150 RPM/3M TPM (https://dev.meta.ai/docs/pricing-rate-limits). Voice Path A is documented by Meta: multipart POST `/v1/asr/transcribe`, model `muse-voice-transcribe-1.0`, `request` JSON plus WAV `audio`, bearer header, 24 kHz mono 16-bit PCM, JSON `transcript`; pricing $0.18/hour (https://dev.meta.ai/docs/speech-to-text).

## Spend
Local live `/api/usage` total $0.0005699: smoke $0.000072 (3 calls), nudge $0.0002234 (2 calls), draft $0.0002745 (3 calls), cache hits 0. Hosted Render `/api/usage` total $0.000268: Voice 2 calls; hosted Spark attempts fell back before metering. Combined observed spend $0.0008379. The first two local smoke calls had empty visible text, the third passed G1. Cap $40; $10 reserve from the stated $50 credit. User confirmed H1.

## How to run
From `backend`: `..\.tools\Python311\python.exe -m seed.generate_seed`; `..\.tools\Python311\python.exe -m app.seed_check`; `..\.tools\Python311\python.exe -m pytest -q tests --basetemp=..\.tools\pytest-p0-push`; `..\.tools\Python311\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Python and the generation-only MiniLM model are in ignored `.tools/`; requirements are installed there. Runtime uses committed seed vectors and no Torch. `AI_MODE=mock` by default. G1 from repo root: set `$env:AI_MODE='live'`, run `.\.tools\Python311\python.exe scripts\smoke_spark.py`, then `Remove-Item Env:AI_MODE`; check `/api/usage`. From `frontend`: `npm.cmd install`; `npm.cmd run dev`; `npm.cmd run build`. Frontend build required sandbox escalation in session 2 because esbuild was denied reading Vite config. Dev frontend uses `http://localhost:5173` for backend CORS.

Deployment after H9: follow `DEPLOY.md`. Import root `render.yaml` as a Render Free Blueprint from the Git repo; the human enters `META_MODEL_API_KEY` in Render settings. Create Vercel Hobby project with Root Directory `frontend/` and `VITE_API_BASE` set to the Render HTTPS origin, then set Render `FRONTEND_ORIGIN` to the Vercel HTTPS origin. For the local seeded vectors, from `backend`: `..\.tools\Python311\python.exe seed/precompute_vectors.py`; re-run if the fictional seed changes. The Render image uses `requirements.deploy.txt`, ffmpeg, and the checked-in vectors.

## Deployed URLs
Frontend: https://porchlight-umber.vercel.app/ ; backend health: https://porchlight-api-vsn3.onrender.com/api/health . Render currently reports `AI_MODE=live`.

## Known issues / bugs
- Two-phone Voice posting UI passed, and Voice billed two live transcriptions. Spark invite parsing still fell back due hosted 404; deployed three-run G2 loop has not passed.
- Computer-use browser inventory is empty in session 2; the 390px home screenshot was reviewed, while click-through UI testing remains for deployed H6.
- Hosted CORS is fixed and Render is live. Spark nudge and parse_invite fail with `NotFoundError` before usage accounting; H10 environment check pending. The human accepted continued use of the existing Meta key after its value appeared in IDE context.
- Render Free spins down after 15 idle minutes and its local SQLite/cache disappear on restart; this also resets the per-instance cost ledger. Warm before demos, run three cache-hit loops within one active instance, and check Meta account spend externally.
- Render Free memory is 512 MB. The slim image starts and responds to API checks, but sustained memory use has not been measured.
- A stateless hosted instance can lose the local usage ledger on cold start. Reset demo and same-file restarts preserve it.
- Docker daemon is not running locally; the Dockerfile has not been built here.

## Ideas (not approved)
- None.
