from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.models.entities import (
    ActionItem,
    AnalysisJob,
    BusinessMetric,
    Department,
    Finding,
    Organization,
    Recommendation,
    ReportRecord,
    RiskRecord,
    User,
)
from app.core.database import get_db

router = APIRouter(prefix="/api", tags=["Dashboard & Departments"])


async def compute_kpi_snapshot(db: AsyncSession, org_id: str) -> dict:
    metrics = (
        await db.execute(
            select(BusinessMetric)
            .where(BusinessMetric.organization_id == org_id)
            .order_by(BusinessMetric.period.asc())
        )
    ).scalars().all()

    by_period: dict[str, dict[str, float]] = defaultdict(dict)
    targets_by_period: dict[str, dict[str, float]] = defaultdict(dict)
    for m in metrics:
        by_period[m.period][m.metric_name] = m.actual_value
        if m.target_value is not None:
            targets_by_period[m.period][m.metric_name] = m.target_value

    periods = sorted(by_period.keys())
    if not periods:
        return {
            "latest_period": "N/A",
            "revenue": 0.0,
            "net_profit": 0.0,
            "profit_margin_pct": 0.0,
            "operating_expenses": 0.0,
            "customer_complaints": 0.0,
            "revenue_change_pct": 0.0,
            "opex_change_pct": 0.0,
            "business_health_score": 0.0,
            "trends": [],
        }

    latest = periods[-1]
    baseline = periods[max(0, len(periods) - 4)]  # Quarter-over-quarter baseline

    rev = by_period[latest].get("revenue", 0.0)
    opex = by_period[latest].get("operating_expenses", 0.0)
    profit = by_period[latest].get("net_profit", rev - opex)
    complaints = by_period[latest].get("customer_complaints", 0.0)
    margin = (profit / rev * 100.0) if rev > 0 else 0.0

    base_rev = by_period[baseline].get("revenue", rev) or 1.0
    base_opex = by_period[baseline].get("operating_expenses", opex) or 1.0
    rev_change = ((rev - base_rev) / base_rev) * 100.0
    opex_change = ((opex - base_opex) / base_opex) * 100.0

    # Transparent business health index (0-100) derived from actual margin, revenue trend, and OpEx control
    health = max(25.0, min(98.0, 62.0 + (margin * 0.6) + (rev_change * 0.8) - max(0.0, opex_change * 0.9)))

    trends = []
    for p in periods:
        r = by_period[p].get("revenue", 0.0)
        o = by_period[p].get("operating_expenses", 0.0)
        pr = by_period[p].get("net_profit", r - o)
        trends.append({
            "period": p,
            "revenue": r,
            "revenue_target": targets_by_period[p].get("revenue"),
            "operating_expenses": o,
            "opex_target": targets_by_period[p].get("operating_expenses"),
            "net_profit": pr,
            "profit_margin_pct": round((pr / r * 100.0) if r > 0 else 0.0, 1),
            "customer_complaints": by_period[p].get("customer_complaints", 0.0),
            "delivery_cost": by_period[p].get("delivery_cost", 0.0),
        })

    return {
        "latest_period": latest,
        "revenue": round(rev, 2),
        "net_profit": round(profit, 2),
        "profit_margin_pct": round(margin, 1),
        "operating_expenses": round(opex, 2),
        "customer_complaints": round(complaints, 0),
        "revenue_change_pct": round(rev_change, 1),
        "opex_change_pct": round(opex_change, 1),
        "business_health_score": round(health, 1),
        "trends": trends,
    }


