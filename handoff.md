# Porchlight — handoff

_Last updated: 2026-10-24 23:18 America/Chicago by lead/session 1_
_Current phase: 5–9 — P0 AI, voice, frontend, deployment | Gates passed: G1 ☐ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
Phase 2–4 backend and graph work in mock mode; 21 backend tests pass. AI/voice code is implemented but live checks await H1. Frontend is in progress. H2/H3 are done; H1 was deferred by the human.

## Next up (do these in order)
1. Commit reviewed Phase 3 API and Phase 4 graph; commit Phase 5–6 mock AI/voice implementation with live verification explicitly pending H1.
2. Finish Phase 8 frontend and run the local P0 loop at 390px with mock backend.
3. Finish Phase 9 deploy artifacts, then raise H5 when a concrete deployment is ready for login/env setup.

## In progress (exact state)
- Task: Frontend build and local P0 integration. API, graph, and mock AI/voice are ready for commit.
- Files touched since last commit: backend API/AI/graph modules and tests, `backend/Dockerfile`, `backend/.dockerignore`, `DEPLOY.md`, frontend files in progress.
- State: Backend dependencies installed in ignored workspace Python; 21 backend tests pass. MiniLM model saved in ignored `.tools/all-MiniLM-L6-v2` and loaded without network; Priya ranks first. Live checks await H1.
- Last command run + result: `..\.tools\Python311\python.exe -m pytest -q tests --basetemp=..\.tools\pytest-full-p0-1` from backend: 21 passed, one Starlette/anyio deprecation warning. A real ffmpeg conversion produced mono 16-bit 24 kHz WAV.

## Completed
| Phase | Task | Verified by | Commit |
|---|---|---|---|
| 1 | Bootstrap, shared contracts, mock fixtures, design prompts | File checks; JSON parse; Python import pending runtime | `ad81c57` |
| 2 | Deterministic A/B seeds, SQLite reseed, public serializers | Seed check; 4 focused tests passed | `744f1fb` |
| 3 | P0 mock API routes, public serializers, spend-preserving reset | HTTP app checks; 21-test backend suite | `54ac736` |
| 4 | Reach, gaps, bridge scoring with local MiniLM | 4 graph tests; actual MiniLM loaded and ranked Priya first | `f32914a` |

## Scope tier checklist
P0: [ ] map+pins [ ] graph overlay [ ] gaps+reach [ ] spark nudge+draft [ ] voice-to-pin [ ] A/B toggle [ ] mark-as-met updates reach [ ] deployed + reset
P1: [ ] muse connector (path: __) [ ] join/waitlist [ ] low-pressure mode [ ] eval [ ] safety layer
P2: [ ] muse image assets [ ] (roadmap items untouched by design)

## Human gates
| Gate | Status (open/done/skipped) | Notes |
|---|---|---|
| H1 | skipped for now | Human deferred key. No `.env` exists; G1/live G2 pending. |
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

## Meta API facts confirmed
No live account check yet. Human supplied H2 answers: choose `muse-spark-1.3-contributor` and the standalone Meta API agent path; skip Graph API. Meta docs confirm Contributor pricing $0.10/M input, $0.20/M output, 150 RPM/3M TPM (https://dev.meta.ai/docs/pricing-rate-limits). Voice Path A is documented by Meta: multipart POST `/v1/asr/transcribe`, model `muse-voice-transcribe-1.0`, `request` JSON plus WAV `audio`, bearer header, 24 kHz mono 16-bit PCM, JSON `transcript`; pricing $0.18/hour (https://dev.meta.ai/docs/speech-to-text).

## Spend
No live calls made. Cap $40; $10 reserve from the stated $50 credit, pending confirmation.

## How to run
From `backend`: `..\.tools\Python311\python.exe -m seed.generate_seed`; `..\.tools\Python311\python.exe -m app.seed_check`; `..\.tools\Python311\python.exe -m pytest -q tests --basetemp=..\.tools\pytest-full-p0-1`; `$env:MINILM_MODEL_DIR=(Resolve-Path '..\.tools\all-MiniLM-L6-v2').Path; ..\.tools\Python311\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Runtime and MiniLM are in ignored `.tools/`; requirements are installed there. `AI_MODE=mock` by default. Frontend commands pending build.

## Deployed URLs
None.

## Known issues / bugs
- H1 deferred: no live Spark/Voice call, G1 or G2 verification yet.
- A stateless hosted instance can lose the local usage ledger on cold start. Reset demo and same-file restarts preserve it.

## Ideas (not approved)
- None.
