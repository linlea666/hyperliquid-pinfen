from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse, summary="用户登录")
def login(payload: LoginRequest) -> TokenResponse:
    token = auth_service.authenticate_user(payload.email, payload.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=token)
