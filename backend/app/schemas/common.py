from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=140)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role_code: str = Field(default="ceo")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AskAIRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1500)


class GenerateReportRequest(BaseModel):
    title: Optional[str] = None
    report_type: str = Field(default="executive_summary")  # executive_summary | financial | department | risk | forecast
    period_label: str = Field(default="FY 2026 (Dec 2025 - Nov 2026)")
    departments: List[str] = Field(default_factory=list)


class ActionCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    description: str = ""
    department_id: Optional[str] = None
    assigned_to_name: str = "Operations Lead"
    source_finding_id: Optional[str] = None
    priority: str = Field(default="high")
    due_date: str = Field(default="2026-12-20")
    baseline_metric: Optional[str] = None


class ActionUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    progress_pct: Optional[int] = Field(default=None, ge=0, le=100)
    assigned_to_name: Optional[str] = None
    due_date: Optional[str] = None
    comment: Optional[str] = None
    outcome_note: Optional[str] = None
    post_action_metric: Optional[str] = None
