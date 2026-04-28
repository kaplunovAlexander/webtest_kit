# backend/app/routers/tasks.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import User, Project, Task, UserRole, TaskStatus, TaskPriority
from app.schemas import TaskCreate, TaskUpdate
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ───────────────────────── helpers ─────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_task_or_404(task_id: int, project_id: int, db: Session) -> Task:
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.project_id == project_id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _can_edit_task(user: User, project: Project) -> bool:
    """
    Редактировать задачи может: admin, manager, владелец проекта.
    Обычный user может только смотреть.
    """
    return (
        user.role in (UserRole.admin, UserRole.manager)
        or project.owner_id == user.id
    )


def _parse_due_date(value: str) -> Optional[datetime]:
    """Парсит дату из HTML input[type=date]. Возвращает None если пусто."""
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def _get_assignable_users(db: Session) -> list[User]:
    """Список активных пользователей для выпадающего списка assignee."""
    return db.query(User).filter(User.is_active == True).order_by(User.username).all()


# ───────────────────────── CREATE ─────────────────────────

@router.get("/{project_id}/tasks/new", response_class=HTMLResponse)
async def task_new_page(
    request: Request,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    return templates.TemplateResponse(
        "tasks/form.html",
        {
            "request": request,
            "user": current_user,
            "project": project,
            "task": None,
            "errors": [],
            "users": _get_assignable_users(db),
            "statuses": TaskStatus,
            "priorities": TaskPriority,
        },
    )


@router.post("/{project_id}/tasks/new", response_class=HTMLResponse)
async def task_create(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    task_status: str = Form("todo"),
    priority: str = Form("medium"),
    due_date: str = Form(""),
    assignee_id: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    errors = []

    # Приводим assignee_id к int или None
    parsed_assignee_id: Optional[int] = None
    if assignee_id and assignee_id.strip():
        try:
            parsed_assignee_id = int(assignee_id)
        except ValueError:
            errors.append("Invalid assignee.")

    # Валидация через Pydantic
    try:
        data = TaskCreate(
            title=title,
            description=description or None,
            status=task_status,
            priority=priority,
            due_date=_parse_due_date(due_date),
            assignee_id=parsed_assignee_id,
        )
    except Exception as e:
        for err in e.errors():
            errors.append(err["msg"].replace("Value error, ", ""))

    if errors:
        return templates.TemplateResponse(
            "tasks/form.html",
            {
                "request": request,
                "user": current_user,
                "project": project,
                "task": None,
                "errors": errors,
                "form": {
                    "title": title,
                    "description": description,
                    "status": task_status,
                    "priority": priority,
                    "due_date": due_date,
                    "assignee_id": assignee_id,
                },
                "users": _get_assignable_users(db),
                "statuses": TaskStatus,
                "priorities": TaskPriority,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    task = Task(
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        project_id=project_id,
        assignee_id=data.assignee_id,
    )
    db.add(task)
    db.commit()
    return RedirectResponse(
        url=f"/projects/{project_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ───────────────────────── EDIT ─────────────────────────

@router.get("/{project_id}/tasks/{task_id}/edit", response_class=HTMLResponse)
async def task_edit_page(
    request: Request,
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    task = _get_task_or_404(task_id, project_id, db)

    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    return templates.TemplateResponse(
        "tasks/form.html",
        {
            "request": request,
            "user": current_user,
            "project": project,
            "task": task,
            "errors": [],
            "users": _get_assignable_users(db),
            "statuses": TaskStatus,
            "priorities": TaskPriority,
        },
    )


@router.post("/{project_id}/tasks/{task_id}/edit", response_class=HTMLResponse)
async def task_update(
    request: Request,
    project_id: int,
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    task_status: str = Form("todo"),
    priority: str = Form("medium"),
    due_date: str = Form(""),
    assignee_id: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    task = _get_task_or_404(task_id, project_id, db)

    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    errors = []

    parsed_assignee_id: Optional[int] = None
    if assignee_id and assignee_id.strip():
        try:
            parsed_assignee_id = int(assignee_id)
        except ValueError:
            errors.append("Invalid assignee.")

    try:
        data = TaskCreate(
            title=title,
            description=description or None,
            status=task_status,
            priority=priority,
            due_date=_parse_due_date(due_date),
            assignee_id=parsed_assignee_id,
        )
    except Exception as e:
        for err in e.errors():
            errors.append(err["msg"].replace("Value error, ", ""))

    if errors:
        return templates.TemplateResponse(
            "tasks/form.html",
            {
                "request": request,
                "user": current_user,
                "project": project,
                "task": task,
                "errors": errors,
                "form": {
                    "title": title,
                    "description": description,
                    "status": task_status,
                    "priority": priority,
                    "due_date": due_date,
                    "assignee_id": assignee_id,
                },
                "users": _get_assignable_users(db),
                "statuses": TaskStatus,
                "priorities": TaskPriority,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    task.title = data.title
    task.description = data.description
    task.status = data.status
    task.priority = data.priority
    task.due_date = data.due_date
    task.assignee_id = data.assignee_id
    db.commit()

    return RedirectResponse(
        url=f"/projects/{project_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ───────────────────────── DELETE ─────────────────────────

@router.post("/{project_id}/tasks/{task_id}/delete")
async def task_delete(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    task = _get_task_or_404(task_id, project_id, db)

    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.delete(task)
    db.commit()
    return RedirectResponse(
        url=f"/projects/{project_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ───────────────────────── API endpoints ─────────────────────────

@router.get("/{project_id}/tasks/api/list", tags=["tasks-api"])
async def api_tasks_list(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_project_or_404(project_id, db)
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project_id)
        .options(joinedload(Task.assignee))
        .order_by(Task.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "assignee_id": t.assignee_id,
            "assignee_username": t.assignee.username if t.assignee else None,
            "project_id": t.project_id,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


@router.post(
    "/{project_id}/tasks/api/create",
    status_code=status.HTTP_201_CREATED,
    tags=["tasks-api"],
)
async def api_task_create(
    project_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        project_id=project_id,
        assignee_id=payload.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "project_id": task.project_id,
    }


@router.patch("/{project_id}/tasks/api/{task_id}", tags=["tasks-api"])
async def api_task_update(
    project_id: int,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    task = _get_task_or_404(task_id, project_id, db)

    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
    }


@router.delete(
    "/{project_id}/tasks/api/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tasks-api"],
)
async def api_task_delete(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    task = _get_task_or_404(task_id, project_id, db)

    if not _can_edit_task(current_user, project):
        raise HTTPException(status_code=403, detail="Forbidden")

    db.delete(task)
    db.commit()
