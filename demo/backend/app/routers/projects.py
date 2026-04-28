# backend/app/routers/projects.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Project, Task, UserRole
from app.schemas import ProjectCreate, ProjectUpdate
from app.dependencies import get_current_user, require_role

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ───────────────────────── helpers ─────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _can_edit(user: User, project: Project) -> bool:
    """Редактировать проект может его владелец, manager или admin."""
    return user.role in (UserRole.admin, UserRole.manager) or project.owner_id == user.id


# ───────────────────────── LIST ─────────────────────────

@router.get("/", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Список всех активных проектов."""
    projects = (
        db.query(Project)
        .filter(Project.is_active == True)
        .options(joinedload(Project.owner))
        .order_by(Project.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "projects/list.html",
        {
            "request": request,
            "projects": projects,
            "user": current_user,
        },
    )


# ───────────────────────── CREATE ─────────────────────────

@router.get("/new", response_class=HTMLResponse)
async def project_new_page(
    request: Request,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    """Форма создания проекта — только для admin и manager."""
    return templates.TemplateResponse(
        "projects/form.html",
        {
            "request": request,
            "user": current_user,
            "project": None,
            "errors": [],
        },
    )


@router.post("/new", response_class=HTMLResponse)
async def project_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    errors = []
    try:
        data = ProjectCreate(title=title, description=description or None)
    except Exception as e:
        for err in e.errors():
            errors.append(err["msg"].replace("Value error, ", ""))

    if errors:
        return templates.TemplateResponse(
            "projects/form.html",
            {
                "request": request,
                "user": current_user,
                "project": None,
                "errors": errors,
                "form": {"title": title, "description": description},
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    project = Project(
        title=data.title,
        description=data.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(
        url=f"/projects/{project.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ───────────────────────── DETAIL ─────────────────────────

@router.get("/{project_id}", response_class=HTMLResponse)
async def project_detail(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Страница проекта со списком задач."""
    project = (
        db.query(Project)
        .options(
            joinedload(Project.owner),
            joinedload(Project.tasks).joinedload(Task.assignee),
        )
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "project": project,
            "user": current_user,
            "can_edit": _can_edit(current_user, project),
        },
    )


# ───────────────────────── EDIT ─────────────────────────

@router.get("/{project_id}/edit", response_class=HTMLResponse)
async def project_edit_page(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    return templates.TemplateResponse(
        "projects/form.html",
        {
            "request": request,
            "user": current_user,
            "project": project,
            "errors": [],
        },
    )


@router.post("/{project_id}/edit", response_class=HTMLResponse)
async def project_update(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    errors = []
    try:
        data = ProjectCreate(title=title, description=description or None)
    except Exception as e:
        for err in e.errors():
            errors.append(err["msg"].replace("Value error, ", ""))

    if errors:
        return templates.TemplateResponse(
            "projects/form.html",
            {
                "request": request,
                "user": current_user,
                "project": project,
                "errors": errors,
                "form": {"title": title, "description": description},
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    project.title = data.title
    project.description = data.description
    db.commit()
    return RedirectResponse(
        url=f"/projects/{project.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ───────────────────────── DELETE ─────────────────────────

@router.post("/{project_id}/delete")
async def project_delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Мягкое удаление: is_active = False.
    Физическое удаление данных — плохая практика в учебном проекте,
    мягкое удаление нагляднее и легче тестировать.
    """
    project = _get_project_or_404(project_id, db)
    if not _can_edit(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    project.is_active = False
    db.commit()
    return RedirectResponse(url="/projects", status_code=status.HTTP_303_SEE_OTHER)


# ───────────────────────── API endpoints ─────────────────────────
# Отдельные JSON-эндпоинты для API-тестов через pytest + requests

@router.get("/api/list", tags=["projects-api"])
async def api_projects_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = (
        db.query(Project)
        .filter(Project.is_active == True)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "owner_id": p.owner_id,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@router.post("/api/create", status_code=status.HTTP_201_CREATED, tags=["projects-api"])
async def api_project_create(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.manager)),
):
    project = Project(
        title=payload.title,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "title": project.title}


@router.patch("/api/{project_id}", tags=["projects-api"])
async def api_project_update(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "title": project.title, "is_active": project.is_active}


@router.delete("/api/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["projects-api"])
async def api_project_delete(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")
    project.is_active = False
    db.commit()
