from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ato import DEFAULT_CATEGORIES
from ..config import get_settings
from ..db import get_db
from ..models import Category, Portfolio, User, utcnow
from ..schemas import (ForgotPasswordIn, LoginIn, PasswordChange, ResetPasswordIn, SetupIn, UserCreate, UserOut,
                       UserUpdate)
from ..services import email as mailer
from ..security import (COOKIE_NAME, create_reset_token, create_token, current_user, hash_password, is_admin,
                        user_from_reset_token, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])
users_router = APIRouter(prefix="/api/users", tags=["users"])


def _set_cookie(resp: Response, user: User) -> None:
    s = get_settings()
    resp.set_cookie(
        COOKIE_NAME,
        create_token(user),
        httponly=True,
        samesite="lax",
        secure=s.cookie_secure,
        max_age=s.session_hours * 3600,
        path="/",
    )


def seed_categories(db: Session, portfolio_id: int) -> None:
    for i, (name, key, keywords) in enumerate(DEFAULT_CATEGORIES):
        db.add(Category(portfolio_id=portfolio_id, name=name, ato_key=key,
                        keywords=", ".join(keywords), sort_order=(i + 1) * 10))


@router.get("/status")
def auth_status(db: Session = Depends(get_db)):
    """Tells the UI whether first-run setup is still needed."""
    count = db.scalar(select(func.count()).select_from(User))
    return {"setup_required": count == 0, "email_reset": get_settings().email_enabled}


@router.post("/setup", response_model=UserOut)
def first_run_setup(body: SetupIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Setup has already been completed")
    portfolio = Portfolio(name=body.portfolio_name)
    db.add(portfolio)
    db.flush()
    user = User(portfolio_id=portfolio.id, email=body.email.strip().lower(), name=body.name,
                password_hash=hash_password(body.password), role="admin")
    db.add(user)
    seed_categories(db, portfolio.id)
    db.commit()
    _set_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    user.last_login_at = utcnow()
    db.commit()
    _set_cookie(response, user)
    return user


# ---- forgot / reset password by email ------------------------------------
_RESET_COOLDOWN_SECONDS = 60
_last_reset_request: dict[str, float] = {}


def _reset_link(request: Request, token: str) -> str:
    base = (get_settings().public_url or str(request.base_url)).rstrip("/")
    return f"{base}/reset-password?token={token}"


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, request: Request, background: BackgroundTasks,
                    db: Session = Depends(get_db)):
    """Emails a reset link. Always gives the same answer so it can't be used to discover accounts."""
    s = get_settings()
    if not s.email_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Password reset by email isn't set up on this server - ask an admin to reset it.")
    email = body.email.strip().lower()
    now = time.monotonic()
    if now - _last_reset_request.get(email, -1e9) >= _RESET_COOLDOWN_SECONDS:
        _last_reset_request[email] = now
        user = db.scalar(select(User).where(User.email == email))
        if user and user.is_active:
            link = _reset_link(request, create_reset_token(user))
            text = (
                f"Hi {user.name},\n\n"
                "Someone (hopefully you) asked to reset your Rental Manager password.\n"
                f"Open this link to choose a new one - it works once and expires in {s.reset_link_minutes} minutes:\n\n"
                f"{link}\n\n"
                "If you didn't ask for this you can ignore this email; your password won't change.\n"
            )
            background.add_task(mailer.send_email_logged, user.email, "Reset your Rental Manager password", text)
    return {"ok": True, "message": "If that email belongs to an account, a reset link is on its way."}


@router.post("/reset-password", response_model=UserOut)
def reset_password(body: ResetPasswordIn, response: Response, db: Session = Depends(get_db)):
    user = user_from_reset_token(db, body.token)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "This reset link is invalid, has expired or has already been used. Request a new one.")
    user.password_hash = hash_password(body.new_password)
    user.last_login_at = utcnow()
    db.commit()
    _set_cookie(response, user)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    portfolio = db.get(Portfolio, user.portfolio_id)
    return {"user": UserOut.model_validate(user), "portfolio": {"id": portfolio.id, "name": portfolio.name}}


@router.post("/password")
def change_password(body: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}


# ---- user management (admin) -------------------------------------------
@users_router.get("", response_model=list[UserOut])
def list_users(user: User = Depends(is_admin), db: Session = Depends(get_db)):
    return db.scalars(select(User).where(User.portfolio_id == user.portfolio_id).order_by(User.name)).all()


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, user: User = Depends(is_admin), db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")
    new = User(portfolio_id=user.portfolio_id, email=email, name=body.name, role=body.role,
               password_hash=hash_password(body.password))
    db.add(new)
    db.commit()
    return new


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, user: User = Depends(is_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target or target.portfolio_id != user.portfolio_id:
        raise HTTPException(404, "User not found")
    if target.id == user.id and (body.role not in (None, "admin") or body.is_active is False):
        raise HTTPException(400, "You can't remove your own admin access")
    if body.name is not None:
        target.name = body.name
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.password:
        target.password_hash = hash_password(body.password)
    db.commit()
    return target
