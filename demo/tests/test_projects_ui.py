# demo/tests/test_projects_ui.py
"""
UI E2E-тесты проектов TaskFlow через webtest-kit.
"""
import pytest
from demo.pages.projects_page import (
    ProjectsListPage,
    ProjectFormPage,
    ProjectDetailPage,
)
from demo.pages.tasks_page import TaskFormPage

pytestmark = pytest.mark.e2e


class TestProjectsUi:

    def test_manager_sees_new_project_button(self, manager_page, base_url):
        """Manager видит кнопку создания проекта."""
        page = ProjectsListPage(manager_page, base_url)
        page.navigate()
        page.expect_visible(page.new_project_btn)

    def test_user_cannot_see_new_project_button(self, user_page, base_url):
        """User не видит кнопку создания проекта."""
        page = ProjectsListPage(user_page, base_url)
        page.navigate()
        page.expect_hidden(page.new_project_btn)

    def test_create_project_and_appears_in_list(self, manager_page, base_url):
        """Созданный проект появляется в списке."""
        import uuid
        unique = uuid.uuid4().hex[:6]
        title = f"Demo Project {unique}"

        list_page = ProjectsListPage(manager_page, base_url)
        list_page.navigate()
        list_page.open_new_project_form()

        form = ProjectFormPage(manager_page, base_url)
        form.fill_and_submit(title)

        manager_page.wait_for_url(
            lambda url: "/projects/" in url and "new" not in url
        )

        list_page.navigate()
        list_page.expect_project_visible(title)

    def test_empty_title_shows_error(self, manager_page, base_url):
        """Пробельный title при создании — alert с ошибкой."""
        manager_page.goto(f"{base_url}/projects/new")
        form = ProjectFormPage(manager_page, base_url)
        form.fill_and_submit("   ")
        form.expect_error()

    def test_user_cannot_access_create_form(self, user_page, base_url):
        """User не может открыть форму создания проекта."""
        user_page.goto(f"{base_url}/projects/new")
        form = ProjectFormPage(user_page, base_url)
        page_text = user_page.locator("body").inner_text()
        assert "403" in page_text or form.is_visible(form.title_input) is False


class TestTaskLifecycleUi:
    """
    Ключевой E2E-сценарий для диплома.
    Задача проходит полный цикл через UI.
    """

    def test_full_task_lifecycle(self, manager_page, base_url, demo_project):
        """
        todo → in_progress → done через UI.
        Это главный сценарий который демонстрирует ценность автотестов:
        без них этот путь нужно проверять вручную при каждом деплое.
        """
        # Открываем страницу проекта
        detail = ProjectDetailPage(manager_page, base_url)
        detail.navigate_to(demo_project)
        detail.open_new_task_form()

        manager_page.wait_for_url(
            lambda url: f"/projects/{demo_project}/tasks/new" in url
        )

        # Создаём задачу
        form = TaskFormPage(manager_page, base_url)
        form.fill_and_submit(
            title="Full Lifecycle Task",
            status="todo",
            priority="high",
        )

        manager_page.wait_for_url(
            lambda url: f"/projects/{demo_project}" in url
            and "tasks" not in url
        )
        detail.expect_task_visible("Full Lifecycle Task")

        # Получаем task_id из таблицы
        task_row = manager_page.locator("[data-task-id]").last
        task_id = task_row.get_attribute("data-task-id")

        # todo → in_progress
        manager_page.goto(
            f"{base_url}/projects/{demo_project}/tasks/{task_id}/edit"
        )
        form = TaskFormPage(manager_page, base_url)
        form.click_quick_status("in_progress")
        manager_page.wait_for_url(
            lambda url: f"/projects/{demo_project}" in url and "tasks" not in url
        )

        row = manager_page.locator(f"[data-task-id='{task_id}']")
        form.expect_text(
            row.get_by_test_id("task-status"), "In Progress"
        )

        # in_progress → done
        manager_page.goto(
            f"{base_url}/projects/{demo_project}/tasks/{task_id}/edit"
        )
        form = TaskFormPage(manager_page, base_url)
        form.click_quick_status("done")
        manager_page.wait_for_url(
            lambda url: f"/projects/{demo_project}" in url and "tasks" not in url
        )

        row = manager_page.locator(f"[data-task-id='{task_id}']")
        form.expect_text(
            row.get_by_test_id("task-status"), "Done"
        )
