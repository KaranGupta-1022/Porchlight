# Porchlight — handoff

_Last updated: 2026-10-24 22:55 America/Chicago by lead/session 1_
_Current phase: 2 — Data model and seed | Gates passed: G1 ☐ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
Bootstrap and shared contracts are written. H1/H2/H3 are open. Python is not on PATH, so backend verification needs a local Python runtime. All product work stays in mock mode until Meta access is verified.

## Next up (do these in order)
1. Commit bootstrap and contracts with existing Git identity.
2. Generate and verify Phase 2 seed data and SQLite reseed.
3. Find or install a Python 3.11 runtime; run the backend checks.

## In progress (exact state)
- Task: Phase 2 seed and database next.
- Files touched: `.env.example`, `.gitignore`, `CONTEXT.md`, `handoff.md`, `API_SCHEMA.md`, `backend/app/models.py`, four mock fixtures, `design/PROMPTS.md`.
- State: Contracts written; backend tests not run because `python`, `py`, and `python3` are unavailable on PATH.
- Last command run + result: `Get-Command py,python,python3,uv,node,npm,git`; only Node, npm, and Git found.

## Completed
| Phase | Task | Verified by | Commit |
|---|---|---|---|

## Scope tier checklist
P0: [ ] map+pins [ ] graph overlay [ ] gaps+reach [ ] spark nudge+draft [ ] voice-to-pin [ ] A/B toggle [ ] mark-as-met updates reach [ ] deployed + reset
P1: [ ] muse connector (path: __) [ ] join/waitlist [ ] low-pressure mode [ ] eval [ ] safety layer
P2: [ ] muse image assets [ ] (roadmap items untouched by design)

## Human gates
| Gate | Status (open/done/skipped) | Notes |
|---|---|---|
| H1 | open | Asked for key in local `.env`, model, and credit. No `.env` exists yet. |
| H2 | open | Asked for six workshop answers. |
| H3 | open | `design/PROMPTS.md` delivered; five PNGs pending. |

## Decisions & deviations from the guide
| When | Decision | Why |
|---|---|---|
| 2026-10-24 | Use existing initialized repo and existing Git identity. | Repo is already initialized. |
| 2026-10-24 | `/api/voice/invite` returns a transcript and parsed preview; human posts through `/api/invites`. | The guide requires a confirm step before posting. |

## Meta API facts confirmed
None from a live account. Model ID, voice path, connector path, and workshop answers pending.

## Spend
No live calls made. Cap $40; $10 reserve from the stated $50 credit, pending confirmation.

## How to run
Pending implementation.

## Deployed URLs
None.

## Known issues / bugs
- None identified yet.

## Ideas (not approved)
- None.
