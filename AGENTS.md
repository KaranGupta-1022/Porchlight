# AGENTS.md — Porchlight autonomous build instructions

You are the **lead agent (orchestrator)** building **Porchlight** for HackTX '26 (Meta track + Best Overall). You build the entire project by following `Porchlight_Build_Guide.md`, delegating to subagents where your tool supports them, and you stop to ask the human **only** at the gates listed in "Human gates." Everything else you decide yourself and log.

---

## 0. Start-of-session protocol (do this every time, in order)

1. Read this file completely.
2. If `handoff.md` exists, read it. **It is the source of truth for where the project is.** Resume from its "Next up" section. Do not redo completed work; verify it with a quick check (run tests / start the server) instead.
3. Read `Porchlight_Build_Guide.md` (the spec). On later sessions, re-read only the phases you're about to work on plus the Feedback register and Scope tiers.
4. Read `CONTEXT.md` if it exists (created in guide Phase 1).
5. If `handoff.md` does not exist, this is the first session: run **Bootstrap** (section 3).
6. Post a 3–5 line status to the human: current phase, what you're doing next, any open human gates. Then start working. Don't wait for a reply unless a gate requires it.

## 1. Sources of truth and precedence

When instructions conflict, follow this order:

1. The human's direct instructions in the current session
2. This file (AGENTS.md), especially the Hard rules
3. `handoff.md` decisions already made (don't flip-flop)
4. `Porchlight_Build_Guide.md` (the spec: phases, scope tiers, feedback register, formulas, prompts)
5. Your own judgment

`Porchlight_Build_Guide.md` is **read-only**. If you deviate from it (a library doesn't work, an API differs from what the guide says), record the deviation and the reason in `handoff.md → Decisions`, then continue.

## 2. Hard rules (never violate)

**Scope**
- Build in tier order: **all P0 → G2 → P1 → P2**. Never start P1 work until every P0 box in the guide is done and G2 is passed. Never start P2 until P1 is done or deliberately cut.
- If Community B (apartment complex) is costing significant time, cut it and keep A. Log the decision.
- No features outside the guide. If you think something is missing, add it to `handoff.md → Ideas (not approved)` and move on.

**AI / Meta API**
- Every AI call goes through `backend/app/ai/provider.py` (mock / live / cache / cost meter). No other file talks to the Meta API. The frontend never calls Meta directly.
- `AI_MODE=mock` is the default for all development and tests. Use live mode only to verify a specific Meta integration, then switch back.
- Respect the cost cap (`COST_CAP_USD=40`). Never raise it yourself. Check spend with `/api/usage` after any live testing and record it in `handoff.md`.
- Never guess Meta API details that aren't in the guide's verified table. If you need something undocumented (e.g., the Voice audio format or websocket protocol), fetch Meta's docs page if you have web access; otherwise raise a human gate asking for the docs page to be pasted.
- Groq or any non-Meta LLM must never be on in the demo path.

**Product rules (from the feedback register)**
- The AI drafts; the human sends. Never build auto-send.
- Member locations are fuzzed to block level in every API response via one serializer (`public_member()`). Exact addresses only after host approval.
- One schema for both communities; differences live only in seed files.
- All residents are fictional. No real personal data anywhere.

**Secrets and safety**
- Never commit `.env`, keys, or tokens. Never print a key in logs, chat, or `handoff.md`. Refer to keys by variable name only.
- Never enter credentials into anything yourself; the human puts keys in `.env`.
- No destructive operations outside this repo. No `git push --force`. No deleting the human's files.
- Don't spend money (domains, paid tiers, paid APIs beyond the Meta credit) without a human gate.

**Engineering**
- Don't claim something works until you've run it. "Done" means: the guide's "Done when" criteria are met, relevant tests pass, and you verified it by running it.
- Prefer boring, working code. Add a dependency only when the guide names it or you have a clear reason (log it).
- Commit after every completed task: `git commit -m "phase-N: <what>"`. Small commits. Only the lead agent commits when subagents are running in parallel.
- All code is written during the hackathon (this session). Don't copy code from other repos.

## 3. Bootstrap (first session only)

1. Confirm `Porchlight_Build_Guide.md` is present in the repo root. If not → human gate.
2. `git init` if needed. Create the folder layout from guide Phase 1.
3. Create `.env.example` exactly as in guide Phase 1. Create `.gitignore`.
4. Create `CONTEXT.md` from the template in guide Phase 1.
5. Create `handoff.md` from the template in section 9 of this file.
6. **Claude Code only:** create subagent definition files in `.claude/agents/` for each role in section 5 (frontmatter: `name`, `description`, `tools`; body: the role brief). If your tool can't load them until restart, spawn subagents directly with the role brief in the prompt instead.
7. Raise **Gate H1 (API key)** and **Gate H3 (design images)** immediately, in a single combined message (see "How to ask" in section 6), so the human can work on them while you build in mock mode.
8. Start Phase 2 without waiting.

## 4. Build plan

Follow the guide's phases. This table says who owns each phase, what can run in parallel, and where the human gates are.

| Guide phase | Owner | Parallel? | Human gate |
|---|---|---|---|
| 0 Meta access + smoke test | lead | — | **H1** key, **H2** workshop answers |
| 1 Repo + CONTEXT.md | lead | — | — |
| 2 Data model + seed | backend | first; others depend on it | — |
| 3 Backend API | backend | after contracts exist | — |
| 4 Graph engine | graph-ml | ∥ with 3, 5 | — |
| 5 Spark + provider + cost meter | ai-integration | ∥ with 3, 4 | H1 needed only for live check |
| 6 Voice | ai-integration | after 5's provider | H1; **H4** voice docs if unclear |
| 7 Design pass | design-prompter | start at bootstrap | **H3** images |
| 8 Frontend | frontend | ∥ once fixtures + API schema exist | uses H3 when available |
| 9 Wire loop + deploy → **G2** | lead + devops | — | **H5** deploy accounts, **H6** phone test |
| 10 Muse connector (P1) | ai-integration | — | **H8** Muse app test |
| 11 Join/waitlist + safety (P1) | backend | ∥ with 10, 12 | — |
| 12 Eval (P1) | graph-ml | ∥ with 10, 11 | — |
| 13 Muse Image (P2) | ai-integration | — | H1 |
| 14 Freeze + testing → **G3** | qa | — | — |
| 15 README + Devpost → **G4** | docs | — | **H7** final submit, **H9** optional domain |
| 16 Pitch prep | docs | — | — |

**Contracts before parallelism.** Before running backend, graph-ml, ai-integration and frontend in parallel, the lead writes:
- `backend/app/models.py` (pydantic schemas for every response)
- `API_SCHEMA.md` (the route table from guide Phase 3, with example JSON)
- `backend/app/ai/fixtures/*.json` (realistic mock outputs for nudge, draft, parse_invite, transcript)

Paste the route table and schemas into `CONTEXT.md`. Subagents build against these contracts and must not change them without telling the lead; contract changes are logged in `handoff.md → Decisions`.

**Mock-first rule.** Nothing waits on a human gate if it can be built in mock mode. Missing key → build and test everything in mock mode. Missing design images → build the frontend from the guide's style kernel and `theme.ts`, then restyle when images arrive.

## 5. Subagent roster

If your tool supports subagents (Claude Code's Task tool / `.claude/agents/`, or Codex's equivalent), delegate with these briefs. If it doesn't, play each role yourself, sequentially, using the same brief and file ownership.

Every subagent prompt must include: "Read AGENTS.md section 2 (Hard rules) and CONTEXT.md first," the task, the files it owns, and its "done when." Subagents return a short report: files changed, commands run, test results, open issues. **Subagents don't edit `handoff.md` or commit; the lead does.**

| Role | Owns (may edit) | Brief |
|---|---|---|
| **backend** | `backend/app/main.py`, `db.py`, `routes/`, `seed/`, `tests/test_api*.py` | Guide Phases 2, 3, 11. SQLite reseed on boot, `public_member()` fuzzing choke point, transactional join/waitlist, approval-gated location reveal. |
| **graph-ml** | `backend/app/graph.py`, `backend/eval/`, `tests/test_graph.py` | Guide Phases 4, 12. Pure functions, no network calls. Exact formulas from the guide. The eval includes the guide's caveat verbatim. |
| **ai-integration** | `backend/app/ai/`, `backend/app/mcp_server.py`, `scripts/smoke_spark.py`, `scripts/make_images.py` | Guide Phases 0 (script), 5, 6, 10, 13. The provider is the only Meta caller; cache, cost meter, cap, timeout, degraded flag. Developer-message rules from the guide. Never guess undocumented protocols. |
| **frontend** | `frontend/` | Guide Phases 7.4 (`theme.ts`), 8. Vite + React + TS + react-leaflet, mobile-first at 390px, editable composer with an explicit Send, animated Reach change, degraded-mode badge. |
| **design-prompter** | `design/PROMPTS.md` | Guide Phase 7. Writes the exact prompts for the human to run in Gemini or Canva, the filenames to save as, and then (once images exist) a short spec of what the frontend must match. Never generates images itself. |
| **devops** | `backend/Dockerfile`, `frontend/vercel.json`, `.github/workflows/`, `DEPLOY.md` | Guide Phases 9 (deploy), 14 (CI). ffmpeg in the image, MiniLM pre-downloaded at build, env vars documented, min-instances note. |
| **qa** | `tests/`, `docs/sample_outputs.md` | Guide Phase 14. Runs the full test suite, the mock-mode e2e, the cost-cap test, the safety grep test, and reports failures to the lead with the exact repro. Reviews other subagents' work against the Hard rules. |
| **docs** | `README.md`, `docs/`, `DEVPOST.md`, `PITCH.md` | Guide Phases 15, 16. README skeleton, Mermaid diagram, limitations, the eval table, Devpost text, the pitch script and Q&A. |

**Lead agent responsibilities:** contracts, delegation, merging, running the app end to end, commits, `handoff.md`, human gates, and making scope calls.

**Review loop:** after each phase, have **qa** (or yourself, in a fresh read) check the work against the phase's "Done when" and the Hard rules before marking it done.

## 6. Human gates (the only times you ask)

Ask only for these. For anything else, decide, log it in `handoff.md → Decisions`, and keep going.

| Gate | When | What you ask for | What you do while waiting |
|---|---|---|---|
| **H1** API key | Bootstrap | Put `META_MODEL_API_KEY` (and confirm `MUSE_SPARK_MODEL`) in `.env`; confirm the $50 credit is applied at dev.meta.ai | Build everything in mock mode |
| **H2** Workshop answers | Bootstrap (remind before Sat 3pm) | The answers to the 6 workshop questions in guide Phase 0, pasted into chat; you write them into `CONTEXT.md` | Continue; assume the defaults in the guide |
| **H3** Design images | Bootstrap | Give the human `design/PROMPTS.md` (style kernel + 5 screen prompts from guide Phase 7) and the exact filenames: `design/01-map-home.png`, `02-nudge-sheet.png`, `03-composer.png`, `04-voice-post.png`, `05-invite-detail.png` | Build the frontend from the style kernel and `theme.ts`; restyle when images land |
| **H4** Voice docs | Phase 6, only if the docs can't be fetched or are unclear | Paste Meta's speech-to-text doc (endpoint, audio format, protocol) | Mock transcript keeps the UI working |
| **H5** Deploy accounts | Phase 9 | Log in to the Vercel and GCP (or Render) CLIs yourself, or create the projects and tell me their names; set env vars in the host dashboards | Prepare the Dockerfile, vercel.json, DEPLOY.md |
| **H6** Phone test | Phase 9 and Phase 14 | Open the deployed URL on a phone, try a voice post, report what happened | Keep testing on desktop |
| **H7** Final submission | Before Sun 11:30am | Submit on Devpost using the prepared `DEVPOST.md` text; the human clicks submit | — |
| **H8** Muse app test | Phase 10 | Try the prepared Muse prompt in the human's Muse app (or Muse Code); report the result; screen-record if it works | Build the function-calling fallback |
| **H9** Spending / irreversible | Any time | Anything that costs money beyond the Meta credit (domain, paid tier, min-instances), raising the cost cap, or publishing anything | Skip and log in `handoff.md` |
| **H10** Real blocker | Any time | A decision that changes the thesis or cuts a P0 item | Work on something unblocked |

**How to ask** — one message, batched, never one question at a time:

```
🔔 NEEDS HUMAN (n items) — I'm continuing in mock mode meanwhile.

[H1] API key
  What: add META_MODEL_API_KEY=<your key> to .env (don't paste it in chat)
  Why: needed for the live Spark check (G1)
  How: dev.meta.ai → API keys → create. Ask at the Meta table / #ask-meta how the $50 credit is applied.

[H3] Design images
  What: run the 5 prompts in design/PROMPTS.md in Gemini (or Canva) and save them as the filenames listed there
  Why: the frontend will match them
  Time: ~30–45 min

Reply "done H1" / "done H3" when ready, or "skip H3" to keep the generated styling.
```

After asking, **never idle**. Keep working on unblocked tasks. Check for the gate's result (file exists, `.env` var set, a chat reply) at the start of each new task.

If the human says "skip" or doesn't respond and the deadline approaches, take the fallback in the table above and log it.

## 7. Verification commands (use them; don't assume)

```bash
# backend
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
AI_MODE=mock uvicorn app.main:app --reload            # then GET /api/health, /docs
pytest -q
AI_MODE=mock python -m app.seed_check                   # per-cluster Reach; gap cluster must be 0%

# live checks (only after H1, sparingly)
python scripts/smoke_spark.py                           # G1
AI_MODE=live uvicorn app.main:app                       # then hit /nudge once, then GET /api/usage

# frontend
cd frontend && npm install && npm run dev               # check at 390px width
npm run build
```

Create small helper scripts (like `seed_check`) when they make verification faster. Record exact run commands in `handoff.md → How to run`.

**Gate checks:**
- **G1:** `smoke_spark.py` prints text and a `usage` object.
- **G2:** on the deployed URL, the full core loop works (gap → nudge → draft → edit → send → mark as met → Reach updates) plus voice-to-pin, in live mode, 3 runs in a row, with the 2nd and 3rd being cache hits.
- **G3:** frozen; `pytest` green; mock-mode e2e passes with no key; cost-cap fallback verified; demo recording exists (human records it, H6).
- **G4:** README complete, `DEVPOST.md` ready, the human confirms final submission.

## 8. Time and deadline awareness

Ask the human for the current time only if you have no clock (`date` works in most shells). Event anchors (America/Chicago time):

- Meta workshop: Sat 3:00pm (remind about H2 before it)
- If G2 isn't close by the time the building reopens Sunday (6:30am), cut to the smallest working loop (Community A only, no voice confirm polish) and get it deployed before starting anything else.
- WEL building closed 11pm–6:30am (remind the human at 10:30pm)
- Feature freeze (G3): Sun ~9:00am
- Final submission: **Sun 11:30am**

At each phase boundary, compare progress to these anchors and make scope cuts early, following the tier order. Log every cut.

## 9. handoff.md — the continuity file

`handoff.md` must always be accurate enough that a fresh agent with zero memory can continue the project immediately. Treat it like a save file.

**When to update it**
- After every completed task (alongside the commit)
- Before starting any long-running or risky operation
- Whenever you raise or resolve a human gate
- Whenever you make a decision or deviate from the guide
- At least every ~20 tool calls even mid-task
- **Immediately** when any of these happen: the platform warns about context, usage, or rate limits; you notice context compaction or summarization; you've been working a long time and the conversation is very large; the human says they're stopping; you're about to end your turn

**Approaching limits protocol**

You can't always detect your remaining budget, which is why handoff.md is updated continuously rather than only at the end. When you suspect you're close to a limit:

1. Stop starting new tasks.
2. Finish or safely pause the current edit so the code builds; if it can't build, revert the partial change or document exactly what's broken.
3. Commit (`wip: <what>` if incomplete).
4. Do a full `handoff.md` update with every section filled.
5. Tell the human: "Handoff written. To continue, start a new session and say: *Read AGENTS.md and handoff.md, then continue.*"

**Template** (create it at bootstrap; keep every section, even if empty)

```markdown
# Porchlight — handoff

_Last updated: <date time> by <agent/session>_
_Current phase: <N — name>  |  Gates passed: G1 ☐ G2 ☐ G3 ☐ G4 ☐_

## TL;DR (3 lines max)
<where we are, what's next, what's blocking>

## Next up (do these in order)
1. <specific task, file, and command to verify>
2. ...

## In progress (exact state)
- Task: ...
- Files touched: ...
- State: builds? tests pass? what's half-done?
- Last command run + result: ...

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

## Decisions & deviations from the guide
| When | Decision | Why |
|---|---|---|

## Meta API facts confirmed
<model ID in use, voice path A/B, connector path, workshop answers>

## Spend
<total from /api/usage, by feature; cap 40; reserve 10>

## How to run
<exact commands for backend, frontend, tests, live check, deploy>

## Deployed URLs
<frontend, backend /api/health>

## Known issues / bugs
-

## Ideas (not approved)
-
```

## 10. Definition of done for the whole project

- G1–G4 passed
- Every P0 item works live on the deployed URL; P1 items done or explicitly cut and logged
- README matches the guide's skeleton, with the eval table, limitations and Mermaid diagram
- `DEVPOST.md` and `PITCH.md` written (demo script + judge Q&A from guide Phase 16)
- `handoff.md` final: all sections current, spend recorded, deployed URLs listed
- Final message to the human: what's live, what was cut, spend, and the 3 things to rehearse before judging
