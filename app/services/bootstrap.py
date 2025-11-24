from sqlalchemy import select

from app.core.database import session_scope
from app.core.security import hash_password
from app.models import User


def ensure_default_admin():
    """Create default admin account if none exists."""
    with session_scope() as session:
        existing = session.execute(select(User)).scalars().first()
        if existing:
            return
        password_hash, salt = hash_password("admin888")
        user = User(
            email="admin@example.com",
            name="Admin",
            password_hash=password_hash,
            password_salt=salt,
            require_2fa=0,
            status="active",
        )
        session.add(user)
