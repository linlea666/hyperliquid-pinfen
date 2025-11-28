from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.deps import get_current_user
from app.services import tags as tag_service
from app.schemas.tags import (
    TagCreateRequest,
    TagResponse,
    WalletTagsResponse,
    AssignTagsRequest,
    TagUpdateRequest,
)


router = APIRouter()


def to_response(tag) -> TagResponse:
    return TagResponse(
        id=tag.id,
        name=tag.name,
        type=tag.type,
        color=tag.color,
        icon=tag.icon,
        description=tag.description,
        parent_id=tag.parent_id,
        rule=tag.rule_json,
    )


@router.get("/tags", response_model=List[TagResponse])
def list_tags(tag_type: str | None = None):
    tags = tag_service.list_tags(tag_type)
    return [to_response(tag) for tag in tags]


@router.post("/tags", response_model=TagResponse, dependencies=[Depends(get_current_user)])
def create_tag(payload: TagCreateRequest):
    tag = tag_service.create_tag(
        name=payload.name,
        tag_type=payload.type,
        color=payload.color,
        icon=payload.icon,
        description=payload.description,
        rule_json=payload.rule,
        parent_id=payload.parent_id,
    )
    return to_response(tag)


@router.put("/tags/{tag_id}", response_model=TagResponse, dependencies=[Depends(get_current_user)])
def update_tag(tag_id: int, payload: TagUpdateRequest):
    try:
        tag = tag_service.update_tag(
            tag_id,
            {
                "name": payload.name,
                "type": payload.type,
                "color": payload.color,
                "icon": payload.icon,
                "description": payload.description,
                "parent_id": payload.parent_id,
                "rule_json": payload.rule,
            },
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Tag not found")
    return to_response(tag)


@router.delete("/tags/{tag_id}", dependencies=[Depends(get_current_user)])
def delete_tag(tag_id: int):
    try:
        tag_service.delete_tag(tag_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"status": "ok"}


@router.get("/wallets/{address}/tags", response_model=WalletTagsResponse)
def wallet_tags(address: str):
    return WalletTagsResponse(address=address, tags=[to_response(tag) for tag in tag_service.wallet_tags(address)])


@router.post("/wallets/{address}/tags", response_model=WalletTagsResponse, dependencies=[Depends(get_current_user)])
def assign_wallet_tags(address: str, payload: AssignTagsRequest = Body(...)):
    tag_service.assign_tags(address, payload.tag_ids)
    return wallet_tags(address)
