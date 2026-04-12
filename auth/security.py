from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from auth.config import AuthSettings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("ascii"),
        )
    except ValueError:
        return False


def create_access_token(user_id: int, settings: AuthSettings) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_user_id(token: str, settings: AuthSettings) -> int:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    sub = payload.get("sub")
    if sub is None:
        raise jwt.InvalidTokenError("missing sub")
    return int(sub)
