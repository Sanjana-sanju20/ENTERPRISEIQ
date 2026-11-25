import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), default="Enterprise Operations")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[List[str]] = mapped_column(JSON, default=list)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    head_name: Mapped[str] = mapped_column(String(120), default="Department Lead")
    health_score: Mapped[float] = mapped_column(Float, default=80.0)
    budget_monthly: Mapped[float] = mapped_column(Float, default=100000.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    role_code: Mapped[str] = mapped_column(String(50), default="ceo", index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(140), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="financial_report")
    storage_path: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(32), default="Uploaded")  # Uploaded->Validating->Extracting->Processing->Indexed->Ready|Failed
    processing_stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_issues: Mapped[List[dict[str, Any]]] = mapped_column(JSON, default=list)
    preview_text: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_or_section: Mapped[str] = mapped_column(String(80), default="Section 1")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BusinessMetric(Base):
    __tablename__ = "business_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(20), index=True)  # YYYY-MM
    metric_name: Mapped[str] = mapped_column(String(80), index=True)  # revenue, operating_expense, net_profit, customer_complaints, delivery_cost, etc.
    actual_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(24), default="USD")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(64), default="full_diagnostic")
    status: Mapped[str] = mapped_column(String(32), default="Completed")
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="profitability")
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_hypotheses: Mapped[List[dict[str, Any]]] = mapped_column(JSON, default=list)
    supporting_evidence: Mapped[List[dict[str, Any]]] = mapped_column(JSON, default=list)
    severity: Mapped[str] = mapped_column(String(24), default="high")  # low | medium | high | critical
    confidence: Mapped[float] = mapped_column(Float, default=0.82)
    methodology_note: Mapped[str] = mapped_column(Text, default="")
    suggested_next_step: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RiskRecord(Base):
    __tablename__ = "risk_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="financial")
    severity: Mapped[str] = mapped_column(String(24), default="high")
    probability: Mapped[float] = mapped_column(Float, default=0.7)  # 0..1
    impact_score: Mapped[float] = mapped_column(Float, default=0.8)  # 0..1
    financial_impact_usd: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[List[dict[str, Any]]] = mapped_column(JSON, default=list)
    mitigation_plan: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    metric_name: Mapped[str] = mapped_column(String(80), index=True)
    period: Mapped[str] = mapped_column(String(20))
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(80), default="Holt-Winters Exponential Smoothing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[Optional[str]] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(24), default="high")
    expected_impact: Mapped[str] = mapped_column(String(240), default="")
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    department_id: Mapped[Optional[str]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    assigned_to_name: Mapped[str] = mapped_column(String(120), default="Operations Lead")
    source_finding_id: Mapped[Optional[str]] = mapped_column(ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(24), default="high")  # low | medium | high | critical
    status: Mapped[str] = mapped_column(String(32), default="Open")  # Open | In Progress | Under Review | Completed | Overdue
    due_date: Mapped[str] = mapped_column(String(32), default="2026-12-15")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[List[dict[str, Any]]] = mapped_column(JSON, default=list)
    outcome_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    baseline_metric: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)
    post_action_metric: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    mode_label: Mapped[str] = mapped_column(String(64), default="Demonstration / Grounded Extractive")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_or_section: Mapped[str] = mapped_column(String(80), default="Section 1")
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), default="")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="warning")  # info | warning | critical
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), default="system")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), default="executive_summary")
    period_label: Mapped[str] = mapped_column(String(64), default="FY 2026 YTD")
    departments_included: Mapped[List[str]] = mapped_column(JSON, default=list)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    metrics_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(120), default="System")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
