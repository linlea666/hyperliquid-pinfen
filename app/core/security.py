import hashlib
import os
from typing import Tuple


def hash_password(password: str, salt: str | None = None) -> Tuple[str, str]:
    """Return (hash, salt) using SHA256 with salt."""
    salt = salt or os.urandom(16).hex()
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return digest, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    computed, _ = hash_password(password, salt)
    return computed == hashed
