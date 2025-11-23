from typing import List, Optional

from pydantic import BaseModel, Field


class TagCreateRequest(BaseModel):
    name: str
    type: str = Field("user", description="system|ai|user")
    color: str = "#7c3aed"
    icon: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    rule: Optional[dict] = None


class TagResponse(BaseModel):
    id: int
    name: str
    type: str
    color: str
    icon: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None


class WalletTagsResponse(BaseModel):
    address: str
    tags: List[TagResponse]


class AssignTagsRequest(BaseModel):
    tag_ids: List[int] = Field(default_factory=list)
