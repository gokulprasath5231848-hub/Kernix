# Implementation Plan — Process Intelligence & Automation Blueprints

Build-out plan for the two sidebar pages that currently render "Coming Soon"
placeholders (`web/src/App.tsx`, the `process-intelligence` and `blueprints`
routes). Ordered easiest-first. Written to match the conventions already in the
codebase.

## Ground rules (match existing patterns)

- **Backend router** → new file in `backend/app/api/`, registered in
  `backend/app/main.py` with `app.include_router(x.router, prefix="/api")`.
- **Schemas** → `backend/app/schemas.py`, Pydantic with
  `model_config = ConfigDict(from_attributes=True)`.
- **DB session** → `db: AsyncSession = Depends(get_db_session)`.
- **Async relationships** → `Process.score` is `lazy="joined"`, but `events` and
  `blueprints` are **not** eager. Use explicit `select()` queries; never
  lazy-access an un-loaded relationship in async code (raises `MissingGreenlet`).
- **Frontend** → add TS interface in `web/src/types.ts`, method in the `api`
  object (`web/src/api/client.ts`), hook in `web/src/hooks/useProcesses.ts`, page
  in `web/src/pages/`, then swap the placeholder element in `web/src/App.tsx`.
- **Design tokens** → reuse `surface-container-*`, `outline-variant`, `primary`,
  `status-*`. Reuse `RiskBadge`, `StatCard`, and the table markup from
  `web/src/pages/AuditPage.tsx` / `web/src/components/roadmap/RoadmapTable.tsx`.
- **Type-check after each page**:
  `docker exec kintix_web sh -c "cd /app && npx tsc --noEmit -p tsconfig.app.json"`

---

## PAGE 1 — Automation Blueprints (build first; ~½ day)

**Goal:** one catalog of every process's blueprint + status, with actions.

### Backend

1. **New schema** in `schemas.py`:

```python
class BlueprintCatalogItem(BaseModel):
    process_id: uuid.UUID
    process_name: str
    department: Optional[str]
    risk_decision: RiskDecision
    value_score: float
    blueprint_id: Optional[uuid.UUID] = None
    generated_at: Optional[datetime.datetime] = None
    estimated_savings_hours: Optional[float] = None
    status: str   # "Blocked" | "Not Generated" | "Draft" | "Awaiting Approval"
```

2. **New router** `backend/app/api/catalog.py`, `prefix="/blueprints"`:

```python
@router.get("", response_model=list[BlueprintCatalogItem])
async def list_blueprints(db=Depends(get_db_session)):
    # 1. processes + score  -> select(Process).outerjoin(Process.score)
    # 2. blueprints         -> {process_id: Blueprint}
    # 3. approvals          -> set of process_ids with AuditLog.action == "SUBMITTED_FOR_APPROVAL"
    # 4. status logic:
    #      TOO_RISKY                -> "Blocked"
    #      no blueprint             -> "Not Generated"
    #      blueprint + submitted    -> "Awaiting Approval"
    #      blueprint, not submitted -> "Draft"
```

3. Register in `main.py`: `app.include_router(catalog.router, prefix="/api")`.

> Reuse the existing `Blueprint` model, `/generate`, and `/submit-for-approval`
> endpoints in `backend/app/api/blueprints.py` — you only need this one **list**
> endpoint.

### Frontend

4. `types.ts` → `BlueprintCatalogItem` interface (mirror the schema).
5. `client.ts` → add:

```ts
getBlueprintsCatalog: () => fetchAPI<BlueprintCatalogItem[]>('/api/blueprints'),
generateBlueprint: (id: string) =>
  fetchAPI<Blueprint>(`/api/processes/${id}/blueprint/generate`, { method: 'POST' }),
```

   (`submitForApproval` already exists.)
6. `useProcesses.ts` → `useBlueprintsCatalog()` (useQuery) + `useGenerateBlueprint()`
   / `useSubmitForApproval()` mutations that `invalidateQueries(['blueprints'])`.
