from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, record_audit, require_roles
from app.core.database import get_db
from app.core.security import ALL_ROLES, ROLE_ADMIN, ROLE_CEO, create_access_token, hash_password, verify_password
from app.models.entities import AuditLog, Department, Notification, Organization, User
from app.schemas.common import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api", tags=["Auth, Notifications & Settings"])


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if payload.role_code not in ALL_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role_code. Choose one of: {', '.join(ALL_ROLES)}")

    exists = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email is already registered.")

    org = Organization(name=payload.organization_name.strip(), is_demo=False)
    db.add(org)
    await db.flush()

    for name in ("Finance", "Sales", "Operations", "Customer Support"):
        db.add(Department(organization_id=org.id, name=name))

    user = User(
        organization_id=org.id,
        role_code=payload.role_code,
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await record_audit(db, org.id, user.email, "USER_REGISTER", "user", f"Registered organization '{org.name}'")
    await db.commit()

    return TokenResponse(access_token=create_access_token(user.id, org.id, user.role_code))


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    await record_audit(db, user.organization_id, user.email, "USER_LOGIN", "auth", "Successful JWT login")
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.organization_id, user.role_code))


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    org = (await db.execute(select(Organization).where(Organization.id == user.organization_id))).scalar_one()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role_code": user.role_code,
        "department_id": user.department_id,
        "organization": {
            "id": org.id,
            "name": org.name,
            "industry": org.industry,
            "is_demo": org.is_demo,
        },
    }


@router.get("/notifications")
async def list_notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Notification)
            .where(Notification.organization_id == user.organization_id)
            .order_by(Notification.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    return [
        {
            "id": n.id,
            "severity": n.severity,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.patch("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = (
        await db.execute(
            select(Notification).where(Notification.id == notif_id, Notification.organization_id == user.organization_id)
        )
    ).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    await db.commit()
    return {"id": n.id, "is_read": True}


@router.get("/settings/users")
async def list_org_users(
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_CEO)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(select(User).where(User.organization_id == user.organization_id))
    ).scalars().all()
    return [
        {"id": u.id, "email": u.email, "full_name": u.full_name, "role_code": u.role_code, "is_active": u.is_active}
        for u in rows
    ]


@router.get("/settings/audit-logs")
async def list_audit_logs(
    user: User = Depends(require_roles(ROLE_ADMIN, ROLE_CEO)),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == user.organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id": a.id,
            "actor_email": a.actor_email,
            "action": a.action,
            "target_type": a.target_type,
            "details": a.details,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]
