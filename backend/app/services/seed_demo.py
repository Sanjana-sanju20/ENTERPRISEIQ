"""
Seeds an internally consistent, clearly labeled demonstration organization:
  Meridian Apex Corp (Demonstration Data)
Scenario:
  Q3-Q4 revenue declines from $1.56M/mo to $1.31M/mo while operational expenses rise
  from $910K/mo to $1.07M/mo (delivery surcharges + fleet maintenance) and customer
  complaints climb from 118/mo to 246/mo.
All dashboard KPIs, charts, anomalies, forecasts, documents, risks, reports, and
actions share these exact figures.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.engine import forecast_metric
from app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_CEO, ROLE_MANAGER, hash_password
from app.models.entities import (
    ActionItem,
    AnalysisJob,
    AuditLog,
    BusinessMetric,
    Department,
    Document,
    DocumentChunk,
    Finding,
    Forecast,
    Notification,
    Organization,
    Recommendation,
    ReportRecord,
    RiskRecord,
    Role,
    User,
)


async def seed_demo_data(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count(Organization.id)))).scalar_one()
    if existing > 0:
        return

    # 1. Roles
    roles = [
        Role(code=ROLE_CEO, name="CEO / Managing Director", permissions=["view:all", "approve:actions", "generate:reports"]),
        Role(code=ROLE_MANAGER, name="Department Manager", permissions=["view:department", "manage:actions", "view:reports"]),
        Role(code=ROLE_ANALYST, name="Business Analyst", permissions=["upload:documents", "run:analytics", "view:all"]),
        Role(code=ROLE_ADMIN, name="System Administrator", permissions=["admin:all", "view:audit_logs", "manage:users"]),
    ]
    db.add_all(roles)

    # 2. Demo Organization
    org = Organization(
        name="Meridian Apex Corp (Demo)",
        industry="B2B Logistics & Enterprise Supply Chain",
        is_demo=True,
    )
    db.add(org)
    await db.flush()

    # 3. 6 Departments
    dept_specs = [
        ("Finance", "Elena Vance", 76.0, 145000.0),
        ("Sales", "Marcus Chen", 68.0, 210000.0),
        ("Marketing", "Priya Nair", 82.0, 165000.0),
        ("Operations", "David Morales", 59.0, 420000.0),
        ("Human Resources", "Hannah Brooks", 86.0, 95000.0),
        ("Customer Support", "Aarav Patel", 61.0, 130000.0),
    ]
    depts: dict[str, Department] = {}
    for name, head, health, budget in dept_specs:
        d = Department(
            organization_id=org.id,
            name=name,
            head_name=head,
            health_score=health,
            budget_monthly=budget,
        )
        db.add(d)
        depts[name] = d
    await db.flush()

    # 4. Demo Users across all 4 roles (password: DemoPass123!)
    demo_pw = hash_password("DemoPass123!")
    users = [
        User(organization_id=org.id, role_code=ROLE_CEO, email="ceo@meridian-demo.com", full_name="Victoria Sterling (CEO)", hashed_password=demo_pw),
        User(organization_id=org.id, department_id=depts["Operations"].id, role_code=ROLE_MANAGER, email="ops.manager@meridian-demo.com", full_name="David Morales (Ops Manager)", hashed_password=demo_pw),
        User(organization_id=org.id, department_id=depts["Finance"].id, role_code=ROLE_ANALYST, email="analyst@meridian-demo.com", full_name="Sophia Lin (BI Analyst)", hashed_password=demo_pw),
        User(organization_id=org.id, role_code=ROLE_ADMIN, email="admin@meridian-demo.com", full_name="Alex Mercer (Sys Admin)", hashed_password=demo_pw),
    ]
    db.add_all(users)
    await db.flush()

    # 5. Internally Consistent 12-Month Time Series (2025-12 to 2026-11)
    monthly_data = [
        # period, revenue, rev_target, opex, opex_target, complaints, delivery_cost
        ("2025-12", 1480000, 1500000, 895000, 900000, 114, 215000),
        ("2026-01", 1510000, 1510000, 905000, 905000, 118, 218000),
        ("2026-02", 1535000, 1520000, 912000, 910000, 121, 222000),
        ("2026-03", 1560000, 1540000, 918000, 915000, 119, 224000),
        ("2026-04", 1550000, 1550000, 926000, 920000, 126, 230000),
        ("2026-05", 1525000, 1560000, 940000, 925000, 134, 239000),
        ("2026-06", 1490000, 1570000, 962000, 930000, 148, 254000),
        ("2026-07", 1445000, 1580000, 988000, 935000, 169, 272000),
        ("2026-08", 1405000, 1590000, 1015000, 940000, 192, 294000),
        ("2026-09", 1370000, 1600000, 1038000, 945000, 214, 315000),
        ("2026-10", 1338000, 1610000, 1056000, 950000, 231, 331000),
        ("2026-11", 1310000, 1620000, 1072000, 955000, 246, 348000),
    ]

    rev_series = []
    opex_series = []
    for period, rev, rev_t, opex, opex_t, complaints, deliv in monthly_data:
        profit = rev - opex
        profit_t = rev_t - opex_t
        rows = [
            BusinessMetric(organization_id=org.id, department_id=depts["Sales"].id, period=period, metric_name="revenue", actual_value=rev, target_value=rev_t, unit="USD", is_demo=True),
            BusinessMetric(organization_id=org.id, department_id=depts["Operations"].id, period=period, metric_name="operating_expenses", actual_value=opex, target_value=opex_t, unit="USD", is_demo=True),
            BusinessMetric(organization_id=org.id, department_id=depts["Finance"].id, period=period, metric_name="net_profit", actual_value=profit, target_value=profit_t, unit="USD", is_demo=True),
            BusinessMetric(organization_id=org.id, department_id=depts["Customer Support"].id, period=period, metric_name="customer_complaints", actual_value=complaints, target_value=120, unit="tickets", is_demo=True),
            BusinessMetric(organization_id=org.id, department_id=depts["Operations"].id, period=period, metric_name="delivery_cost", actual_value=deliv, target_value=230000, unit="USD", is_demo=True),
        ]
        db.add_all(rows)
        rev_series.append({"period": period, "metric_name": "revenue", "actual_value": rev})
        opex_series.append({"period": period, "metric_name": "operating_expenses", "actual_value": opex})

    # 6. Forecasts computed by real Statsmodels engine
    for fc in forecast_metric(rev_series, horizon=3) + forecast_metric(opex_series, horizon=3):
        db.add(
            Forecast(
                organization_id=org.id,
                metric_name=fc["metric_name"],
                period=fc["period"],
                predicted_value=fc["predicted_value"],
                lower_bound=fc["lower_bound"],
                upper_bound=fc["upper_bound"],
                model_used=fc["model_used"],
            )
        )

    # 7. Grounded Demonstration Documents & Chunks
    demo_docs = [
        (
            "Q4_2026_Operations_Cost_Audit_Demo.pdf",
            "pdf",
            "operational_audit",
            depts["Operations"].id,
            [
                ("Page 2 - Freight & Fuel", "Regional carrier fuel surcharges increased 28% between June and November 2026, pushing monthly delivery costs from $254,000 to $348,000. Emergency spot-market bookings accounted for 41% of the variance."),
                ("Page 4 - Fleet Maintenance", "Deferred preventive maintenance on 18 mid-mile delivery vehicles led to $64,000 in unscheduled repair overtime in October-November 2026 and caused 14% route delays across West & South corridors."),
            ],
        ),
        (
            "Q3_Q4_Sales_Pipeline_Review_Demo.docx",
            "docx",
            "sales_report",
            depts["Sales"].id,
            [
                ("Section 1 - Revenue Slippage", "Monthly revenue declined from $1.56M in March 2026 to $1.31M in November 2026 (-16.0%). Three enterprise renewals totaling $185K/mo were paused citing fulfillment SLA misses."),
                ("Section 3 - Discount Pressure", "Average renewal discount widened from 6.5% to 11.2% in Q4 to offset service-level friction, reducing gross margin."),
            ],
        ),
        (
            "Customer_Support_SLA_Escalations_Demo.xlsx",
            "xlsx",
            "customer_metrics",
            depts["Customer Support"].id,
            [
                ("Sheet 1 - Escalation Summary", "Monthly customer complaints rose from 118 in Jan 2026 to 246 in Nov 2026 (+108%). 62% of escalated tickets cite late deliveries; average first-response time degraded from 2.4 hours to 6.8 hours."),
            ],
        ),
        (
            "FY2026_Finance_Margin_Brief_Demo.pdf",
            "pdf",
            "financial_report",
            depts["Finance"].id,
            [
                ("Page 1 - Margin Compression", "Net profit margin compressed from 41.2% in March 2026 ($642K net profit) to 18.2% in November 2026 ($238K net profit). Operating expenses exceeded the $955K monthly target by $117K (+12.3%)."),
            ],
        ),
    ]

    for fname, ftype, cat, dept_id, chunks in demo_docs:
        doc = Document(
            organization_id=org.id,
            department_id=dept_id,
            uploaded_by=users[2].id,
            filename=fname,
            file_type=ftype,
            category=cat,
            status="Ready",
            is_demo=True,
            preview_text=chunks[0][1],
            processing_stats={
                "total_records": len(chunks) * 12,
                "invalid_records": 0,
                "missing_values": 0,
                "duplicate_records": 0,
                "extracted_tables": 1 if ftype in ("xlsx", "pdf") else 0,
                "generated_chunks": len(chunks),
            },
            validation_issues=[],
        )
        db.add(doc)
        await db.flush()
        for idx, (sec, text) in enumerate(chunks):
            db.add(
                DocumentChunk(
                    organization_id=org.id,
                    document_id=doc.id,
                    chunk_index=idx,
                    page_or_section=sec,
                    content=text,
                    metadata_json={"category": cat, "is_demo": True},
                )
            )

    # 8. AI Findings (with Root Cause Hypotheses + Methodology + Evidence)
    f1 = Finding(
        organization_id=org.id,
        department_id=depts["Finance"].id,
        category="profitability",
        title="Net Profit Margin Compressed 23 Points (41.2% → 18.2%)",
        finding="Monthly net profit dropped from $642K in March 2026 to $238K in November 2026 as revenue fell 16.0% while operational expenses rose 16.8%.",
        business_impact="Annualized operating cash flow run-rate has declined by ~$4.8M if current trajectory persists into Q1 2027.",
        root_cause_hypotheses=[
            {"factor": "Escalating delivery & spot-freight surcharges ($224K → $348K/mo)", "confidence": 0.89, "label": "Strong Hypothesis (Correlated + Documented)"},
            {"factor": "Deferred fleet maintenance causing unscheduled repairs & 14% route delays", "confidence": 0.84, "label": "Supported Hypothesis"},
            {"factor": "Enterprise renewal pauses ($185K/mo) linked to fulfillment SLA misses", "confidence": 0.81, "label": "Supported Hypothesis"},
        ],
        supporting_evidence=[
            {"document": "Q4_2026_Operations_Cost_Audit_Demo.pdf", "section": "Page 2 - Freight & Fuel", "metric": "Delivery cost +55.4% since Mar 2026"},
            {"document": "Q3_Q4_Sales_Pipeline_Review_Demo.docx", "section": "Section 1 - Revenue Slippage", "metric": "3 enterprise renewals paused ($185K/mo)"},
        ],
        severity="critical",
        confidence=0.87,
        methodology_note="Combined IsolationForest anomaly flags on 12-month Finance/Operations time series with RAG retrieval across Q3-Q4 audit reports. Correlation does not prove exclusive causation.",
        suggested_next_step="Renegotiate regional carrier contracts and restore preventive maintenance schedule immediately.",
    )
    f2 = Finding(
        organization_id=org.id,
        department_id=depts["Customer Support"].id,
        category="customer_experience",
        title="Customer Complaints Doubled (+108%) Alongside Fulfillment Delays",
        finding="Monthly support escalations climbed from 118 (Jan 2026) to 246 (Nov 2026), exceeding the 120-ticket threshold for six consecutive months.",
        business_impact="Elevated churn risk across mid-market and enterprise logistics accounts; renewal discounts widened from 6.5% to 11.2%.",
        root_cause_hypotheses=[
            {"factor": "14% route delays on West & South delivery corridors driving 62% of tickets", "confidence": 0.86, "label": "Strong Hypothesis"},
            {"factor": "Support first-response SLA degraded from 2.4h to 6.8h under ticket surge", "confidence": 0.82, "label": "Supported Hypothesis"},
        ],
        supporting_evidence=[
            {"document": "Customer_Support_SLA_Escalations_Demo.xlsx", "section": "Sheet 1 - Escalation Summary", "metric": "246 complaints in Nov 2026 vs 120 target"},
        ],
        severity="high",
        confidence=0.84,
        methodology_note="Cross-referenced Customer Support monthly ticket series with Operations route delay audit excerpts.",
        suggested_next_step="Deploy proactive delay alerts and assign dedicated escalation pod for top 20 accounts.",
    )
    db.add_all([f1, f2])
    await db.flush()

    # 9. Risk Records
    db.add_all([
        RiskRecord(
            organization_id=org.id,
            department_id=depts["Operations"].id,
            title="Uncontrolled Freight & Fleet Maintenance Cost Escalation",
            category="operational",
            severity="critical",
            probability=0.86,
            impact_score=0.91,
            financial_impact_usd=1450000.0,
            evidence=[{"source": "Q4_2026_Operations_Cost_Audit_Demo.pdf", "note": "OpEx $117K over target in Nov 2026"}],
            mitigation_plan="Lock fixed-rate regional carrier agreements and reinstate 30-day fleet preventive maintenance.",
            status="Active",
        ),
        RiskRecord(
            organization_id=org.id,
            department_id=depts["Sales"].id,
            title="Enterprise Account Churn from Fulfillment SLA Breaches",
            category="revenue",
            severity="high",
            probability=0.74,
            impact_score=0.85,
            financial_impact_usd=2220000.0,
            evidence=[{"source": "Q3_Q4_Sales_Pipeline_Review_Demo.docx", "note": "$185K/mo in paused enterprise renewals"}],
            mitigation_plan="Executive sponsor outreach + SLA service credits tied to verified on-time delivery recovery.",
            status="Active",
        ),
        RiskRecord(
            organization_id=org.id,
            department_id=depts["Customer Support"].id,
            title="Support Queue Backlog Breaching Contractual Response SLAs",
            category="customer",
            severity="high",
            probability=0.78,
            impact_score=0.72,
            financial_impact_usd=480000.0,
            evidence=[{"source": "Customer_Support_SLA_Escalations_Demo.xlsx", "note": "Response time 6.8h vs 2.4h baseline"}],
            mitigation_plan="Add temporary tier-2 triage capacity and automate shipment-delay notifications.",
            status="Active",
        ),
        RiskRecord(
            organization_id=org.id,
            department_id=depts["Finance"].id,
            title="Q1 2027 Operating Margin Dipping Below 15% Covenant Threshold",
            category="financial",
            severity="medium",
            probability=0.62,
            impact_score=0.80,
            financial_impact_usd=950000.0,
            evidence=[{"source": "FY2026_Finance_Margin_Brief_Demo.pdf", "note": "Current margin 18.2% with downward trend"}],
            mitigation_plan="Enforce weekly OpEx variance sign-off above $10K and accelerate Operations cost cap.",
            status="Monitoring",
        ),
    ])

    # 10. Recommendations
    db.add_all([
        Recommendation(
            organization_id=org.id,
            finding_id=f1.id,
            department_id=depts["Operations"].id,
            title="Consolidate Spot Freight into Fixed Regional Carrier Contracts",
            rationale="Spot-market bookings represent 41% of the $124K monthly delivery cost increase.",
            priority="critical",
            expected_impact="Estimated $55K-$75K/month OpEx reduction within 60 days",
        ),
        Recommendation(
            organization_id=org.id,
            finding_id=f2.id,
            department_id=depts["Customer Support"].id,
            title="Launch Proactive Delivery-Delay Alerts & VIP Escalation Desk",
            rationale="62% of the 246 monthly complaints originate from unannounced route delays.",
            priority="high",
            expected_impact="Target 35% complaint reduction and faster renewal close rates",
        ),
    ])

    # 11. Action Center Items (Kanban statuses)
    db.add_all([
        ActionItem(
            organization_id=org.id,
            department_id=depts["Operations"].id,
            assigned_to_name="David Morales",
            source_finding_id=f1.id,
            title="Renegotiate West & South Carrier Fuel Surcharge Caps",
            description="Replace spot-market carrier bookings with capped 12-month volume contracts.",
            priority="critical",
            status="In Progress",
            due_date="2026-12-12",
            progress_pct=55,
            baseline_metric="Delivery Cost: $348K/mo (Nov 2026)",
            comments=[{"author": "Victoria Sterling", "text": "Prioritize top 3 corridors before Q1 renewal cycle."}],
        ),
        ActionItem(
            organization_id=org.id,
            department_id=depts["Operations"].id,
            assigned_to_name="David Morales",
            source_finding_id=f1.id,
            title="Restore Preventive Maintenance Cycle for 18 Mid-Mile Vehicles",
            description="Clear deferred maintenance backlog to eliminate unscheduled roadside repairs.",
            priority="high",
            status="Open",
            due_date="2026-12-18",
            progress_pct=15,
            baseline_metric="Route Delays: 14% across West/South",
        ),
        ActionItem(
            organization_id=org.id,
            department_id=depts["Customer Support"].id,
            assigned_to_name="Aarav Patel",
            source_finding_id=f2.id,
            title="Deploy Automated Delay Notifications & Dedicated VIP Queue",
            description="Reduce inbound 'where is my shipment' escalations and cut first-response time under 3 hours.",
            priority="high",
            status="Under Review",
            due_date="2026-12-08",
            progress_pct=85,
            baseline_metric="Complaints: 246/mo | FRT: 6.8h",
            post_action_metric="Pilot cohort FRT reduced to 3.1h",
        ),
        ActionItem(
            organization_id=org.id,
            department_id=depts["Sales"].id,
            assigned_to_name="Marcus Chen",
            source_finding_id=f1.id,
            title="Executive Recovery Plan for 3 Paused Enterprise Renewals",
            description="Joint Sales + Operations SLA commitment calls for $185K/mo paused ARR.",
            priority="critical",
            status="Overdue",
            due_date="2026-11-22",
            progress_pct=40,
            baseline_metric="Paused Renewals: $185K/mo",
        ),
        ActionItem(
            organization_id=org.id,
            department_id=depts["Finance"].id,
            assigned_to_name="Elena Vance",
            title="Implement Weekly OpEx Variance Guardrail ($10K Approval Gate)",
            description="Require Finance review on unbudgeted departmental spend over $10K.",
            priority="medium",
            status="Completed",
            due_date="2026-11-15",
            progress_pct=100,
            baseline_metric="Unplanned spend visibility: Monthly lag",
            post_action_metric="Weekly automated variance flagging live",
            outcome_note="Rollout completed across all 6 departments; caught $22K duplicate vendor invoice.",
        ),
    ])

    # 12. Executive Report, Analysis Job, Notifications & Audit Log
    db.add(
        ReportRecord(
            organization_id=org.id,
            title="Executive Margin & Operations Diagnostic (Nov 2026 — Demo)",
            report_type="executive_summary",
            period_label="Dec 2025 – Nov 2026",
            departments_included=["Finance", "Operations", "Sales", "Customer Support"],
            summary_markdown=(
                "## Executive Summary (Demonstration Data)\n\n"
                "- **Revenue (Nov 2026):** $1,310,000 (-16.0% vs Mar 2026 peak of $1,560,000)\n"
                "- **Operating Expenses (Nov 2026):** $1,072,000 (+12.3% above $955,000 target)\n"
                "- **Net Profit Margin:** 18.2% (down from 41.2% in Mar 2026)\n"
                "- **Customer Complaints:** 246 tickets/month (+108% since Jan 2026)\n\n"
                "### Priority Management Actions\n"
                "1. Cap regional carrier spot-freight surcharges in Operations.\n"
                "2. Clear deferred maintenance on 18 mid-mile fleet vehicles.\n"
                "3. Execute joint Sales/Operations recovery calls for $185K/mo paused enterprise renewals."
            ),
            metrics_snapshot={"revenue": 1310000, "operating_expenses": 1072000, "net_profit": 238000, "profit_margin_pct": 18.2},
            created_by="Victoria Sterling (CEO)",
        )
    )
    db.add(AnalysisJob(organization_id=org.id, job_type="full_diagnostic", status="Completed", summary="Analyzed 12 months of metrics across 6 departments and indexed 4 operational documents."))
    db.add_all([
        Notification(organization_id=org.id, severity="critical", title="Critical OpEx Anomaly Detected", message="November Operating Expenses ($1.07M) exceeded target by 12.3% (+$117K)."),
        Notification(organization_id=org.id, severity="warning", title="Overdue Corrective Action", message="'Executive Recovery Plan for 3 Paused Enterprise Renewals' passed due date (2026-11-22)."),
        Notification(organization_id=org.id, severity="warning", title="Customer Complaints Threshold Breached", message="November complaints reached 246 vs 120 target (+105%)."),
    ])
    db.add(AuditLog(organization_id=org.id, actor_email="system@enterpriseiq.local", action="SEED_DEMO_ORG", target_type="organization", details="Initialized Meridian Apex Corp (Demo) dataset."))

    await db.commit()