@router.get("/dashboard/overview")
async def dashboard_overview(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(Organization).where(Organization.id == user.organization_id))).scalar_one()
    snap = await compute_kpi_snapshot(db, user.organization_id)
    depts = (await db.execute(select(Department).where(Department.organization_id == user.organization_id))).scalars().all()
    top_finding = (
        await db.execute(select(Finding).where(Finding.organization_id == user.organization_id).order_by(Finding.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    top_risk = (
        await db.execute(select(RiskRecord).where(RiskRecord.organization_id == user.organization_id).order_by(RiskRecord.impact_score.desc()).limit(1))
    ).scalar_one_or_none()
    top_rec = (
        await db.execute(select(Recommendation).where(Recommendation.organization_id == user.organization_id).order_by(Recommendation.created_at.desc()).limit(1))
    ).scalar_one_or_none()
    actions = (
        await db.execute(select(ActionItem).where(ActionItem.organization_id == user.organization_id).order_by(ActionItem.created_at.desc()).limit(5))
    ).scalars().all()
    reports = (
        await db.execute(select(ReportRecord).where(ReportRecord.organization_id == user.organization_id).order_by(ReportRecord.created_at.desc()).limit(3))
    ).scalars().all()
    last_job = (
        await db.execute(select(AnalysisJob).where(AnalysisJob.organization_id == user.organization_id).order_by(AnalysisJob.created_at.desc()).limit(1))
    ).scalar_one_or_none()

    return {
        "organization": {"id": org.id, "name": org.name, "is_demo": org.is_demo},
        "last_analysis_at": last_job.created_at.isoformat() if last_job else None,
        "kpis": {k: v for k, v in snap.items() if k != "trends"},
        "trends": snap["trends"],
        "departments": [
            {"id": d.id, "name": d.name, "head_name": d.head_name, "health_score": d.health_score, "budget_monthly": d.budget_monthly}
            for d in depts
        ],
        "intelligence_panel": {
            "key_insight": {"id": top_finding.id, "title": top_finding.title, "summary": top_finding.finding, "confidence": top_finding.confidence} if top_finding else None,
            "critical_risk": {"id": top_risk.id, "title": top_risk.title, "severity": top_risk.severity, "financial_impact_usd": top_risk.financial_impact_usd} if top_risk else None,
            "recommended_action": {"id": top_rec.id, "title": top_rec.title, "expected_impact": top_rec.expected_impact, "priority": top_rec.priority} if top_rec else None,
        },
        "pending_actions": [
            {"id": a.id, "title": a.title, "status": a.status, "priority": a.priority, "due_date": a.due_date, "assigned_to_name": a.assigned_to_name, "progress_pct": a.progress_pct}
            for a in actions
        ],
        "latest_reports": [
            {"id": r.id, "title": r.title, "report_type": r.report_type, "period_label": r.period_label, "created_at": r.created_at.isoformat()}
            for r in reports
        ],
    }


@router.get("/dashboard/trends")
async def dashboard_trends(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    snap = await compute_kpi_snapshot(db, user.organization_id)
    return {"latest_period": snap["latest_period"], "trends": snap["trends"]}


@router.get("/departments")
async def list_departments(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    depts = (await db.execute(select(Department).where(Department.organization_id == user.organization_id))).scalars().all()
    risks = (await db.execute(select(RiskRecord).where(RiskRecord.organization_id == user.organization_id))).scalars().all()
    actions = (await db.execute(select(ActionItem).where(ActionItem.organization_id == user.organization_id))).scalars().all()

    out = []
    for d in depts:
        d_risks = [r for r in risks if r.department_id == d.id]
        d_actions = [a for a in actions if a.department_id == d.id]
        out.append({
            "id": d.id,
            "name": d.name,
            "head_name": d.head_name,
            "health_score": d.health_score,
            "budget_monthly": d.budget_monthly,
            "active_risks_count": len(d_risks),
            "open_actions_count": len([a for a in d_actions if a.status != "Completed"]),
        })
    return out


@router.get("/departments/{dept_id}")
async def get_department_detail(dept_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    d = (
        await db.execute(select(Department).where(Department.id == dept_id, Department.organization_id == user.organization_id))
    ).scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Department not found.")

    metrics = (
        await db.execute(
            select(BusinessMetric)
            .where(BusinessMetric.organization_id == user.organization_id, BusinessMetric.department_id == d.id)
            .order_by(BusinessMetric.period.asc())
        )
    ).scalars().all()
    risks = (await db.execute(select(RiskRecord).where(RiskRecord.organization_id == user.organization_id, RiskRecord.department_id == d.id))).scalars().all()
    recs = (await db.execute(select(Recommendation).where(Recommendation.organization_id == user.organization_id, Recommendation.department_id == d.id))).scalars().all()
    actions = (await db.execute(select(ActionItem).where(ActionItem.organization_id == user.organization_id, ActionItem.department_id == d.id))).scalars().all()

    return {
        "id": d.id,
        "name": d.name,
        "head_name": d.head_name,
        "health_score": d.health_score,
        "budget_monthly": d.budget_monthly,
        "metrics": [{"period": m.period, "metric_name": m.metric_name, "actual_value": m.actual_value, "target_value": m.target_value, "unit": m.unit} for m in metrics],
        "risks": [{"id": r.id, "title": r.title, "severity": r.severity, "financial_impact_usd": r.financial_impact_usd} for r in risks],
        "recommendations": [{"id": rec.id, "title": rec.title, "rationale": rec.rationale, "expected_impact": rec.expected_impact} for rec in recs],
        "actions": [{"id": a.id, "title": a.title, "status": a.status, "priority": a.priority, "progress_pct": a.progress_pct} for a in actions],
    }
