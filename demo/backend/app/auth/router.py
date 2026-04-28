# backend/app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User
from app.schemas import UserCreate
from app.auth.utils import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ───────────────────────────── REGISTER ─────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации."""
    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request, "errors": [], "form": {}},
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    db: Session = Depends(get_db),
):
    """Обработка формы регистрации."""
    errors = []

    # Валидация через Pydantic-схему
    try:
        user_data = UserCreate(
            email=email,
            username=username,
            password=password,
            full_name=full_name or None,
        )
    except Exception as e:
        # Извлекаем читаемые сообщения из ValidationError
        for err in e.errors():
            errors.append(err["msg"].replace("Value error, ", ""))

    if not errors:
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
        )
        try:
            db.add(new_user)
            db.commit()
        except IntegrityError:
            db.rollback()
            errors.append("Email or username already taken.")

    if errors:
        return templates.TemplateResponse(
            "auth/register.html",
            {
                "request": request,
                "errors": errors,
                "form": {"email": email, "username": username, "full_name": full_name},
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return RedirectResponse(url="/auth/login?registered=1", status_code=status.HTTP_303_SEE_OTHER)


# ───────────────────────────── LOGIN ─────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    registered = request.query_params.get("registered")
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "errors": [],
            "success": "Registration successful! Please log in." if registered else None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Обработка формы входа. Выдаёт JWT в httponly cookie."""
    errors = []

    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        errors.append("Invalid username or password.")

    elif not user.is_active:
        errors.append("Your account is deactivated. Contact administrator.")

    if errors:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "errors": errors, "success": None},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(data={"sub": str(user.id)})

    response = RedirectResponse(url="/projects", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,   # недоступен из JS — защита от XSS
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return response


# ───────────────────────────── LOGOUT ─────────────────────────────

@router.get("/logout")
async def logout():
    """Выход: очищаем cookie и редиректим на логин."""
    response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


# ───────────────────────────── PROFILE (API) ─────────────────────────────

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    API-эндпоинт для получения текущего пользователя.
    Удобен для API-тестов — возвращает JSON.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "full_name": current_user.full_name,
    }
