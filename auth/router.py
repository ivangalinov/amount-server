from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import AuthSettings, get_auth_settings
from auth.deps import CurrentUser
from auth.security import create_access_token, hash_password, verify_password
from auth.workspace_bootstrap import ensure_user_has_default_workspace
from database import get_db
from user.model import User

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    name: str | None = Field(None, max_length=255)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


def _set_auth_cookie(response: Response, token: str, settings: AuthSettings) -> None:
    max_age = settings.jwt_expire_minutes * 60
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        max_age=max_age,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def _clear_auth_cookie(response: Response, settings: AuthSettings) -> None:
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        samesite=settings.auth_cookie_samesite,
    )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterBody,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    email = _normalize_email(body.email)
    display_name = (body.name or "").strip() or email.split("@", 1)[0]

    user = User(
        email=email,
        name=display_name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from None
    await ensure_user_has_default_workspace(db, user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, settings)
    _set_auth_cookie(response, token, settings)
    return user


@router.post("/login", response_model=UserPublic)
async def login(
    body: LoginBody,
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    email = _normalize_email(body.email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await ensure_user_has_default_workspace(db, user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, settings)
    _set_auth_cookie(response, token, settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    settings: AuthSettings = Depends(get_auth_settings),
) -> None:
    _clear_auth_cookie(response, settings)


@router.get("/me", response_model=UserPublic)
async def me(user: CurrentUser) -> User:
    return user
