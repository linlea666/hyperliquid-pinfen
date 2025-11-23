from typing import List, Optional

from sqlalchemy import select

from app.core.database import session_scope
from app.core.security import hash_password
from app.models import AuditLog, Permission, Role, SystemConfig, User


def list_permissions() -> List[Permission]:
    with session_scope() as session:
        return session.execute(select(Permission)).scalars().all()


def create_permission(code: str, description: Optional[str]) -> Permission:
    with session_scope() as session:
        perm = Permission(code=code, description=description)
        session.add(perm)
        session.flush()
        session.refresh(perm)
        return perm


def list_roles() -> List[Role]:
    with session_scope() as session:
        return session.execute(select(Role)).scalars().all()


def create_role(name: str, description: Optional[str], permission_ids: List[int]) -> Role:
    with session_scope() as session:
        role = Role(name=name, description=description)
        if permission_ids:
            perms = session.execute(select(Permission).where(Permission.id.in_(permission_ids))).scalars().all()
            role.permissions = perms
        session.add(role)
        session.flush()
        session.refresh(role)
        return role


def update_role(role_id: int, name: Optional[str], description: Optional[str], permission_ids: Optional[List[int]]) -> Role:
    with session_scope() as session:
        role = session.get(Role, role_id)
        if not role:
            raise ValueError("Role not found")
        if name:
            role.name = name
        if description is not None:
            role.description = description
        if permission_ids is not None:
            perms = session.execute(select(Permission).where(Permission.id.in_(permission_ids))).scalars().all()
            role.permissions = perms
        session.add(role)
        session.flush()
        session.refresh(role)
        return role


def list_users() -> List[User]:
    with session_scope() as session:
        return session.execute(select(User)).scalars().all()


def create_user(email: str, name: str, password: str, roles: List[int], require_2fa: bool) -> User:
    hash_value, salt = hash_password(password)
    with session_scope() as session:
        user = User(
            email=email,
            name=name,
            password_hash=hash_value,
            password_salt=salt,
            require_2fa=1 if require_2fa else 0,
        )
        if roles:
            role_objs = session.execute(select(Role).where(Role.id.in_(roles))).scalars().all()
            user.roles = role_objs
        session.add(user)
        session.flush()
        session.refresh(user)
        return user


def update_user(user_id: int, name: Optional[str], password: Optional[str], status: Optional[str], roles: Optional[List[int]], require_2fa: Optional[bool]) -> User:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        if name:
            user.name = name
        if password:
            hash_value, salt = hash_password(password)
            user.password_hash = hash_value
            user.password_salt = salt
        if status:
            user.status = status
        if require_2fa is not None:
            user.require_2fa = 1 if require_2fa else 0
        if roles is not None:
            role_objs = session.execute(select(Role).where(Role.id.in_(roles))).scalars().all()
            user.roles = role_objs
        session.add(user)
        session.flush()
        session.refresh(user)
        return user


def delete_user(user_id: int) -> None:
    with session_scope() as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)


def upsert_config(key: str, value: str, description: Optional[str]) -> SystemConfig:
    with session_scope() as session:
        config = session.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        if config:
            config.value = value
            config.description = description
        else:
            config = SystemConfig(key=key, value=value, description=description)
            session.add(config)
        session.flush()
        session.refresh(config)
        return config


def list_configs() -> List[SystemConfig]:
    with session_scope() as session:
        return session.execute(select(SystemConfig)).scalars().all()


def list_audit_logs(limit: int = 50, offset: int = 0) -> List[AuditLog]:
    with session_scope() as session:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        return session.execute(stmt).scalars().all()


def get_config(key: str) -> Optional[str]:
    with session_scope() as session:
        cfg = session.execute(select(SystemConfig).where(SystemConfig.key == key)).scalar_one_or_none()
        return cfg.value if cfg else None
