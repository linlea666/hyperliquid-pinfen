from datetime import timedelta

from sqlalchemy import select

from app.core.database import session_scope
from app.core.security import create_access_token, verify_password
from app.core.config import get_settings
from app.models import User


def authenticate_user(email: str, password: str) -> str | None:
    with session_scope() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash, user.password_salt):
            return None
        token = create_access_token(
            {"sub": str(user.id), "email": user.email},
            expires_delta=timedelta(minutes=get_settings().access_token_expire_minutes),
        )
        return token
