import datetime
import uuid
from sqlalchemy import String, Float, Boolean, DateTime, Integer, ForeignKey, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Events belong to the process they were clustered into. Nullable because raw
    # events exist in the log before discovery/clustering assigns them a process.
    process_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processes.id"), nullable=True, index=True
    )
    case_id: Mapped[str] = mapped_column(String)
    activity_raw: Mapped[str] = mapped_column(String)
    activity_normalised: Mapped[str] = mapped_column(String)
    event_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    actor_masked: Mapped[str] = mapped_column(String)
    system: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    process: Mapped["Process | None"] = relationship(back_populates="events")

class Process(Base):
    __tablename__ = "processes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    cases_per_month: Mapped[int] = mapped_column(Integer)
    steps: Mapped[int] = mapped_column(Integer)
    systems_touched: Mapped[int] = mapped_column(Integer)
    systems: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    
    score: Mapped["Score"] = relationship(back_populates="process", uselist=False, lazy="joined")
    blueprints: Mapped[list["Blueprint"]] = relationship(back_populates="process", lazy="selectin")
    events: Mapped[list["Event"]] = relationship(back_populates="process")

class Score(Base):
    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    process_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("processes.id"))
    frequency_volume: Mapped[float] = mapped_column(Float)
    manual_time: Mapped[float] = mapped_column(Float)
    rule_determinism: Mapped[float] = mapped_column(Float)
    api_readiness: Mapped[float] = mapped_column(Float)
    exception_frequency: Mapped[float] = mapped_column(Float)
    privacy_risk: Mapped[float] = mapped_column(Float)
    value_score: Mapped[float] = mapped_column(Float)
    sensitive_outcome: Mapped[bool] = mapped_column(Boolean)
    fully_rule_based: Mapped[bool] = mapped_column(Boolean)
    risk_decision: Mapped[str] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    scored_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    weights_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scoring_weights.id"), nullable=True)
    
    process: Mapped["Process"] = relationship(back_populates="score")

class ScoringWeights(Base):
    __tablename__ = "scoring_weights"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    weights: Mapped[dict] = mapped_column(JSON)
    effective_from: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    set_by: Mapped[str] = mapped_column(String, default="system")

class Blueprint(Base):
    __tablename__ = "blueprints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    process_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("processes.id"))
    steps: Mapped[list[dict]] = mapped_column(JSON)
    trigger: Mapped[str] = mapped_column(String)
    estimated_savings_hours: Mapped[float] = mapped_column(Float)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    process: Mapped["Process"] = relationship(back_populates="blueprints")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    process_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("processes.id"), nullable=True)
    action: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    detail: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
