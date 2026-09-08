# KINTIX — From Scratch to Live: Free-Tier Full-Stack Deployment Playbook

A knowledge-transfer document. It captures **what we built, every hurdle we hit, and the exact fix for each**, so an AI assistant (or a human) can replay the same process on a future project. Written to be pasted into an LLM as context.

---

## 1. What the project is

**KINTIX** — an "Automation Opportunity Miner". You upload a raw work-event log (CSV) and it:
- mines the events into distinct **process types** (clustering),
- scores each on a **Viability Index**,
- classifies each into a **risk tier** (Pre-Approved / Human-in-the-Loop / Too Risky) using a keyword policy + an LLM,
- and presents a governance dashboard (roadmap, process intelligence, blueprints, audit log).

Tagline: *"Autonomous intelligence, human control."*

### Architecture (3 tiers)
| Tier | Tech | Deployed on (final) |
|------|------|---------------------|
| Frontend | React 18 + Vite 6 + TypeScript + Tailwind, React Router, TanStack Query | **Netlify** (static) |
| Backend | FastAPI + SQLAlchemy async + asyncpg + Alembic; Groq LLM for classification | **Render** (Docker, free web service) |
| Database | PostgreSQL 16 | **Neon** (serverless Postgres, free) |

Repo: `gokulprasath5231848-hub/Kernix`, branch `main`.

---

## 2. The goal & the hosting decision

Goal: **a live deployment that costs $0**.

Decision path:
1. **Railway** — easiest (runs all 3 from `docker-compose`), but the free "$5 trial credit" is one-time and drains in ~1–2 weeks, then suspends. Good for a short demo, **not** permanent-free. (We started here, then the credit ran out.)
2. **Final free stack (stays live):**
   - Frontend → **Netlify** (or Vercel/Cloudflare Pages) — truly free, no sleep.
   - Backend → **Render** free web service — free, but **sleeps after ~15 min idle** (~40s cold start).
   - DB → **Neon** — free serverless Postgres, auto-wakes (better than Supabase which pauses after 7 days idle).

**Key lesson:** a 3-tier app is not "one free host". Split it: static CDN for the frontend, a small always-reachable server for the API, managed Postgres for data.

---

## 3. The hurdles and their fixes (the important part)

Each hurdle = a real problem we hit, its root cause, and the fix.

### H1. Monorepo build failed on the host
- **Symptom:** Railway/Render tried to build the repo root; no app there → "could not determine how to build."
- **Cause:** `backend/` and `web/` are subfolders; the builder needs to know which.
- **Fix:** Set **Root Directory** per service (`backend`, `web`). On Render, **Dockerfile Path is relative to repo root even when Root Directory is set** — so `backend/Dockerfile`.

### H2. App bound to a hardcoded port
- **Cause:** Hosts inject a dynamic `$PORT`; Dockerfile hardcoded 8000/5173.
- **Fix:** `CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]` (and same for Vite).

### H3. Vite dev server blocked the host
- **Symptom:** "Blocked request. This host is not allowed."
- **Cause:** Vite 6 blocks unknown hosts by default.
- **Fix:** `server.allowedHosts: true` in `vite.config.ts`. (Only relevant if serving the dev server; on Netlify we serve a static build instead — see H8.)

### H4. CORS blocked the frontend
- **Cause:** FastAPI `allow_origins` was hardcoded to localhost.
- **Fix:** Make it an env var `CORS_ORIGINS` (comma-separated), read into the middleware. Set it to the exact frontend URL (`https://<site>`, **no trailing slash**). Note: `allow_credentials=True` is incompatible with `*`, so set the real origin.

### H5. asyncpg rejected the managed DB URL
- **Cause 1:** Managed providers hand out `postgresql://...`; SQLAlchemy async needs `postgresql+asyncpg://...`.
- **Cause 2:** Neon/Supabase append `?sslmode=require` (and `channel_binding`) — libpq params that **asyncpg rejects**.
- **Fix:** Normalize the URL: swap the scheme to `+asyncpg`, **strip** `sslmode`/`channel_binding`, and re-apply SSL via `connect_args={"ssl": True}` for any non-localhost host. Apply in both the app engine and Alembic's `env.py`.
- **Supabase note:** use the **Session pooler** connection string (port 5432, IPv4). Avoid the Direct connection (IPv6, unreachable from Render) and the Transaction pooler (port 6543, breaks asyncpg prepared statements).

