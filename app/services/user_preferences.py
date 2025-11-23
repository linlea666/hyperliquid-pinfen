import json
from typing import Optional

from sqlalchemy import select

from app.core.database import session_scope
from app.models import User, UserPreference


def get_user_by_email(email: str) -> Optional[User]:
    with session_scope() as session:
        return session.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_preference(user_id: int) -> Optional[UserPreference]:
    with session_scope() as session:
        return session.execute(select(UserPreference).where(UserPreference.user_id == user_id)).scalar_one_or_none()


def upsert_preference(user_id: int, **kwargs) -> UserPreference:
    with session_scope() as session:
        pref = session.execute(select(UserPreference).where(UserPreference.user_id == user_id)).scalar_one_or_none()
        if pref:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(pref, key, value)
        else:
            pref = UserPreference(user_id=user_id, **kwargs)
            session.add(pref)
        session.flush()
        session.refresh(pref)
        return pref
