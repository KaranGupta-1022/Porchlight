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

### Cloud Run sequence after H5 and H9

Use project ID supplied by the human. The selected region is `us-central1`, service name `porchlight-api`, minimum instances `0`, and maximum instances `1`. Do not paste the Meta key into the shell or a CLI flag. The human enters it in the Cloud Run service environment settings after the first mock deployment.

```powershell
gcloud auth login
gcloud config set project <GCP_PROJECT_ID>
gcloud run deploy porchlight-api --source backend --region us-central1 --allow-unauthenticated --min-instances 0 --max-instances 1 --set-env-vars AI_MODE=mock,COST_CAP_USD=40,META_API_BASE=https://api.meta.ai/v1,MUSE_SPARK_MODEL=muse-spark-1.3-contributor,PRICE_IN_PER_M=0.10,PRICE_OUT_PER_M=0.20,PRICE_VOICE_PER_MIN=0.003
```

Read the printed service URL and verify `<BACKEND_URL>/api/health` and `/docs`. The Dockerfile is used for `gcloud run deploy --source backend` when it exists in that directory, as documented by [Cloud Run source deployments](https://docs.cloud.google.com/run/docs/deploying-source-code). The Cloud Run source build uses Cloud Build and Artifact Registry; check billing before running it. Once Vercel has returned its exact HTTPS origin, set `FRONTEND_ORIGIN` to that origin in Cloud Run. The human sets `META_MODEL_API_KEY` in Cloud Run's environment settings; after G1 and local live checks pass, set `AI_MODE=live` there and verify `/api/usage` after any live request. Avoid redeploying with `--set-env-vars` after setting the key because that flag replaces all existing variables; use the dashboard or `--update-env-vars` for non-secret updates.

## Frontend: Vercel

Set the project root to `frontend/`. Set `VITE_API_BASE` to the public HTTPS backend origin without a trailing slash. Build with `npm run build`; output directory is `dist`. `frontend/vercel.json` rewrites SPA routes to `index.html`.

Browser microphone access needs HTTPS on a phone. After H5 account setup, verify the full loop on the deployed URL and ask for H6 phone testing. Keep `AI_MODE=mock` on the backend until H1/G1 are verified, then make the planned live integration checks sparingly and record `/api/usage` spend in `handoff.md`.

### Vercel sequence after the backend URL exists

The selected project name is `porchlight-ui`, root directory `frontend/`, output directory `dist`. The human signs in with `vercel login` (or links an existing project) and handles any account terms. Set `VITE_API_BASE` to `<BACKEND_URL>` in the Vercel project's Production environment settings so later builds retain it. Run the CLI from the repository root because the Vercel project has `frontend/` configured as its Root Directory:

```powershell
npx vercel link
npx vercel deploy --prod
```

If the project is linked to the Git repository, `npx vercel link --repo` can link it from the repo root instead. If the project is created in Vercel's dashboard, set its root directory to `frontend/` and build command to `npm run build`. Copy the resulting HTTPS origin into Cloud Run's `FRONTEND_ORIGIN`. Open the deployed URL on two phones for H6, then run the live core loop three times and inspect `/api/usage` for cache hits. No custom domain or minimum instance is in scope without a separate H9 approval.