### H6. Backend OOM'd the 512 MB free instance (biggest one)
- **Symptom:** Docker build pulled `torch` (554 MB) + `nvidia-*` CUDA libs (~1.5 GB) + sentence-transformers/spaCy/presidio; would OOM on boot.
- **Cause:** The image installed heavy ML extras `.[ml,pii]`.
- **Fix:** Default the image to **core deps only**. The app already **degrades gracefully** (lexical embeddings instead of sentence-transformers; regex PII instead of Presidio). Made extras opt-in via a Docker build-arg (`PIP_EXTRAS=".[ml,pii]"`) and gated the spaCy model download on Presidio being present.
- **Lesson:** On a 512 MB free host, **never ship torch/CUDA**. Check `pyproject.toml` for optional extras and confirm the code has import-guarded fallbacks before trimming.

### H7. Neon CLI onboarding steps were unnecessary
- **Cause:** Neon's console suggested `neon skills / mcp / config init / neon.ts / neon deploy` — that's their app-deploy/agent tooling.
- **Fix:** Ignore all of it. We only needed **the connection string** from the console → paste as `DATABASE_URL`.

### H8. Netlify folder drag lost the `assets/` folder
- **Symptom:** Site loaded `index.html` but JS/CSS returned 404 → blank app.
- **Cause:** Dragging a nested folder onto Netlify Drop uploaded only the top file.
- **Fix:** **Zip the build output and drag the ZIP.** Critical Windows gotcha: PowerShell `Compress-Archive` writes **backslash** path separators that Netlify mis-reads → assets 404 again. Build the zip with **forward-slash** entry names (via `System.IO.Compression.ZipArchive`, replacing `\` with `/`).

### H9. SPA deep links 404'd
- **Cause:** React Router client routes have no server files.
- **Fix:** SPA fallback. Netlify: a `public/_redirects` file with `/*  /index.html  200`. Vercel: `vercel.json` with a rewrite of `/(.*)` → `/index.html`.

### H10. Build-time env var
- **Cause:** `VITE_API_URL` is inlined into the static bundle at **build time**.
- **Fix:** Build with it set: `VITE_API_URL="https://<backend>" npm run build`. (On Vercel it's a project env var; for a manual Netlify zip, bake it at build.)

### H11. Demo showed canned seed data
- **Cause:** `SEED_DEMO_DATA` defaults on → seeds 48 demo processes on first boot.
- **Fix:** Set `SEED_DEMO_DATA=false` on the host so it starts empty; upload a work log to populate. (Setting it false does **not** delete existing rows — use the Reset feature, H13.)

### H12. Login gate (done securely)
- **Requirement:** password-protect the app.
- **Wrong way:** checking the password in the frontend (visible in the JS bundle — trivially bypassed).
- **Right way:** credentials live **server-side** as env vars (`AUTH_EMAIL`, `AUTH_PASSWORD`, `AUTH_SECRET`). Backend `POST /api/auth/login` compares with `hmac.compare_digest` (constant-time) and returns an **HMAC-signed, time-limited token**. Frontend stores the token, a `RequireAuth` route guard gates the dashboard, logout clears it. Sensitive endpoints check the token via a `require_auth` dependency.

### H13. Reset feature
- **Need:** clear stored data between demos.
- **Fix:** `POST /api/admin/reset` deletes processes/events/scores/blueprints/audit logs (keeps scoring weights), guarded by the session token. Frontend "Danger Zone → Reset all data" button with a confirm dialog that invalidates cached queries.

### H14. "Only a few processes / all Too Risky"
- **Not a bug.** It's a **process miner**, not a log viewer: it clusters N log lines into a handful of process *types*. And a mono-theme log (all IT/identity) trips the sensitive-keyword policy (`diagnos`, identity/access) → all red.
- **Fix:** feed a **multi-department** log so the board spans green/amber/red. We generated a synthetic 29-process, 6-department log (Finance/HR/Sales/Procurement/Customer Ops/Ops/Legal) with families designed to land in each tier. Sensitive domains (payroll/tax/termination/medical/legal/wire) are **hard-locked red** by the keyword policy regardless of the LLM.

### H15. Uploads *append*, don't replace
- **Symptom:** counts doubled (58 instead of 29).
- **Fix:** always **Reset before uploading**.

### H16. Groq free-tier rate limits degraded classification
- **Symptom:** usage graph showed requests (~57) and tokens (~10.2K) spiking above the free limits (~30 req/min, ~9K tokens/min) during an upload burst of ~29 LLM calls.
- **Effect:** 429s → those processes fell back to the conservative heuristic → board skewed red.
- **Fix:** switch `GROQ_MODEL` to a **higher-limit model** — `llama-3.3-70b-versatile` produced correct output with no throttling. (Endpoint stays Groq.) Alternative: pre-load the board before the demo so no live LLM calls happen.

### H17. Made the LLM provider swappable
- Added `LLM_API_URL` env var (defaults to Groq). Point it at NVIDIA (`https://integrate.api.nvidia.com/v1/chat/completions`) or any OpenAI-compatible endpoint by setting `LLM_API_URL` + `GROQ_API_KEY` + `GROQ_MODEL`. Caveat: not all providers accept `response_format: json_object`; the code falls back to the heuristic if a call fails.

### H18. `/login` didn't redirect a logged-in user
- **Cause:** called `navigate()` during render (React doesn't honor it).
- **Fix:** `return <Navigate to="/" replace />` instead. (Found during a QA pass.)

---

## 4. Final environment variables

**Backend (Render):**
```
DATABASE_URL   = <Neon connection string, pasted as-is>
GROQ_API_KEY   = <Groq API key>
GROQ_MODEL     = llama-3.3-70b-versatile
CORS_ORIGINS   = https://<your-netlify-site>        # exact, no trailing slash
AUTH_EMAIL     = <operator email>
AUTH_PASSWORD  = <a fresh password, server-side only>
AUTH_SECRET    = <long random string, e.g. secrets.token_urlsafe(48)>
SEED_DEMO_DATA = false
# optional: LLM_API_URL to switch provider
```
**Frontend (build-time):**
```
VITE_API_URL = https://<your-render-backend>
```

---

## 5. Deploy sequence (repeatable)

1. **Neon** → create project → copy connection string.
2. **Render** → New Web Service → connect repo → Root Directory `backend`, Dockerfile Path `backend/Dockerfile`, Free instance → add backend env vars (CORS_ORIGINS=`*` temporarily) → deploy → copy backend URL. Verify `GET /health`.
3. **Netlify** → build frontend with `VITE_API_URL=<backend URL>` → zip `dist` (forward-slash entries) → drag ZIP onto the site's Deploys → copy site URL.
4. **Close the CORS loop** → set backend `CORS_ORIGINS` to the exact Netlify URL → redeploy.
5. Log in → **Reset** → **Upload CSV** once.

---

## 6. Reusable checklist for ANY free-tier full-stack deploy

- [ ] Split tiers: static CDN (frontend) + small server (API) + managed Postgres.
- [ ] Bind the server to `$PORT`, not a hardcoded port.
- [ ] Set per-service Root Directory in a monorepo; know where the host expects the Dockerfile.
- [ ] Make CORS origins an env var; set to the exact deployed frontend URL.
- [ ] Normalize managed Postgres URLs for your driver (scheme + strip libpq-only params + SSL).
- [ ] Keep the server image lean — no torch/CUDA on a 512 MB host; confirm graceful fallbacks before trimming ML deps.
- [ ] Frontend env vars that are build-time (Vite `VITE_*`) must be set at build.
- [ ] Add an SPA fallback (`_redirects` / `vercel.json` rewrite).
- [ ] Zip static output with forward-slash paths when hand-uploading (Windows gotcha).
- [ ] Protect the app server-side (never check secrets in the browser).
- [ ] Free API/LLM tiers rate-limit bursts — pace calls, pick a higher-limit model, or pre-load results.
- [ ] Know your host's free-tier caveats: Render sleeps (~15 min), Neon auto-wakes, Supabase pauses after 7 days, Railway credit is one-time.

---

*Generated as a portable playbook. Feed this whole file to an AI assistant as context to replay the process on a new project.*
