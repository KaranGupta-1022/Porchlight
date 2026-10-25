# Porchlight deployment notes

## Local checks

The backend defaults to `AI_MODE=mock`. Run from `backend/` with Python 3.11 after `pip install -r requirements.txt`:

```powershell
python -m seed.generate_seed
python -m app.seed_check
python -m pytest -q tests
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, run `npm install`, then `npm run dev` or `npm run build`. Set `VITE_API_BASE=http://127.0.0.1:8000` only if bypassing Vite's local `/api` proxy.

## Backend: Render Free

`render.yaml` defines one Free Docker web service, `porchlight-api`, using `backend/Dockerfile` with `backend/` as the build context. The Dockerfile installs ffmpeg and `backend/requirements.deploy.txt`, copies the precomputed MiniLM interest vectors from `backend/seed/interest_embeddings.json`, and listens on `$PORT` at `0.0.0.0`. Torch and the MiniLM model are development-only; the 384-dimensional vectors were computed from the fictional seed ahead of deployment. Regenerate them with `python backend/seed/precompute_vectors.py` if the seed changes. The app defaults to `AI_MODE=mock`; the Blueprint disables automatic service deployments and contains no credentials. Do not import the Blueprint or create a public service until H5 account setup and H9 public deployment approval are complete.

After H5/H9:

1. The human signs in to [Render](https://dashboard.render.com/), connects the repository through a Git provider, and creates a new Blueprint from the root `render.yaml`. Confirm that `porchlight-api` uses the **Free** plan before approving the initial deployment. Blueprint creation starts the first build and deployment even though later automatic deployments are disabled.
2. Wait for the build and open `<BACKEND_URL>/api/health` and `<BACKEND_URL>/docs`. `/api/health` should report `ai_mode: mock`. Record the actual HTTPS `onrender.com` origin.
3. The human enters `META_MODEL_API_KEY` in Render's service Environment settings. Do not put the key in `render.yaml`, the image, commands, or chat. After the Vercel URL exists, set `FRONTEND_ORIGIN` there to its exact HTTPS origin. For the live Contributor path, set `AI_MODE=live`, `MUSE_SPARK_MODEL=muse-spark-1.3-contributor`, `PRICE_IN_PER_M=0.10`, and `PRICE_OUT_PER_M=0.20` together, then choose **Save and deploy**. Check `/api/usage` after live calls.
4. Manually deploy any later committed changes from Render's service dashboard because the Blueprint sets `autoDeployTrigger: off`.

For a single Standard Spark access trial, change only `MUSE_SPARK_MODEL=muse-spark-1.3`, `PRICE_IN_PER_M=1.25`, and `PRICE_OUT_PER_M=4.25` in Render's service Environment page; leave `META_MODEL_API_KEY`, `AI_MODE=live`, and `COST_CAP_USD=40` unchanged. Choose **Save and deploy**, wait for `/api/health`, make one nudge request, and inspect `degraded` and `/api/usage`. Return all three model/price settings to Contributor values if Standard fails. [Meta's prices](https://dev.meta.ai/docs/pricing-rate-limits) are per million tokens. Render's [Environment page](https://render.com/docs/configure-environment-variables) applies dashboard changes on Save and deploy; a manual service deploy does not itself sync the Blueprint. A Blueprint sync can replace values that are hardcoded in `render.yaml`, so `AI_MODE`, `MUSE_SPARK_MODEL`, and token prices are omitted from it. Render [preserves existing environment variables omitted from a Blueprint](https://render.com/docs/blueprint-spec), including the human-entered key. The Blueprint still fixes `COST_CAP_USD=40`, `META_API_BASE=https://api.meta.ai/v1`, and the Voice price. `MCP_SHARED_SECRET` is needed only if the P1 MCP server is enabled after G2. Keep `AI_MODE=mock` for routine development and tests.

Render [spins down Free web services after 15 minutes without inbound traffic](https://render.com/docs/free); the next request can take about a minute to wake the service. Open `<BACKEND_URL>/api/health` shortly before each demo. The Free filesystem is ephemeral: spin-down, restart, or redeploy erases local SQLite state, cached AI responses, and the local usage ledger. The app reseeds on boot, so the demo starts clean, but run G2's three live loops in one warm session to observe cache hits. The $40 in-app cap cannot span instance replacement; check Meta account usage before and during judging. Render Free has a 512 MB RAM limit, so the slim container's startup and memory use must be verified after deployment. No paid plan or persistent disk is in scope.

## Frontend: Vercel

After H5/H9, the human signs in to Vercel, imports the repository, and creates `porchlight-ui` on the Hobby plan if the project qualifies for its [personal, noncommercial restriction](https://vercel.com/docs/plans/hobby). Set **Root Directory** to `frontend/`, framework to Vite, build command to `npm run build`, output directory to `dist`, and Production `VITE_API_BASE` to the Render HTTPS origin without a trailing slash. Deploy; `frontend/vercel.json` rewrites SPA routes to `index.html`. Vercel documents the [Root Directory setting for monorepos](https://vercel.com/docs/monorepos).

If deploying the already linked project with Vercel CLI, run it from the repository root because the project Root Directory is `frontend/`:

```powershell
npx vercel link --repo
npx vercel deploy --prod
```

Set the resulting exact Vercel HTTPS origin as Render's `FRONTEND_ORIGIN` and verify CORS from that page. Browser microphone access needs HTTPS on a phone. Ask for H6 phone testing after deployment: open the URL on two phones and record a voice post on each. Run the full live core loop three times in one warm Render session and inspect `/api/usage` for cache hits before marking G2 passed. No custom domain or paid service is authorized.
