# Porchlight — handoff

_Last updated: 2026-10-24 23:47 America/Chicago by lead/session 2_
_Current phase: 5, 8–9 — live Spark nudge repair, P0 frontend and deployment | Gates passed: G1 ☑ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
G1 passed: live Spark smoke returned text and usage; spend is $0.0001686 after one live nudge attempt. The local mock P0 API loop passes in both communities, 24 backend tests pass, and the frontend build passes. The live Priya nudge selected the right candidate but returned a degraded fallback because its 300-token budget was spent on reasoning; fix that before deploying.

## Next up (do these in order)
1. Fix live nudge output starvation in `backend/app/ai/provider.py` / `spark.py`, run one grounded Priya live check, inspect `/api/usage`, and switch back to mock.
2. Commit the verified QA privacy fix and Docker secret exclusion; review and commit the Phase 8 frontend. Finish local browser interactions at 390px.
3. Raise H5 for Vercel and backend host login/env setup once deployment artifacts and local UI are ready. Stay in P0 until deployed live G2 passes.

## In progress (exact state)
- Task: Finish live nudge, sample outputs, frontend interaction review, and small commits.
- Files touched since last commit: `backend/.dockerignore`, `backend/app/ai/provider.py`, `backend/app/routes/core.py`, `backend/tests/test_api_routes.py`, `scripts/smoke_spark.py`, `handoff.md`, untracked `frontend/`.
- State: Mock backend at `http://127.0.0.1:8000` serves `/api/health` and `/docs` (200). G1 live smoke returned visible text and usage after setting `reasoning_effort=minimal`; product default was set to `low`. One live Priya nudge call selected Priya/Duval but returned degraded fallback because 300 completion tokens were exhausted by reasoning. Both live and mock servers were started with MiniLM from ignored `.tools/`; confirm live server state before another call. Frontend 390×844 home render was reviewed by the frontend agent; production build passes outside the sandbox (sandbox esbuild file read was denied). QA privacy fix passes and `.dockerignore` excludes `.env`/`.env.*`. Docker daemon unavailable.
- Last command run + result: backend seed generator and seed check passed, Duval 0/6 and South Wing 0/8; backend full suite 24 passed, one Starlette warning; mock `/health` and `/docs` 200; `npm.cmd run build` passed outside sandbox. Live `/api/usage`: $0.0001686 ($0.000072 smoke, $0.0000966 nudge).

## Completed
| Phase | Task | Verified by | Commit |
|---|---|---|---|
| 1 | Bootstrap, shared contracts, mock fixtures, design prompts | File checks; JSON parse; Python import pending runtime | `ad81c57` |
| 2 | Deterministic A/B seeds, SQLite reseed, public serializers | Seed check; 4 focused tests passed | `744f1fb` |
| 3 | P0 mock API routes, public serializers, spend-preserving reset | HTTP app checks; 21-test backend suite | `54ac736` |
| 4 | Reach, gaps, bridge scoring with local MiniLM | 4 graph tests; actual MiniLM loaded and ranked Priya first | `f32914a` |
| 5–6 | Mock and live-capable Spark/Voice provider, cache, cap, batch WAV upload | 21-test suite; real ffmpeg WAV conversion. Live checks pending H1. | `ab1c365` |
| 9 (local prep) | Dockerfile, build-time MiniLM, ffmpeg, deployment notes | File review; container build pending Docker daemon. Full mock API loop passed locally. | `400d444` |
| 0 (G1) | Live Spark smoke returns text and usage | `AI_MODE=live` `scripts/smoke_spark.py`; `/api/usage` read | pending commit for reasoning fix |
| 3 (QA fix) | Reject numbered exact addresses in invite title, activity, and place hint | 3 focused privacy cases; 24-test backend suite | `c57a09f` |
| 9 (QA fix) | Exclude local `.env` secrets from backend Docker build context | `.dockerignore` inspected; Docker build pending daemon | `8999870` |
| 5 (samples) | Ten fictional mock prompt/output pairs for nudges, drafts, and invite parsing | QA checked seed facts, safety wording, numbering, and JSON | pending commit |

