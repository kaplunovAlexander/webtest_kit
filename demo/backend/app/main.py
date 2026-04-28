# demo/backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import engine, Base
from app.auth.utils import decode_token
from app.database import SessionLocal
from app.models import User

from app.auth.router import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


@app.middleware("http")
async def attach_user_to_request(request: Request, call_next):
    request.state.user = None
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload and (user_id := payload.get("sub")):
            db = SessionLocal()
            try:
                user = db.get(User, int(user_id))
                if user and user.is_active:
                    request.state.user = user
            finally:
                db.close()
    response = await call_next(request)

    if response.status_code == 401:
        path = request.url.path
        accept = request.headers.get("accept", "")

        # Пути которые никогда не редиректим — сами страницы авторизации
        # и все API-эндпоинты
        no_redirect_paths = {"/auth/login", "/auth/register", "/auth/me"}
        is_api_path = (
            path in no_redirect_paths
            or "api" in path          # /projects/api/*, /tasks/api/*, etc
        )
        is_json = "application/json" in accept

        if not is_api_path and not is_json:
            return RedirectResponse(url="/auth/login", status_code=302)

    return response


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(tasks_router, prefix="/projects", tags=["tasks"])
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/projects")
