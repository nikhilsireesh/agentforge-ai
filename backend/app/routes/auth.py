from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, rate_limit
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _require_auth_enabled() -> None:
    if not get_settings().auth_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Authentication is disabled (AUTH_ENABLED=false).")


@router.post("/register", response_model=TokenResponse, status_code=201,
             dependencies=[Depends(rate_limit("auth"))])
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _require_auth_enabled()
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email exists.")
    user = auth_service.register_user(db, payload.name, payload.email, payload.password)
    return TokenResponse(access_token=auth_service.create_access_token(user),
                         user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("auth"))])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _require_auth_enabled()
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    return TokenResponse(access_token=auth_service.create_access_token(user),
                         user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
