# Porchlight deployment notes

## Local checks

The backend starts in `AI_MODE=mock` unless explicitly set to `live`. Run from `backend/` with Python 3.11 after `pip install -r requirements.txt`:

```powershell
python -m seed.generate_seed
python -m app.seed_check
python -m pytest -q tests
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, run `npm install`, then `npm run dev` or `npm run build`. Set `VITE_API_BASE=http://127.0.0.1:8000` for local development.

## Backend: Cloud Run or Render

Build `backend/Dockerfile` with `backend/` as the build context. It installs ffmpeg for the documented Muse Voice batch upload path and saves MiniLM inside the image at `/opt/minilm`, so a cold start does not download the model. The container listens on `$PORT` (default 8000).

Set these on the hosting service, never in the image or repository:

| Variable | Purpose |
|---|---|
| `META_MODEL_API_KEY` | Meta Model API credential; human enters it |
| `AI_MODE` | `mock` until H1/G1 pass; then `live` for the live demo |
| `META_API_BASE` | `https://api.meta.ai/v1` |
| `MUSE_SPARK_MODEL` | `muse-spark-1.3-contributor` for fictional demo data |
| `COST_CAP_USD` | `40`; do not raise without H9 |
| `PRICE_IN_PER_M` | `0.10` for contributor |
| `PRICE_OUT_PER_M` | `0.20` for contributor |
| `PRICE_VOICE_PER_MIN` | `0.003` per Meta Voice docs |
| `FRONTEND_ORIGIN` | Exact HTTPS frontend origin for CORS |
| `MCP_SHARED_SECRET` | Only if the P1 MCP server is enabled after G2 |

SQLite reseeds on boot so app state resets on cold starts. The usage ledger survives the Reset demo button and same-file process restarts, but an ephemeral host can lose its local ledger when an instance is replaced. Check Meta's account usage before and during judging; the $40 in-app cap is per persistent instance until durable storage is available. A minimum instance could reduce cold starts but has a cost and needs H9 approval. A free alternative is to open `/api/health` before each judge arrives.

## Frontend: Vercel

Set the project root to `frontend/`. Set `VITE_API_BASE` to the public HTTPS backend origin without a trailing slash. Build with `npm run build`; output directory is `dist`. `frontend/vercel.json` rewrites SPA routes to `index.html`.

Browser microphone access needs HTTPS on a phone. After H5 account setup, verify the full loop on the deployed URL and ask for H6 phone testing. Keep `AI_MODE=mock` on the backend until H1/G1 are verified, then make the planned live integration checks sparingly and record `/api/usage` spend in `handoff.md`.
