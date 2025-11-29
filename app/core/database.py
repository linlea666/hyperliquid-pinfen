from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

Base = declarative_base()


def get_engine():
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.sqlite_path}",
        future=True,
        echo=False,
        connect_args={"check_same_thread": False, "timeout": 30},
    )


engine = get_engine()
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
