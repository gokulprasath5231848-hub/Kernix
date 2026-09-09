# Agentic execution layer.
#
# The discovery pipeline (app/pipeline) DISCOVERS automatable work and the risk
# gate (app/scoring/risk_gate) DECIDES whether an agent may touch it. This
# package is the missing third act: an agent that ACTS — it plans, calls tools,
# observes results and loops — but only ever inside the fence the gate drew.
#
#     PRE_APPROVED       -> the agent runs the whole blueprint autonomously
#     HUMAN_IN_THE_LOOP  -> the agent does the safe prep, then STOPS at the first
#                           consequential write and asks a human
#     TOO_RISKY          -> the agent refuses to start at all
#
# The gate is enforced in code, not by the model. A confused, wrong or
# prompt-injected model can only ever be stopped earlier — never pushed past the
# fence. That is the same one-directional-safety principle as
# app/pipeline/semantic.py:harden_with_policy, now applied to an actor instead of
# a classifier.
