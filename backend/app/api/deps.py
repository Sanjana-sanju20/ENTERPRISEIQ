from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import EnterpriseAIEngine
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.entities import AuditLog, User

bearer = HTTPBearer(auto_error=False)
_ai_engine: EnterpriseAIEngine | None = None


def get_ai_engine() -> EnterpriseAIEngine:
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = EnterpriseAIEngine()
    return _ai_engine


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required.")
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


def require_roles(*allowed_roles: str) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role_code not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role_code}' is not authorized for this action. Required: {', '.join(allowed_roles)}.",
            )
        return user
    return checker


async def record_audit(
    db: AsyncSession,
    org_id: str,
    actor_email: str,
    action: str,
    target_type: str,
    details: str,
) -> None:
    db.add(
        AuditLog(
            organization_id=org_id,
            actor_email=actor_email,
            action=action,
            target_type=target_type,
            details=details,
        )
    )
