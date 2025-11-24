from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class WalletImportRecord(Base):
    __tablename__ = "wallet_import_records"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(32), default="manual", nullable=False)
    tag_list = Column(Text, default="")
    created_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
