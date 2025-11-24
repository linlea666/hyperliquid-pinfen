import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Tuple

from jose import jwt

from app.core.config import get_settings


def hash_password(password: str, salt: str | None = None) -> Tuple[str, str]:
    """Return (hash, salt) using SHA256 with salt."""
    salt = salt or os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return digest, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    computed, _ = hash_password(password, salt)
    return computed == hashed


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
