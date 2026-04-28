# backend/app/routers/users.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import UserUpdate
from app.dependencies import get_current_user, require_role

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ───────────────────────── helpers ─────────────────────────

def _get_user_or_404(user_id: int, db: Session) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ───────────────────────── LIST ─────────────────────────

@router.get("/", response_class=HTMLResponse)
async def users_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Список всех пользователей. Только для admin."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "users/list.html",
        {
            "request": request,
            "users": users,
            "user": current_user,
            "roles": UserRole,
        },
    )


# ───────────────────────── DETAIL / EDIT ─────────────────────────

@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    target = _get_user_or_404(user_id, db)
    return templates.TemplateResponse(
        "users/detail.html",
        {
            "request": request,
            "target": target,
            "user": current_user,
            "roles": UserRole,
            "errors": [],
            "success": None,
        },
    )


@router.post("/{user_id}", response_class=HTMLResponse)
async def user_update(
    request: Request,
    user_id: int,
    full_name: str = Form(""),
    role: str = Form(...),
    is_active: str = Form("off"),       # чекбокс: "on" или "off"
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    target = _get_user_or_404(user_id, db)
    errors = []

    # Нельзя снять роль admin с самого себя
    if target.id == current_user.id and role != UserRole.admin:
        errors.append("You cannot change your own role.")

    # Нельзя деактивировать самого себя
    active = is_active == "on"
    if target.id == current_user.id and not active:
        errors.append("You cannot deactivate your own account.")

    # Валидация роли
    try:
        validated_role = UserRole(role)
    except ValueError:
        errors.append(f"Invalid role: {role}")
        validated_role = target.role

    if errors:
        return templates.TemplateResponse(
            "users/detail.html",
            {
                "request": request,
                "target": target,
                "user": current_user,
                "roles": UserRole,
                "errors": errors,
                "success": None,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    target.full_name = full_name.strip() or None
    target.role = validated_role
    target.is_active = active
    db.commit()

    return templates.TemplateResponse(
        "users/detail.html",
        {
            "request": request,
            "target": target,
            "user": current_user,
            "roles": UserRole,
            "errors": [],
            "success": "User updated successfully.",
        },
    )


# ───────────────────────── TOGGLE ACTIVE (quick action) ─────────────────────────

@router.post("/{user_id}/toggle-active")
async def user_toggle_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Быстрая деактивация/активация прямо из списка."""
    target = _get_user_or_404(user_id, db)

    if target.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate your own account.",
        )

    target.is_active = not target.is_active
    db.commit()
    return RedirectResponse(url="/users", status_code=status.HTTP_303_SEE_OTHER)


# ───────────────────────── API endpoints ─────────────────────────

@router.get("/api/list", tags=["users-api"])
async def api_users_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.patch("/api/{user_id}", tags=["users-api"])
async def api_user_update(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    target = _get_user_or_404(user_id, db)

    if target.id == current_user.id:
        if payload.role and payload.role != UserRole.admin:
            raise HTTPException(status_code=400, detail="Cannot change your own role.")
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate yourself.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    db.commit()
    db.refresh(target)
    return {
        "id": target.id,
        "username": target.username,
        "role": target.role,
        "is_active": target.is_active,
    }
