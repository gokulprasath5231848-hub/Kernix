# Review Fixes — what changed and why

Applied to the generated codebase after end-to-end review. Every item was
either a bug that would have broken the demo, a regression against an agreed
design rule, or a gap between the plan and the code.

## Blockers (the app could not run)

| # | Issue | Fix |
|---|---|---|
| 1 | `main.py` imported `get_settings` from `app.config`, but it was defined in `app.database` — **the app could never start** | Moved `get_settings` into `config.py` so config has no dependency on the persistence layer |
| 2 | Frontend had **27 TypeScript errors and had never built** | Added `@types/node` + `vite-env.d.ts`, removed unused `React` imports from 21 files (automatic JSX runtime), fixed unused vars. Builds clean |
| 3 | Backend returned `{items, total_count}`; frontend expected an array — **roadmap table would render empty** | Client unwraps `.items` |
| 4 | `Event.id` used `uuid_generate_v4()`, requiring a Postgres extension never enabled — **inserts would fail** | `default=uuid.uuid4` |
| 5 | Engine created at import time — app unimportable without a DB driver | Lazy `get_engine()` / `get_sessionmaker()` |
| 6 | Backend Dockerfile ended in `\|\| true`, silently swallowing dependency install failures | Removed; a failed install now fails the build. Added spaCy model + healthcheck |

## Correctness

| # | Issue | Fix |
|---|---|---|
| 7 | Evidence trail was `select(Event).limit(20)` — returned **any** 20 events, not the process's own. Root cause: `Event` had no `process_id` | Added FK + index + relationship, scoped the query, linked seeded events |
| 8 | Seed **hardcoded** risk decisions, so demo data could contradict the gate | Decisions now derived from `evaluate_risk()` with an assertion |
| 9 | Seed produced 27/15/6, not the documented 28/14/6 | Corrected boundaries; locked by a test |
| 10 | `reevaluate` was a canned stub | Re-scores against active weights, re-derives risk, writes an audit entry |
| 11 | Stat cards computed counts from the **filtered** list — filtering to "Too Risky" showed 0 safe / 0 HITL | Counts come from the unfiltered catalog; divide-by-zero guarded |
| 12 | Models used Postgres-only `UUID`/`ARRAY`, blocking integration tests | Portable `Uuid`/`JSON` — same schema on Postgres and SQLite |

## Design regressions

| # | Issue | Fix |
|---|---|---|
| 13 | **"Deploy to Agent Worker Pool"** button returned — implied autonomous execution (contradicting the whole risk-gate premise) and was a fake `setTimeout` | Now **"Send to Approval Queue"**, wired to a real endpoint that re-checks the gate and writes an audit record. KINTIX recommends; a human authorises |

## Gaps closed

| # | Gap | Added |
|---|---|---|
| 14 | Alembic listed as a dependency but **no migrations existed** | Full setup + initial migration, verified to match ORM metadata with **zero drift** |
| 15 | Startup used `create_all`, so dev and prod schemas could diverge | Migrations run on boot; `create_all` only for throwaway test DBs |
| 16 | `test_pii_basic_functionality` ended in a bare `pass` — green while asserting nothing | Real assertions, plus a not-a-noop guard |
| 17 | No clustering tests | 7 tests using deterministic synthetic embeddings (no 80MB download) |
| 18 | No API tests | 13 integration tests against a real in-memory DB |
| 19 | No seed tests | 9 tests locking catalog size, distribution, gate consistency, idempotency |

## Results

- **Tests: 17 → 49**, all passing
- **Frontend: builds clean** (was 27 errors)
- **Migrations: verified zero drift** against ORM metadata
- **Live boot verified**: catalog 28/14/6; the 97-scoring `Payroll Tax Remittance & Filing` returns **403** on both the blueprint and approval endpoints; re-evaluation keeps it `TOO_RISKY`; evidence trails correctly scoped

## Not addressed (deliberately)

- No authentication — fine for a local demo, not a pilot
- `POST /ingest` masks and parses but does not run discovery end-to-end
- Clustering/PII quality depends on optional models; both degrade gracefully rather than crashing

---

# Pipeline connection + packaging fix

## Reported issue (independently verified by the user)

A clean extraction gave **47 passed, 32 errors** — `aiosqlite` missing.

**Root cause was not a missing declaration.** `aiosqlite` *was* listed in
`pyproject.toml`, but as dependency **#16 of 16**, behind
`sentence-transformers` (~2.5GB of torch), `presidio-analyzer` and `spacy`. If
that install fails or is interrupted — common on Windows — every dependency
after it silently never installs, and the async tests error out.

My earlier verification missed this because it installed dependencies
explicitly on the command line rather than through `pip install -e .`. That
proved the *code* worked but never proved the *manifest* was usable.

## Fix: dependency extras

| Group | Contents | Rationale |
|---|---|---|
| core | fastapi, sqlalchemy, asyncpg, alembic, numpy, scikit-learn | Everything needed to run the API and full pipeline |
| `[dev]` | pytest, pytest-asyncio, aiosqlite | Tests install in seconds, never blocked by an ML download |
| `[ml]` | sentence-transformers | Better embeddings; falls back to lexical vectors |
| `[pii]` | presidio, spacy | NER masking; falls back to regex |

`scikit-learn` stays in **core** deliberately: without it, clustering silently
collapses every process into one, which is worse than a slower install.

Docker installs `.[ml,pii]` so the running service has the full stack.

## Verified, following the README verbatim

```
pip install -e ".[dev]"   →  79 passed
torch / sentence_transformers / presidio  →  absent (correct)
pipeline on minimal install  →  3 processes discovered, gate holds
```

## README corrections

- Tagline → **"Intelligent Automation. Human Control."**
- Removed the stale line claiming `/ingest` does not run discovery — it does
- Added the end-to-end pipeline section, endpoints, and the LLM-safety property
- Documented optional-dependency degradation behaviour

## Secret removal (second occurrence)

The compromised Groq key was found a second time, hardcoded as a **default
value** in `docker-compose.yml`:

```yaml
GROQ_API_KEY: ${GROQ_API_KEY:-<REDACTED_KEY>}   # removed
```

Now:

```yaml
GROQ_API_KEY: ${GROQ_API_KEY:-}
GROQ_MODEL: ${GROQ_MODEL:-llama-3.3-70b-versatile}
```

No fallback value. An unset key is visibly absent rather than silently
replaced by someone's real credential. Supply it via a local `.env`, which is
gitignored and not shipped.

**The key remains compromised** — it was published in two files. Revoke it.
