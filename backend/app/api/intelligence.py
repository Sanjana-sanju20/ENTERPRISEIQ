from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import EnterpriseAIEngine
from app.analytics.engine import detect_metric_anomalies, forecast_metric
from app.api.dashboard import compute_kpi_snapshot
from app.api.deps import get_ai_engine, get_current_user, record_audit
from app.core.database import get_db
from app.models.entities import (
    AnalysisJob,
    BusinessMetric,
    Citation,
    Conversation,
    Department,
    Document,
    DocumentChunk,
    Finding,
    Forecast,
    Recommendation,
    RiskRecord,
    User,
)
from app.schemas.common import AskAIRequest

router = APIRouter(prefix="/api", tags=["Analytics, AI Intelligence & Risks"])


@router.get("/analytics/kpis")
async def analytics_kpis(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await compute_kpi_snapshot(db, user.organization_id)


@router.get("/analytics/anomalies")
async def analytics_anomalies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    metrics = (
        await db.execute(
            select(BusinessMetric)
            .where(BusinessMetric.organization_id == user.organization_id)
            .order_by(BusinessMetric.period.asc())
        )
    ).scalars().all()
    grouped: dict[str, list] = defaultdict(list)
    for m in metrics:
        grouped[m.metric_name].append({"period": m.period, "metric_name": m.metric_name, "actual_value": m.actual_value})

    all_anomalies = []
    for name in ("revenue", "operating_expenses", "customer_complaints", "delivery_cost"):
        if name in grouped:
            all_anomalies.extend(detect_metric_anomalies(grouped[name]))
    return {"anomalies": all_anomalies}


@router.get("/analytics/forecasts")
async def analytics_forecasts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Forecast)
            .where(Forecast.organization_id == user.organization_id)
            .order_by(Forecast.period.asc())
        )
    ).scalars().all()
    return {
        "forecasts": [
            {
                "id": f.id,
                "metric_name": f.metric_name,
                "period": f.period,
                "predicted_value": f.predicted_value,
                "lower_bound": f.lower_bound,
                "upper_bound": f.upper_bound,
                "model_used": f.model_used,
                "is_predicted": True,
            }
            for f in rows
        ]
    }


