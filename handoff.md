# Porchlight — handoff

_Last updated: 2026-10-25 01:32 America/Chicago by lead/session 3_
_Current phase: 6, 9 — live Voice and P0 deployment | Gates passed: G1 ☑ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
G1 passed and local live Priya nudge/draft pass. The deployed mock loop and CORS pass. Render is live, but hosted Spark nudge and invite parsing raise `NotFoundError` (404), so both use fallbacks. Two-phone Voice UI worked. Safe diagnostics are deployed; a new nudge still degraded, and the human will paste its sanitized 404 log line. G2 remains open.

## Next up (do these in order)
1. Obtain the sanitized `Meta Spark HTTP 404 feature=nudge ...` Render log line from the human (H10), then fix the specific hosted cause. New diagnostic commit `962b8c7` was deployed; hosted nudge still returned `degraded=true` and `/api/usage` was $0 on the fresh instance. The human replied that they will paste the line.
2. Commit the locally verified Quarry P0 mock Voice fallback fix in `backend/app/ai/`; push it with the hosted Spark root-cause fix to avoid a separate Render manual deploy. After hosted Spark is fixed, re-run three deployed live loops with reset/cache-hit checks and inspect `/api/usage`. Stay in P0 until G2 passes.
3. After G2, continue G2→P1→P2 in guide scope order if event time permits.

## In progress (exact state)
- Task: Diagnose hosted Spark 404. Safe diagnostic code in `backend/app/ai/provider.py` trims model/base outer whitespace and logs only booleans for expected model, base, and Chat Completions path plus OpenAI SDK version, key presence, and 404 feature. It never logs a key, model value, URL, prompt, response body, or exception text. Human confirmed `MUSE_SPARK_MODEL`, `META_API_BASE`, and the key match local. Code `962b8c7` was manually deployed. New hosted nudge remained degraded; human will supply log line.
- Continuity note: context was compacted again at the start of session 3. Read `AGENTS.md`, this handoff, relevant guide sections, and `CONTEXT.md`; compared git log/status. Commits through `60b550f` are complete. Only original human untracked guide/instruction files and design JPGs remain; no half-done tracked edits. Prior stale note about uncommitted AI/devops files was obsolete and removed.
- Files touched since last commit: `backend/app/ai/spark.py`, `backend/app/ai/fixtures/parse_invite.json`, `backend/app/ai/fixtures/transcript.json`, `backend/tests/test_ai.py`, and `handoff.md`. The ai-integration subagent finished the Quarry mock Voice fallback fix. Ignored `.tools/quarry_mock_probe.py` was created by QA.
- State: Mock backend at `http://127.0.0.1:8000` serves `/api/health` and `/docs` (200). G1 live smoke returned visible text and usage. Live Priya nudge and draft both generated non-degraded grounded text using `reasoning_effort=minimal` and 500 tokens. The prior draft 300-token limit truncated JSON after 267–274 reasoning tokens; a targeted 500-token draft passed. Fresh local mock TestClient health 200 with `torch_loaded=False`. Frontend 390×844 home render reviewed; production build passes outside sandbox. QA privacy fix passes and `.dockerignore` excludes `.env`/`.env.*`. Docker daemon unavailable.
- Last command run + result: after Quarry fix, ai-integration ran focused AI tests 10 passed and full backend tests 29 passed. Lead re-ran `.tools/quarry_mock_probe.py`: full mock loop and A/B schema passed; Quarry preview has no Hyde Park place hint; Reach 5/29 to 6/29 and South Wing 0/8 to 1/8. New hosted nudge after Render diagnostics deploy remained `degraded=true`; fresh-instance `/api/usage` $0. Human was asked for the specific sanitized Meta Spark line after sending a normal `GET /` 404 line.

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
| 9 (Spark diagnostic) | Sanitize 404 logs while checking Render model/base/path and SDK version | Synthetic 404 fallback/redaction; AI tests 9 passed; full backend tests 28 passed; local Uvicorn health/docs 200; seed check passed; pushed to GitHub | `962b8c7` |
| 9 (Quarry mock check) | Community B gap, nudge, edit/send, mark met, voice preview/confirm, reset, A/B schema | `.tools/quarry_mock_probe.py` passed; wrong mock Voice place hint found for fix | probe ignored, no commit |
| 6/9 (Quarry Voice fallback) | Location-neutral mock transcript and seed-specific public place hint for each community | Focused AI tests 10 passed; full backend tests 29 passed; Quarry mock probe passed with no Avenue G in Quarry preview | pending commit |

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
| H10 | open (hosted Spark 404) | Human supplied Render Logs showing `NotFoundError` for nudge and parse_invite, then confirmed Spark model ID, base URL, and key match the working local `.env`. Safe provider diagnostics deployed; new hosted nudge degraded. Human will paste the new sanitized 404 line. No secrets requested. |

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
| 2026-10-25 | Log only booleans for Spark model/base/path configuration and the SDK version on hosted HTTP 404. | The prior exception-class log cannot distinguish a malformed Render setting from a model entitlement issue; arbitrary error bodies could contain sensitive data. |