7. **New page** `pages/BlueprintsPage.tsx`:
   - Top: 4 `StatCard`s — total processes, blueprints generated, awaiting approval, blocked.
   - Table (copy AuditPage's `<table>`): Process · Risk (`RiskBadge`) · Score ·
     Status badge · Est. hrs · Actions.
   - Status → colored pill (small map, or reuse `RISK_COLORS` style).
   - Actions by status:
     - **Not Generated** → "Generate" (mutation, spinner, disabled if `Blocked`)
     - **Draft** → "View" (`/process/{id}/blueprint`) + "Submit"
     - **Awaiting Approval** → "View" only
     - **Blocked** → disabled + tooltip
   - Status filter chips (reuse the `RiskFilterBar` idea).
8. `App.tsx` → replace the `path: 'blueprints'` element with `<BlueprintsPage />`.

### Edge cases / acceptance

- Generate calls Groq → can be slow / rate-limited; show a spinner and surface
  `APIError.message` on failure.
- `TOO_RISKY` → never allow generate/submit (backend already 403s; disable in UI too).
- **Done when:** the page lists all processes with correct status, Generate
  creates a blueprint and the row flips to "Draft", Submit flips it to
  "Awaiting Approval", and it survives a refresh.

---

## PAGE 2 — Process Intelligence (build second; ~1–1.5 days)

**Goal:** show *how* a discovered process flows — step map, path variants, bottlenecks.

### Backend

1. **New schemas** in `schemas.py`:

```python
class FlowNode(BaseModel):    activity: str; count: int; avg_minutes: float; systems: list[str]
class FlowEdge(BaseModel):    source: str; target: str; count: int
class FlowVariant(BaseModel): sequence: list[str]; case_count: int; pct: float
class ProcessIntelligence(BaseModel):
    process_id: uuid.UUID; name: str; case_count: int
    nodes: list[FlowNode]; edges: list[FlowEdge]; variants: list[FlowVariant]
    rework_rate: float
```

2. **New endpoint** — add to `processes.py` (or a new `intelligence.py`):

```python
@router.get("/{process_id}/intelligence", response_model=ProcessIntelligence)
```

   Logic (reuse the trace-building pattern in `backend/app/pipeline/orchestrator.py`
   and `backend/app/pipeline/metrics.py`):
   - `select(Event).where(Event.process_id == id)`, group by `case_id`, sort by `event_time`.
   - Build each case's ordered activity trace (dedup consecutive repeats — same as orchestrator).
   - **nodes** = activity frequency + avg step duration (Δ between consecutive `event_time`) + systems seen.
   - **edges** = count of each consecutive `(a → b)` pair.
   - **variants** = `Counter(tuple(trace))` → top N with `pct = case_count / total`.
   - **rework_rate** = reuse the marker/repeat logic from `compute_process_metrics`.

### Frontend

3. `types.ts` + `client.ts` (`getProcessIntelligence(id)`) +
   `useProcessIntelligence(id)` hook.
4. **New page** `pages/ProcessIntelligencePage.tsx` — the route
   `/process-intelligence` has **no id**, so:
   - Add a **process selector** at top (dropdown from `useProcesses()`), default to
     the first / highest-scoring. Store selection in `useState` or `?process_id=`
     search param (like `AuditPage` does).
   - **Flow map** — for MVP, reuse `web/src/components/blueprint/StepFlow.tsx` to
     render the dominant variant's node chain, with each edge labeled by its
     transition count and each node showing avg minutes + a "hot" highlight when
     it's the slowest / most-reworked.
   - **Variants table** — each distinct path + `case_count` + `pct` bar.
   - **Bottlenecks panel** — top 3 slowest nodes and highest-rework activities.
5. `App.tsx` → replace the `path: 'process-intelligence'` element with
   `<ProcessIntelligencePage />`.

### Visualization note

- **MVP:** StepFlow chain + variant table + bottleneck cards — no new dependency.
- **Nicer graph (optional, v2):** render a Mermaid `flowchart LR` string from
  `nodes`/`edges`. Inside the Vite app this needs the `mermaid` npm package.

### Acceptance

- **Done when:** selecting a process shows its real step sequence, the variant
  table sums to 100% of cases, and durations/rework come from actual event
  timestamps (verify against `/api/processes/{id}` evidence trail).

---

## Suggested order & effort

1. **Automation Blueprints** — 1 backend endpoint + 1 page. Lower risk, immediately useful.
2. **Process Intelligence** — 1 heavier endpoint (trace aggregation) + 1 page with a
   selector and the StepFlow-based map.

## Testing each

- Backend: `curl http://localhost:8000/api/blueprints` and
  `.../api/processes/{id}/intelligence` — verify JSON shape before wiring the UI.
- Frontend: run the `tsc --noEmit` check above after each page.
- Reuse-of-relationships gotcha: eager-load or explicitly `select()`; don't
  lazy-access `events` / `blueprints` in async handlers.
