from typing import List

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import require_admin_token
from app.schemas import admin as admin_schema
from app.schemas.preferences import PreferenceResponse, PreferenceUpdate
from app.services import admin as admin_service
from app.services import audit as audit_service
from app.services import user_preferences as pref_service

router = APIRouter(dependencies=[Depends(require_admin_token)])


def serialize_user(user):
    data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "status": user.status,
        "require_2fa": bool(user.require_2fa),
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": [
                    {"id": perm.id, "code": perm.code, "description": perm.description} for perm in role.permissions
                ],
            }
            for role in user.roles
        ],
    }
    return data


@router.get("/admin/users", response_model=List[admin_schema.UserResponse])
def list_users():
    return [serialize_user(u) for u in admin_service.list_users()]


@router.post("/admin/users", response_model=admin_schema.UserResponse)
def create_user(payload: admin_schema.UserCreate):
    user = admin_service.create_user(
        email=str(payload.email),
        name=payload.name,
        password=payload.password,
        roles=payload.roles,
        require_2fa=payload.require_2fa,
    )
    audit_service.log_action("user.create", f"Created user {user.email}")
    return serialize_user(user)


@router.put("/admin/users/{user_id}", response_model=admin_schema.UserResponse)
def update_user(user_id: int, payload: admin_schema.UserUpdate):
    try:
        user = admin_service.update_user(
            user_id=user_id,
            name=payload.name,
            password=payload.password,
            status=payload.status,
            roles=payload.roles,
            require_2fa=payload.require_2fa,
        )
        audit_service.log_action("user.update", f"Updated user {user.email}")
        return serialize_user(user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    admin_service.delete_user(user_id)
    audit_service.log_action("user.delete", f"Deleted user {user_id}")


@router.get("/admin/permissions", response_model=List[admin_schema.PermissionResponse])
def list_permissions():
    perms = admin_service.list_permissions()
    return [{"id": p.id, "code": p.code, "description": p.description} for p in perms]


@router.post("/admin/permissions", response_model=admin_schema.PermissionResponse)
def create_permission(payload: admin_schema.PermissionCreate):
    perm = admin_service.create_permission(payload.code, payload.description)
    audit_service.log_action("permission.create", f"Created permission {perm.code}")
    return {"id": perm.id, "code": perm.code, "description": perm.description}


@router.get("/admin/roles", response_model=List[admin_schema.RoleResponse])
def list_roles():
    roles = admin_service.list_roles()
    result = []
    for role in roles:
        result.append(
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": [
                    {"id": perm.id, "code": perm.code, "description": perm.description} for perm in role.permissions
                ],
            }
        )
    return result


@router.post("/admin/roles", response_model=admin_schema.RoleResponse)
def create_role(payload: admin_schema.RoleCreate):
    role = admin_service.create_role(payload.name, payload.description, payload.permission_ids)
    audit_service.log_action("role.create", f"Created role {role.name}")
    return list_roles_single(role)


@router.put("/admin/roles/{role_id}", response_model=admin_schema.RoleResponse)
def update_role(role_id: int, payload: admin_schema.RoleCreate):
    try:
        role = admin_service.update_role(role_id, payload.name, payload.description, payload.permission_ids)
        audit_service.log_action("role.update", f"Updated role {role.name}")
        return list_roles_single(role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def list_roles_single(role):
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "permissions": [
            {"id": perm.id, "code": perm.code, "description": perm.description} for perm in role.permissions
        ],
    }


@router.get("/admin/configs", response_model=List[admin_schema.ConfigResponse])
def list_configs():
    configs = admin_service.list_configs()
    return [{"key": c.key, "value": c.value, "description": c.description} for c in configs]


@router.post("/admin/configs", response_model=admin_schema.ConfigResponse)
def upsert_config(payload: admin_schema.ConfigUpsert):
    config = admin_service.upsert_config(payload.key, payload.value, payload.description)
    audit_service.log_action("config.upsert", f"Updated config {config.key}")
    return {"key": config.key, "value": config.value, "description": config.description}


@router.get("/admin/audit", response_model=List[admin_schema.AuditLogResponse])
def list_audit_logs(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    logs = admin_service.list_audit_logs(limit=limit, offset=offset)
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@router.get("/admin/preferences", response_model=PreferenceResponse)
def get_preferences(email: str):
    user = pref_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    pref = pref_service.get_preference(user.id)
    return PreferenceResponse(
        default_period=pref.default_period if pref else "30d",
        default_sort=pref.default_sort if pref else "score",
        theme=pref.theme if pref else "dark",
        favorite_wallets=json.loads(pref.favorite_wallets) if pref and pref.favorite_wallets else [],
        favorite_leaderboards=json.loads(pref.favorite_leaderboards) if pref and pref.favorite_leaderboards else [],
    )


@router.post("/admin/preferences", response_model=PreferenceResponse)
def update_preferences(email: str, payload: PreferenceUpdate):
    user = pref_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    pref = pref_service.upsert_preference(
        user.id,
        default_period=payload.default_period,
        default_sort=payload.default_sort,
        theme=payload.theme,
        favorite_wallets=json.dumps(payload.favorite_wallets) if payload.favorite_wallets else None,
        favorite_leaderboards=json.dumps(payload.favorite_leaderboards) if payload.favorite_leaderboards else None,
    )
    return PreferenceResponse(
        default_period=pref.default_period,
        default_sort=pref.default_sort,
        theme=pref.theme,
        favorite_wallets=json.loads(pref.favorite_wallets) if pref.favorite_wallets else [],
        favorite_leaderboards=json.loads(pref.favorite_leaderboards) if pref.favorite_leaderboards else [],
    )
