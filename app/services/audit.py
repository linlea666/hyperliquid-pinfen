from typing import Optional

from app.core.database import session_scope
from app.models import AuditLog


def log_action(action: str, detail: str | None = None, user_id: Optional[int] = None, ip: Optional[str] = None):
    with session_scope() as session:
        session.add(AuditLog(user_id=user_id, action=action, detail=detail, ip_address=ip))
