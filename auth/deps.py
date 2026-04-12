from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.config import AuthSettings, get_auth_settings
from auth.security import decode_user_id
from database import get_db
from user.model import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        user_id = decode_user_id(token, settings)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
