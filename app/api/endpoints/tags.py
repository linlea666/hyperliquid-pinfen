from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.deps import require_admin_token
from app.services import tags as tag_service
from app.schemas.tags import (
    TagCreateRequest,
    TagResponse,
    WalletTagsResponse,
    AssignTagsRequest,
)


router = APIRouter()


@router.get("/tags", response_model=List[TagResponse])
def list_tags(tag_type: str | None = None):
    tags = tag_service.list_tags(tag_type)
    result = []
    for tag in tags:
        result.append(
            TagResponse(
                id=tag.id,
                name=tag.name,
                type=tag.type,
                color=tag.color,
                icon=tag.icon,
                description=tag.description,
                parent_id=tag.parent_id,
            )
        )
    return result


@router.post("/tags", response_model=TagResponse, dependencies=[Depends(require_admin_token)])
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
    return TagResponse(
        id=tag.id,
        name=tag.name,
        type=tag.type,
        color=tag.color,
        icon=tag.icon,
        description=tag.description,
        parent_id=tag.parent_id,
    )


@router.get("/wallets/{address}/tags", response_model=WalletTagsResponse)
def wallet_tags(address: str):
    return WalletTagsResponse(
        address=address,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                type=tag.type,
                color=tag.color,
                icon=tag.icon,
                description=tag.description,
                parent_id=tag.parent_id,
            )
            for tag in tag_service.wallet_tags(address)
        ],
    )


@router.post("/wallets/{address}/tags", response_model=WalletTagsResponse, dependencies=[Depends(require_admin_token)])
def assign_wallet_tags(address: str, payload: AssignTagsRequest = Body(...)):
    tag_service.assign_tags(address, payload.tag_ids)
    return wallet_tags(address)
