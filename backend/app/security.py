from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

COOKIE_NAME = "rm_session"
ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    s = get_settings()
    payload = {
        "sub": str(user.id),
        "pid": user.portfolio_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=s.session_hours),
    }
    return jwt.encode(payload, s.resolved_secret(), algorithm="HS256")


RESET_PURPOSE = "pwreset"


def _password_fingerprint(user: User) -> str:
    # Ties a reset link to the current password: once the password changes, old links stop working.
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def create_reset_token(user: User) -> str:
    s = get_settings()
    payload = {
        "sub": str(user.id),
        "purpose": RESET_PURPOSE,
        "ph": _password_fingerprint(user),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=s.reset_link_minutes),
    }
    return jwt.encode(payload, s.resolved_secret(), algorithm="HS256")


def user_from_reset_token(db: Session, token: str) -> User | None:
    """Returns the user for a valid, unused, unexpired reset token, else None."""
    try:
        payload = jwt.decode(token, get_settings().resolved_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != RESET_PURPOSE:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active or payload.get("ph") != _password_fingerprint(user):
        return None
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    try:
        payload = jwt.decode(token, get_settings().resolved_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    if payload.get("purpose"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def require_role(min_role: str):
    def _dep(user: User = Depends(current_user)) -> User:
        if ROLE_RANK.get(user.role, 0) < ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {min_role} access")
        return user

    return _dep


can_view = require_role("viewer")
can_edit = require_role("editor")
is_admin = require_role("admin")