## Scope tier checklist
P0: [ ] map+pins [ ] graph overlay [ ] gaps+reach [ ] spark nudge+draft [ ] voice-to-pin [ ] A/B toggle [ ] mark-as-met updates reach [ ] deployed + reset
P1: [ ] muse connector (path: __) [ ] join/waitlist [ ] low-pressure mode [ ] eval [ ] safety layer
P2: [ ] muse image assets [ ] (roadmap items untouched by design)

## Human gates
| Gate | Status (open/done/skipped) | Notes |
|---|---|---|
| H1 | done | Human confirmed H1; `.env` has a nonempty `META_MODEL_API_KEY` and `MUSE_SPARK_MODEL=muse-spark-1.3-contributor`. Credit confirmation accepted from human's H1 reply. Live G1 check next; never print key. |
| H2 | done | Six workshop answers recorded in `CONTEXT.md`. Official Contributor limits correct the workshop's standard-model limits. |
| H3 | done | Five supplied JPG mockups converted to the exact PNG filenames. Frontend must match them. |

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
| 2026-10-24 | Use Meta documented `reasoning_effort=minimal` for G1 smoke and `low` for product calls; include it in cache keys. | Default reasoning spent 40 and then 200 completion tokens without visible text. The minimal smoke call returned text and usage. Source: https://dev.meta.ai/docs/reasoning. |

## Meta API facts confirmed
Human confirmed H1 and `.env` contains the key and `muse-spark-1.3-contributor`. G1 passed: Spark returned visible text and a usage object. A live nudge request selected Priya/Duval but its 300-token budget yielded no visible text, so provider metered it and returned a degraded fallback; Phase 5 live criterion remains open. H2 answers choose the standalone Meta API agent path and skip Graph API. Meta docs confirm Contributor pricing $0.10/M input, $0.20/M output, 150 RPM/3M TPM (https://dev.meta.ai/docs/pricing-rate-limits). Voice Path A is documented by Meta: multipart POST `/v1/asr/transcribe`, model `muse-voice-transcribe-1.0`, `request` JSON plus WAV `audio`, bearer header, 24 kHz mono 16-bit PCM, JSON `transcript`; pricing $0.18/hour (https://dev.meta.ai/docs/speech-to-text).

## Spend
Live `/api/usage` total $0.0001686: smoke $0.000072 (3 calls), nudge $0.0000966 (1 call), cache hits 0. The first two smoke calls had empty visible text, the third passed G1. Cap $40; $10 reserve from the stated $50 credit. User confirmed H1.

## How to run
From `backend`: `..\.tools\Python311\python.exe -m seed.generate_seed`; `..\.tools\Python311\python.exe -m app.seed_check`; `..\.tools\Python311\python.exe -m pytest -q tests --basetemp=..\.tools\pytest-audit-session2`; `$env:MINILM_MODEL_DIR=(Resolve-Path '..\.tools\all-MiniLM-L6-v2').Path; ..\.tools\Python311\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Runtime and MiniLM are in ignored `.tools/`; requirements are installed there. `AI_MODE=mock` by default. G1 from repo root: set `$env:AI_MODE='live'`, run `.\.tools\Python311\python.exe scripts\smoke_spark.py`, then `Remove-Item Env:AI_MODE`; check `/api/usage`. From `frontend`: `npm.cmd install`; `npm.cmd run dev`; `npm.cmd run build`. Frontend build required sandbox escalation in session 2 because esbuild was denied reading Vite config. Dev frontend uses `http://localhost:5173` for backend CORS.

## Deployed URLs
None.

## Known issues / bugs
- Phase 5 live Priya nudge returned `degraded=true` because the model used the entire 300-token budget on reasoning; a larger output budget must be tested.
- Live Voice, deployed G2, and phone flow are not verified yet.
- A stateless hosted instance can lose the local usage ledger on cold start. Reset demo and same-file restarts preserve it.
- Docker daemon is not running locally; the Dockerfile has not been built here.

## Ideas (not approved)
- None.
