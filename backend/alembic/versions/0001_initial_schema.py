"""Initial KINTIX schema.

Creates the six core tables. Note the ordering: scoring_weights and processes
must exist before the tables that reference them.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scoring_weights",
        sa.Column("id", sa.Uuid(), nullable=False),
        # Versioned, never updated in place: a score from March stays
        # explainable against the weights that were active in March.
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("set_by", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("department", sa.String(), nullable=True),
        sa.Column("cases_per_month", sa.Integer(), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("systems_touched", sa.Integer(), nullable=False),
        sa.Column("systems", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        # Nullable: raw events land in the log before clustering assigns them
        # to a process.
        sa.Column("process_id", sa.Uuid(), nullable=True),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("activity_raw", sa.String(), nullable=False),
        sa.Column("activity_normalised", sa.String(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        # Masked at ingestion, before this row is ever written.
        sa.Column("actor_masked", sa.String(), nullable=False),
        sa.Column("system", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_process_id", "events", ["process_id"])

    op.create_table(
        "scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("frequency_volume", sa.Float(), nullable=False),
        sa.Column("manual_time", sa.Float(), nullable=False),
        sa.Column("rule_determinism", sa.Float(), nullable=False),
        sa.Column("api_readiness", sa.Float(), nullable=False),
        sa.Column("exception_frequency", sa.Float(), nullable=False),
        sa.Column("privacy_risk", sa.Float(), nullable=False),
        sa.Column("value_score", sa.Float(), nullable=False),
        # Risk inputs are stored alongside the decision so the classification
        # can always be re-derived and audited.
        sa.Column("sensitive_outcome", sa.Boolean(), nullable=False),
        sa.Column("fully_rule_based", sa.Boolean(), nullable=False),
        sa.Column("risk_decision", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("scored_at", sa.DateTime(), nullable=False),
        sa.Column("weights_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.ForeignKeyConstraint(["weights_id"], ["scoring_weights.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scores_process_id", "scores", ["process_id"])
    op.create_index("ix_scores_risk_decision", "scores", ["risk_decision"])

    op.create_table(
        "blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("estimated_savings_hours", sa.Float(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_blueprints_process_id", "blueprints", ["process_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("process_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["process_id"], ["processes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("blueprints")
    op.drop_table("scores")
    op.drop_table("events")
    op.drop_table("processes")
    op.drop_table("scoring_weights")