## Meta API facts confirmed
Human confirmed H1 and `.env` contains the key and `muse-spark-1.3-contributor`. G1 passed: Spark returned visible text and a usage object. Live Priya nudge and draft now return non-degraded generated text with minimal reasoning and 500 tokens. H2 answers choose the standalone Meta API agent path and skip Graph API. Meta docs confirm Contributor pricing $0.10/M input, $0.20/M output, 150 RPM/3M TPM (https://dev.meta.ai/docs/pricing-rate-limits). Voice Path A is documented by Meta: multipart POST `/v1/asr/transcribe`, model `muse-voice-transcribe-1.0`, `request` JSON plus WAV `audio`, bearer header, 24 kHz mono 16-bit PCM, JSON `transcript`; pricing $0.18/hour (https://dev.meta.ai/docs/speech-to-text).

## Spend
Local live `/api/usage` total $0.0006123: previous smoke $0.000072 (3 calls), nudge $0.0002234 (2 calls), draft $0.0002745 (3 calls), plus a fresh Spark availability check $0.0000424 (1 call, no visible text at 200 max tokens); cache hits 0. Previous hosted Render ledger observed $0.000268 from two Voice calls; its cold restart reset the ephemeral ledger to $0 and new Spark attempts fell back before metering. Combined observed spend at least $0.0008803. The earlier third local smoke passed G1. Cap $40; $10 reserve from the stated $50 credit. User confirmed H1.

## How to run
From `backend`: `..\.tools\Python311\python.exe -m seed.generate_seed`; `..\.tools\Python311\python.exe -m app.seed_check`; `..\.tools\Python311\python.exe -m pytest -q tests --basetemp=..\.tools\pytest-p0-push`; `..\.tools\Python311\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Python and the generation-only MiniLM model are in ignored `.tools/`; requirements are installed there. Runtime uses committed seed vectors and no Torch. `AI_MODE=mock` by default. G1 from repo root: set `$env:AI_MODE='live'`, run `.\.tools\Python311\python.exe scripts\smoke_spark.py`, then `Remove-Item Env:AI_MODE`; check `/api/usage`. From `frontend`: `npm.cmd install`; `npm.cmd run dev`; `npm.cmd run build`. Frontend build required sandbox escalation in session 2 because esbuild was denied reading Vite config. Dev frontend uses `http://localhost:5173` for backend CORS.

Deployment after H9: follow `DEPLOY.md`. Import root `render.yaml` as a Render Free Blueprint from the Git repo; the human enters `META_MODEL_API_KEY` in Render settings. Create Vercel Hobby project with Root Directory `frontend/` and `VITE_API_BASE` set to the Render HTTPS origin, then set Render `FRONTEND_ORIGIN` to the Vercel HTTPS origin. For the local seeded vectors, from `backend`: `..\.tools\Python311\python.exe seed/precompute_vectors.py`; re-run if the fictional seed changes. The Render image uses `requirements.deploy.txt`, ffmpeg, and the checked-in vectors.

## Deployed URLs
Frontend: https://porchlight-umber.vercel.app/ ; backend health: https://porchlight-api-vsn3.onrender.com/api/health . Render currently reports `AI_MODE=live`.

## Known issues / bugs
- Two-phone Voice posting UI passed, and Voice billed two live transcriptions. Spark invite parsing still fell back due hosted 404; deployed three-run G2 loop has not passed. Quarry mock Voice preview previously carried Hyde Park's `near Avenue G` hint; local fix is verified and awaits commit/deployment.
- Computer-use browser inventory is empty in session 2; the 390px home screenshot was reviewed, while click-through UI testing remains for deployed H6.
- Hosted CORS is fixed and Render is live. Spark nudge and parse_invite fail with `NotFoundError` before usage accounting even though the human confirmed Render model/base/key match local; H10 root-cause diagnosis remains open. The human accepted continued use of the existing Meta key after its value appeared in IDE context.
- Render Free spins down after 15 idle minutes and its local SQLite/cache disappear on restart; this also resets the per-instance cost ledger. Warm before demos, run three cache-hit loops within one active instance, and check Meta account spend externally.
- Render Free memory is 512 MB. The slim image starts and responds to API checks, but sustained memory use has not been measured.
- A stateless hosted instance can lose the local usage ledger on cold start. Reset demo and same-file restarts preserve it.
- Docker daemon is not running locally; the Dockerfile has not been built here.

## Ideas (not approved)
- None.
