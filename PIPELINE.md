# Discovery Pipeline — what was added

The components (embedding, clustering, scoring, risk gate, Groq) already
existed but were never connected. This adds the orchestration between them.
Nothing was rebuilt.

## Flow

```
CSV upload  ──►  parse + mask PII  ──►  Event log
                                          │
                          build one TRACE per case
                                          │
                                  embed traces
                                          │
                             cluster similar traces
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
        measure (deterministic)                    interpret (Groq LLM)
        frequency · handling time                  name · description
        rework · API readiness                     rule_based · sensitive
                    │                                           │
                    │                            harden_with_policy()
                    │                     LLM may only ESCALATE risk
                    └─────────────────────┬─────────────────────┘
                                          │
                            compute_value_score()   (Python)
                                          │
                              evaluate_risk()       (Python, no score input)
                                          │
                        Process + Score + attributed Events
                                          │
                                      Roadmap
```

## New files

| File | Responsibility |
|---|---|
| `app/pipeline/metrics.py` | Derives the six scoring factors from real events — volume, handling time, rework, API readiness. No LLM. |
| `app/pipeline/semantic.py` | Groq interpretation **plus** the deterministic policy that hardens it. |
| `app/pipeline/orchestrator.py` | `run_discovery()` — connects everything and persists results. |

## The safety property

Groq is upstream of the risk gate, which would normally be dangerous. It is
safe here because the combination is one-directional:

```python
sensitive_outcome = policy_says_sensitive OR llm_says_sensitive
fully_rule_based  = policy_says_rule_based AND llm_says_rule_based
```

A hallucinating, wrong, or prompt-injected model can only move a process
**toward** more human oversight, never away from it. `apply_policy()` matches
sensitive domains (payroll, tax, termination, medical, wire transfer…) by
deterministic pattern, and its verdict cannot be overridden by the model.

Verified by `test_policy_escalates_when_model_says_process_is_safe`: a model
that declares payroll tax filing safe and fully rule-based is overruled.

## Endpoints

- `POST /api/ingest` — upload CSV; runs discovery by default (`?discover=false` to skip)
- `POST /api/ingest/discover` — run discovery over events not yet attributed

Only unattributed events are considered, so re-running is additive, not
destructive.

## Demo

```bash
curl -F "file=@samples/work_log.csv" http://localhost:8000/api/ingest
curl http://localhost:8000/api/processes
```

Produces, from 532 raw events:

| Process | Score | Risk |
|---|---|---|
| Verify Invoice Vs Po | 78.6 | PRE_APPROVED |
| Review Vendor Onboarding Documents | 61.5 | HUMAN_IN_THE_LOOP |
| Payroll Tax Remittance And Filing | 42.6 | **TOO_RISKY** |

Requesting a blueprint for the payroll process returns **403** — on data that
was discovered, not seeded.

## Notes

- Without `sentence-transformers`, embedding degrades to deterministic lexical
  vectors. Previously this path returned zero vectors and **crashed** cosine
  clustering; that is fixed.
- Without `GROQ_API_KEY`, semantic analysis falls back to a conservative
  heuristic that assumes judgement is required. The pipeline still runs.
- Clusters with fewer than 2 cases are treated as noise, not processes.