@router.post("/analytics/analyze")
@router.post("/ai/analyze")
async def run_analysis(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    metrics = (
        await db.execute(
            select(BusinessMetric)
            .where(BusinessMetric.organization_id == user.organization_id)
            .order_by(BusinessMetric.period.asc())
        )
    ).scalars().all()
    grouped: dict[str, list] = defaultdict(list)
    for m in metrics:
        grouped[m.metric_name].append({"period": m.period, "metric_name": m.metric_name, "actual_value": m.actual_value})

    anomalies = []
    for name in ("revenue", "operating_expenses", "customer_complaints"):
        if name in grouped:
            anomalies.extend(detect_metric_anomalies(grouped[name]))

    forecasts = []
    for name in ("revenue", "operating_expenses"):
        if name in grouped:
            forecasts.extend(forecast_metric(grouped[name], horizon=3))

    job = AnalysisJob(
        organization_id=user.organization_id,
        job_type="on_demand_diagnostic",
        status="Completed",
        summary=f"Detected {len(anomalies)} anomaly point(s) and generated {len(forecasts)} forecast horizon point(s).",
    )
    db.add(job)
    await record_audit(db, user.organization_id, user.email, "RUN_ANALYSIS", "analysis_job", job.summary)
    await db.commit()
    return {"job_id": job.id, "status": job.status, "summary": job.summary, "anomalies": anomalies, "forecasts": forecasts}


@router.get("/ai/insights")
async def list_ai_insights(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    findings = (
        await db.execute(
            select(Finding).where(Finding.organization_id == user.organization_id).order_by(Finding.created_at.desc())
        )
    ).scalars().all()
    recs = (
        await db.execute(
            select(Recommendation).where(Recommendation.organization_id == user.organization_id).order_by(Recommendation.created_at.desc())
        )
    ).scalars().all()
    return {
        "findings": [
            {
                "id": f.id,
                "category": f.category,
                "title": f.title,
                "finding": f.finding,
                "business_impact": f.business_impact,
                "root_cause_hypotheses": f.root_cause_hypotheses,
                "supporting_evidence": f.supporting_evidence,
                "severity": f.severity,
                "confidence": f.confidence,
                "methodology_note": f.methodology_note,
                "suggested_next_step": f.suggested_next_step,
                "created_at": f.created_at.isoformat(),
            }
            for f in findings
        ],
        "recommendations": [
            {
                "id": r.id,
                "finding_id": r.finding_id,
                "title": r.title,
                "rationale": r.rationale,
                "priority": r.priority,
                "expected_impact": r.expected_impact,
                "requires_human_approval": r.requires_human_approval,
            }
            for r in recs
        ],
    }


@router.post("/ai/ask")
async def ask_copilot(
    payload: AskAIRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    ai: EnterpriseAIEngine = Depends(get_ai_engine),
):
    snap = await compute_kpi_snapshot(db, user.organization_id)
    chunk_rows = (
        await db.execute(
            select(DocumentChunk, Document.filename)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.organization_id == user.organization_id)
        )
    ).all()
    pool = [
        {
            "document_id": ch.document_id,
            "document_name": fname,
            "page_or_section": ch.page_or_section,
            "content": ch.content,
        }
        for ch, fname in chunk_rows
    ]
    retrieved = ai.retrieve_relevant_chunks(payload.question, pool, top_k=4)
    result = await ai.answer_business_question(payload.question, {k: v for k, v in snap.items() if k != "trends"}, retrieved)

    conv = Conversation(
        organization_id=user.organization_id,
        user_id=user.id,
        question=payload.question,
        answer=result["answer"],
        mode_label=result["mode_label"],
    )
    db.add(conv)
    await db.flush()

    for c in result["citations"]:
        db.add(
            Citation(
                organization_id=user.organization_id,
                conversation_id=conv.id,
                document_name=c["document_name"],
                page_or_section=c["page_or_section"],
                excerpt=c["excerpt"],
                source_ref=c["source_ref"],
            )
        )

    await record_audit(db, user.organization_id, user.email, "AI_COPILOT_QUERY", "conversation", payload.question[:120])
    await db.commit()

    return {
        "conversation_id": conv.id,
        "question": payload.question,
        "answer": result["answer"],
        "mode_label": result["mode_label"],
        "citations": result["citations"],
        "suggested_action_title": result["suggested_action_title"],
        "supporting_metrics": {k: v for k, v in snap.items() if k != "trends"},
    }


@router.get("/risks")
async def list_risks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    risks = (
        await db.execute(
            select(RiskRecord).where(RiskRecord.organization_id == user.organization_id).order_by(RiskRecord.impact_score.desc())
        )
    ).scalars().all()
    depts = {
        d.id: d.name
        for d in (await db.execute(select(Department).where(Department.organization_id == user.organization_id))).scalars().all()
    }
    avg_index = round(sum((r.probability * r.impact_score * 100) for r in risks) / len(risks), 1) if risks else 0.0
    return {
        "overall_risk_index": avg_index,
        "risks": [
            {
                "id": r.id,
                "title": r.title,
                "category": r.category,
                "department_name": depts.get(r.department_id, "Enterprise"),
                "severity": r.severity,
                "probability": r.probability,
                "impact_score": r.impact_score,
                "financial_impact_usd": r.financial_impact_usd,
                "evidence": r.evidence,
                "mitigation_plan": r.mitigation_plan,
                "status": r.status,
            }
            for r in risks
        ],
    }


@router.get("/risks/{risk_id}")
async def get_risk(risk_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = (
        await db.execute(select(RiskRecord).where(RiskRecord.id == risk_id, RiskRecord.organization_id == user.organization_id))
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Risk record not found.")
    return {
        "id": r.id,
        "title": r.title,
        "category": r.category,
        "severity": r.severity,
        "probability": r.probability,
        "impact_score": r.impact_score,
        "financial_impact_usd": r.financial_impact_usd,
        "evidence": r.evidence,
        "mitigation_plan": r.mitigation_plan,
        "status": r.status,
    }
