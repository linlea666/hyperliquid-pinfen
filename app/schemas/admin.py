from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class PermissionCreate(BaseModel):
    code: str = Field(..., description="唯一权限代码")
    description: Optional[str] = None


class PermissionResponse(PermissionCreate):
    id: int


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: List[int] = Field(default_factory=list)


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: List[PermissionResponse] = Field(default_factory=list)


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    roles: List[int] = Field(default_factory=list)
    require_2fa: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None
    roles: Optional[List[int]] = None
    require_2fa: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    status: str
    require_2fa: bool
    roles: List[RoleResponse] = Field(default_factory=list)


class ConfigUpsert(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    detail: Optional[str]
    ip_address: Optional[str]
    created_at: str
