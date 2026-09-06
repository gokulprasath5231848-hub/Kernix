# KINTIX — AI-Powered Work Intelligence

**Intelligent Automation. Human Control.**

KINTIX analyzes fragmented organizational work data to discover recurring workflows, measure effort, score automation potential, and design human-gated blueprints.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your GROQ_API_KEY (optional — the pipeline runs without it)

# 2. Start everything
docker compose up -d

# 3. Open the dashboard
# Frontend: http://localhost:5173
# API docs: http://localhost:8000/docs
```

## Architecture

```
Source Layer (read-only) → Ingestion → Event Log (Postgres)
    → Discovery & Clustering → Scoring & Risk Gate
    → Blueprint Generation → React Dashboard
```

**Non-negotiable rules:**
- Ingestion is **read-only** — KINTIX never writes back to source systems
- Risk gate is a **pure function**, separate from scoring — a high score never overrides risk
- PII masking happens **at ingestion** — before storage, never at display layer
- Frontend **never renders a blueprint** for a TOO_RISKY process — defense in depth

## Project Structure

```
pok/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── web/              # React + Vite + Tailwind
├── docker-compose.yml
└── .env.example
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic |
| Intelligence | Sentence-BERT, scikit-learn, Groq LLM |
| PII Masking | Microsoft Presidio + spaCy |
| Frontend | React 18, Vite, Tailwind CSS, TanStack Query, React Router v6 |
| Infrastructure | Docker Compose |

## Brand

- Wordmark: white **KINTI** + gold **X**
- Tagline: *Intelligent Automation. Human Control.*
- Risk labels: **Pre-Approved** · **Human-in-the-Loop** · **Too Risky**

---

## End-to-end pipeline (CSV → Roadmap)

`POST /api/ingest` runs the full pipeline, not just storage:

```
CSV upload → parse + mask PII → event log → trace per case → embed →
cluster → measure (deterministic) → interpret (Groq) → harden by policy →
score (deterministic) → risk gate (deterministic) → ranked roadmap
```

```bash
curl -F "file=@samples/work_log.csv" http://localhost:8000/api/ingest
curl http://localhost:8000/api/processes
```

From the 532-event sample log this discovers:

| Process | Score | Risk |
|---|---|---|
| Verify Invoice Vs Po | 78.6 | Pre-Approved |
| Review Vendor Onboarding Documents | 61.5 | Human-in-the-Loop |
| Payroll Tax Remittance And Filing | 42.6 | **Too Risky** |

Requesting a blueprint for the payroll process returns **403** — on discovered
data, not seeded data.

Endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /api/ingest` | Upload CSV and discover processes (`?discover=false` to only store events) |
| `POST /api/ingest/discover` | Run discovery over events not yet attributed to a process |

Re-running is additive: only unattributed events are considered, so a second
upload never duplicates existing processes.

### Where the LLM sits, and why that is safe

Groq interprets each discovered process (name, description, whether it looks
rule-based or sensitive). It never computes the score and never makes the risk
decision. Its output is combined with deterministic policy one-directionally:

```python
sensitive_outcome = policy_says_sensitive OR llm_says_sensitive
fully_rule_based  = policy_says_rule_based AND llm_says_rule_based
```

A wrong, hallucinating or prompt-injected model can therefore only move a
process *toward* more human oversight, never away from it. See `PIPELINE.md`.

## Verification

The risk gate is the product's core promise, so it is enforced at four
independent layers and verified by tests at each one.

```bash
cd backend
pip install -e ".[dev]"   # core + test deps only — no 2.5GB ML download
pytest -q                 # 79 tests
```

| Layer | Enforcement | Test |
|---|---|---|
| Function signature | `evaluate_risk()` cannot receive a score | `test_risk_gate_ignores_score` |
| Generator | refuses before any Groq call | `test_precondition_blocks_too_risky` |
| API | `403`, not an empty `200` | `test_blueprint_forbidden_for_too_risky` |
| Frontend | route redirects away | `BlueprintPage.tsx` guard |
| Seed data | classifications derived from the gate, never hardcoded | `test_no_seeded_row_contradicts_the_risk_gate` |
| Semantic layer | an LLM can escalate risk but never reduce it | `test_policy_escalates_when_model_says_process_is_safe` |

### Manual check that matters most

The seeded catalog deliberately contains **"Payroll Tax Remittance & Filing"** —
the *highest-scoring process in the entire catalog* (97/100) — flagged
`sensitive_outcome = true`.

1. Open the Roadmap. It ranks **first** by score.
2. It still shows the red **Too Risky** badge, not gold.
3. Open it — "View Generated Blueprint" is not offered.
4. `GET /api/processes/{id}/blueprint` → **403 Forbidden**.

If a 97-scoring process is still blocked, the gate governs the product rather
than the score.

## Optional dependencies

The core install is intentionally light so tests and the API run without a
multi-gigabyte download. Both extras degrade gracefully when absent:

| Extra | Install | Without it |
|---|---|---|
| `ml` | `pip install -e ".[ml]"` | Embeddings fall back to deterministic lexical vectors; clustering still works |
| `pii` | `pip install -e ".[pii]"` | PII masking falls back to regex; names are not detected |

The Docker image installs `.[ml,pii]`, so the full stack is active there.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | Docker Postgres | Connection string |
| `GROQ_API_KEY` | *(empty)* | Used for semantic process analysis during discovery **and** blueprint generation |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model used for both semantic analysis and blueprints |
| `RUN_MIGRATIONS_ON_STARTUP` | `true` | Apply Alembic on boot |
| `SEED_DEMO_DATA` | `true` | Seed the 48-process demo catalog |

Groq is used at two points in the system:

1. **Semantic analysis during discovery** — naming a discovered process and
   judging whether it looks rule-based or sensitive. Its answers are then
   hardened by deterministic policy, which can only escalate risk.
2. **Blueprint generation** — producing the automation design for a process
   that has passed the risk gate.

Without a key, discovery still runs: semantic analysis falls back to a
conservative heuristic that assumes human judgement is required, so processes
are classified more cautiously rather than not at all. Generating *new*
blueprints is the only thing that stops working; the seeded demo blueprint
still renders.

## Migrations

Schema is owned by Alembic — `create_all` is only a fallback for throwaway test
databases.

```bash
cd backend
alembic upgrade head                      # apply
alembic revision --autogenerate -m "..."  # after changing models.py
```

## Known limitations

Deliberately deferred; see the implementation plan.

- **Clustering** uses embeddings + agglomerative clustering. Without
  `sentence-transformers` installed it degrades to deterministic lexical
  embeddings (hashed word and character n-grams), which still group obvious
  variants such as "verify invoice vs PO" and "Verify invoice against purchase
  order". Grouping quality is lower than with the model, but the pipeline
  produces real processes. (An earlier version returned zero vectors here,
  which made cosine distance undefined and crashed clustering outright.)
- **PII masking** falls back to regex if Presidio/spaCy are unavailable, which
  cannot detect names. The Docker image installs `en_core_web_sm` so the full
  NER path is active there.
- **No authentication.** Every request is unauthenticated — acceptable for a
  local demo, not for a pilot.
- Discovery treats clusters with fewer than 2 cases as noise, so genuinely
  one-off work never appears as an automation opportunity.
- Seed demo data still ships and is additive to discovered processes. Set
  `SEED_DEMO_DATA=false` to run a demo purely on uploaded data.
