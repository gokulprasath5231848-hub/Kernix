import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Process, Score, ScoringWeights, Event, Blueprint, AuditLog
from app.constants import SCORING_WEIGHTS, RiskDecision
from app.scoring.risk_gate import evaluate_risk

async def seed_database(session: AsyncSession):
    count = await session.scalar(select(func.count(Process.id)))
    if count and count > 0:
        # Existing demo databases may predate audit entries for every process.
        # Backfill one immutable catalog/risk entry per process without
        # duplicating rows on subsequent startups.
        processes = (await session.execute(select(Process))).scalars().all()
        existing = set((await session.execute(select(AuditLog.process_id))).scalars().all())
        added = False
        for process in processes:
            if process.id in existing:
                continue
            detail = (
                f"Catalog snapshot · score={process.score.value_score if process.score else 'n/a'} · "
                f"risk={process.score.risk_decision if process.score else 'UNSCORED'}"
            )
            session.add(AuditLog(
                process_id=process.id,
                action="CATALOG_SNAPSHOT",
                actor="system",
                detail=detail,
            ))
            added = True
        if added:
            await session.commit()
        return
        
    weights = ScoringWeights(weights=SCORING_WEIGHTS)
    session.add(weights)
    await session.commit()
    await session.refresh(weights)
    
    processes_data = [
        # 1. "Expense Reconciliation & Audit"
        {
            "name": "Expense Reconciliation & Audit", "department": "Finance", 
            "cases": 1240, "steps": 5, "systems": ["SAP ERP", "Workday", "Coupa"],
            "risk": RiskDecision.PRE_APPROVED, "sensitive": False, "rule_based": True,
            "f_v": 90, "m_t": 95, "r_d": 95, "a_r": 90, "e_f": 90, "p_r": 90, "score": 92.0
        },
        # 2. "Tier-1 Ticket Auto-Triage & Routing"
        {
            "name": "Tier-1 Ticket Auto-Triage & Routing", "department": "Customer Ops", 
            "cases": 8900, "steps": 3, "systems": ["Zendesk", "Jira", "Slack"],
            "risk": RiskDecision.PRE_APPROVED, "sensitive": False, "rule_based": True,
            "f_v": 95, "m_t": 80, "r_d": 80, "a_r": 90, "e_f": 70, "p_r": 90, "score": 84.0
        },
        # 3. "Vendor Onboarding Compliance Verification"
        {
            "name": "Vendor Onboarding Compliance Verification", "department": "Procurement", 
            "cases": 340, "steps": 6, "systems": ["D&B", "DocuSign", "NetSuite"],
            "risk": RiskDecision.HUMAN_IN_THE_LOOP, "sensitive": False, "rule_based": False,
            "f_v": 60, "m_t": 85, "r_d": 70, "a_r": 80, "e_f": 80, "p_r": 90, "score": 78.0
        },
        # 4. "Daily Cash Position & Liquidity Sweep"
        {
            "name": "Daily Cash Position & Liquidity Sweep", "department": "Treasury", 
            "cases": 30, "steps": 4, "systems": ["Bloomberg", "JPM Portal", "Kyriba"],
            "risk": RiskDecision.HUMAN_IN_THE_LOOP, "sensitive": False, "rule_based": False,
            "f_v": 40, "m_t": 90, "r_d": 75, "a_r": 80, "e_f": 70, "p_r": 80, "score": 74.0
        },
        # 5. "Core Banking Ledger Reconciliation"
        {
            "name": "Core Banking Ledger Reconciliation", "department": "Banking Ops", 
            "cases": 12, "steps": 8, "systems": ["Core Mainframe", "Fedwire"],
            "risk": RiskDecision.TOO_RISKY, "sensitive": True, "rule_based": True,
            "f_v": 20, "m_t": 60, "r_d": 50, "a_r": 20, "e_f": 50, "p_r": 60, "score": 41.0
        },
        # 6. "Employee Offboarding Access Revocation"
        {
            "name": "Employee Offboarding Access Revocation", "department": "IT Security", 
            "cases": 85, "steps": 4, "systems": ["Okta", "Active Directory", "Google WS"],
            "risk": RiskDecision.PRE_APPROVED, "sensitive": False, "rule_based": True,
            "f_v": 70, "m_t": 90, "r_d": 100, "a_r": 90, "e_f": 90, "p_r": 90, "score": 89.0
        },
        # 7. THE CRITICAL TRUST-BUILDING ROW
        {
            "name": "Payroll Tax Remittance & Filing", "department": "Finance", 
            "cases": 24, "steps": 5, "systems": ["ADP", "IRS FIRE", "State DOR APIs"],
            "risk": RiskDecision.TOO_RISKY, "sensitive": True, "rule_based": True,
            "f_v": 85, "m_t": 95, "r_d": 100, "a_r": 98, "e_f": 95, "p_r": 99, "score": 97.0
        }
    ]
    
    # Generate 41 more to reach the documented catalog of 48 processes with a
    # 28 / 14 / 6 risk distribution.
    #   explicit rows above contribute:  3 safe, 2 HITL, 2 risky
    #   generated rows contribute:      25 safe, 12 HITL, 4 risky
    for i in range(8, 49):
        if i <= 32:  # 25 generated + 3 explicit = 28 safe
            risk = RiskDecision.PRE_APPROVED
            sensitive = False
            rule_based = True
            sc = 80.0
        elif i <= 44:  # 12 generated + 2 explicit = 14 HITL
            risk = RiskDecision.HUMAN_IN_THE_LOOP
            sensitive = False
            rule_based = False
            sc = 70.0
        else:  # 4 generated + 2 explicit = 6 too risky
            risk = RiskDecision.TOO_RISKY
            sensitive = True
            rule_based = True
            sc = 50.0
            
        processes_data.append({
            "name": f"Generated Process {i}", "department": "Ops", 
            "cases": 100, "steps": 5, "systems": ["SysA", "SysB"],
            "risk": risk, "sensitive": sensitive, "rule_based": rule_based,
            "f_v": sc, "m_t": sc, "r_d": sc, "a_r": sc, "e_f": sc, "p_r": sc, "score": sc
        })
        
    process_1_id = None

    for pd in processes_data:
        p = Process(
            name=pd["name"],
            department=pd["department"],
            cases_per_month=pd["cases"],
            steps=pd["steps"],
            systems_touched=len(pd["systems"]),
            systems=pd["systems"]
        )
        session.add(p)
        await session.flush()
        
        if pd["name"] == "Expense Reconciliation & Audit":
            process_1_id = p.id
            
        # The risk decision is DERIVED from the gate, never hardcoded in seed data.
        # This makes it impossible for demo data to display a classification the
        # real gate would not produce.
        decision, reason = evaluate_risk(
            sensitive_outcome=pd["sensitive"],
            fully_rule_based=pd["rule_based"],
        )
        assert decision == pd["risk"], (
            f"Seed row '{pd['name']}' expects {pd['risk']} but the risk gate "
            f"produces {decision}. Fix the seed data, not the gate."
        )

        s = Score(
            process_id=p.id,
            frequency_volume=pd["f_v"], manual_time=pd["m_t"], rule_determinism=pd["r_d"],
            api_readiness=pd["a_r"], exception_frequency=pd["e_f"], privacy_risk=pd["p_r"],
            value_score=pd["score"], sensitive_outcome=pd["sensitive"], fully_rule_based=pd["rule_based"],
            risk_decision=decision.value,
            reason=reason,
            weights_id=weights.id
        )
        session.add(s)

    # Add events for #1
    dt_base = datetime.datetime(2025, 2, 24, 10, 14, tzinfo=datetime.timezone.utc)
    events = [
        Event(process_id=process_1_id, case_id="ev_99182", activity_raw="Coupa API invoice parsed ($14,200.00)", activity_normalised="coupa api invoice parsed 14200 00", event_time=dt_base + datetime.timedelta(seconds=2), actor_masked="sys_worker_4", system="Coupa"),
        Event(process_id=process_1_id, case_id="ev_99183", activity_raw="SAP GL Ledger 4100 matching line item confirmed", activity_normalised="sap gl ledger 4100 matching line item confirmed", event_time=dt_base + datetime.timedelta(seconds=5), actor_masked="sys_worker_4", system="SAP"),
        Event(process_id=process_1_id, case_id="ev_99184", activity_raw="Workday cost center verification: CC_FIN_NA approved", activity_normalised="workday cost center verification cc fin na approved", event_time=dt_base + datetime.timedelta(seconds=8), actor_masked="sys_worker_4", system="Workday"),
        Event(process_id=process_1_id, case_id="ev_99155", activity_raw="Batch run 420 receipts verified against corporate Amex feed", activity_normalised="batch run 420 receipts verified against corporate amex feed", event_time=dt_base - datetime.timedelta(minutes=30), actor_masked="sys_worker_2", system="Amex"),
    ]
    session.add_all(events)
    
    # Add blueprint for #1
    bp = Blueprint(
        process_id=process_1_id,
        trigger="HTTP POST (Coupa Webhook)",
        estimated_savings_hours=120.0,
        steps=[
            {"name": "Coupa Webhook Event", "description": "Receive webhook", "system": "Coupa", "requires_approval": False},
            {"name": "Multi-Modal Parser", "description": "Parse invoice", "system": "Internal", "requires_approval": False},
            {"name": "Two-Way Match Engine", "description": "Match lines", "system": "SAP", "requires_approval": False},
            {"name": "Governance Boundary", "description": "Approve if >$50k", "system": "Internal", "requires_approval": True, "approval_condition": "Amount > $50k"},
            {"name": "SAP GL Clearing", "description": "Clear GL", "system": "SAP", "requires_approval": False}
        ]
    )
    session.add(bp)
    
    # Audit log
    al = AuditLog(process_id=process_1_id, action="Scored Process", actor="System", detail="Score calculated as 92")
    session.add(al)
    
    await session.commit()
