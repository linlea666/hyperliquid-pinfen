from sqlalchemy import select, text

from app.core.database import session_scope, engine
from app.core.security import hash_password
from app.models import User

PROCESSING_COLUMNS = {
    "wallets": {
        "sync_status": "TEXT DEFAULT 'pending'",
        "score_status": "TEXT DEFAULT 'pending'",
        "ai_status": "TEXT DEFAULT 'pending'",
        "last_score_at": "DATETIME",
        "last_ai_at": "DATETIME",
        "next_score_due": "DATETIME",
        "last_error": "TEXT",
    },
    "wallet_metrics": {
        "details": "TEXT",
    },
    "wallet_scores": {
        "dimension_scores": "TEXT",
    },
}


def ensure_processing_schema() -> None:
    """Ensure new processing columns exist when using SQLite without migrations."""
    with engine.begin() as conn:
        for table, columns in PROCESSING_COLUMNS.items():
            existing_columns = {row[1] for row in conn.execute(text(f"PRAGMA table_info('{table}')"))}
            for column, ddl in columns.items():
                if column not in existing_columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


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
