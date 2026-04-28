# demo/tests/test_projects_api.py
"""
API-тесты проектов TaskFlow через webtest-kit.

Демонстрирует использование:
- assert_status, assert_json_contains из BaseApiClient
- demo_project фикстура из demo/conftest.py
"""
import pytest

pytestmark = pytest.mark.api


class TestProjectsApi:

    def test_manager_creates_project(self, manager_client):
        """Manager создаёт проект — 201 с id в ответе."""
        response = manager_client.post(
            "/projects/api/create",
            json={"title": "webtest-kit Project", "description": "via BaseApiClient"},
        )
        manager_client.assert_status(response, 201)
        manager_client.assert_json_contains(response, title="webtest-kit Project")
        assert "id" in response.json()
        # teardown
        manager_client.delete(f"/projects/api/{response.json()['id']}")

    def test_user_cannot_create_project(self, user_client):
        """Обычный user не может создать проект — 403."""
        response = user_client.post(
            "/projects/api/create",
            json={"title": "Forbidden"},
        )
        user_client.assert_status(response, 403)

    def test_empty_title_rejected(self, manager_client):
        """Пустой title — 422."""
        response = manager_client.post(
            "/projects/api/create",
            json={"title": "   "},
        )
        manager_client.assert_status(response, 422)

    def test_project_appears_in_list(self, manager_client, demo_project):
        """Созданный проект есть в списке."""
        projects = manager_client.get_json("/projects/api/list")
        ids = [p["id"] for p in projects]
        assert demo_project in ids

    def test_update_project_title(self, manager_client, demo_project):
        """Manager обновляет title проекта."""
        response = manager_client.patch(
            f"/projects/api/{demo_project}",
            json={"title": "Updated by webtest-kit"},
        )
        manager_client.assert_status(response, 200)
        manager_client.assert_json_contains(
            response, title="Updated by webtest-kit"
        )

    def test_user_cannot_update_project(self, user_client, demo_project):
        """User не может обновить проект — 403."""
        response = user_client.patch(
            f"/projects/api/{demo_project}",
            json={"title": "Hacked"},
        )
        user_client.assert_status(response, 403)

    def test_delete_project(self, manager_client):
        """Проект архивируется и исчезает из списка."""
        create = manager_client.post(
            "/projects/api/create",
            json={"title": "To Archive"},
        )
        project_id = create.json()["id"]

        response = manager_client.delete(f"/projects/api/{project_id}")
        manager_client.assert_status(response, 204)

        projects = manager_client.get_json("/projects/api/list")
        assert not any(p["id"] == project_id for p in projects)

    def test_task_status_lifecycle(self, manager_client, demo_project):
        """
        Ключевой бизнес-сценарий: задача проходит todo → in_progress → done.
        Демонстрирует ценность автотестов — этот сценарий
        вручную нужно проверять при каждом изменении логики.
        """
        # Создаём задачу
        create = manager_client.post(
            f"/projects/{demo_project}/tasks/api/create",
            json={"title": "Lifecycle Task", "status": "todo", "priority": "high"},
        )
        manager_client.assert_status(create, 201)
        task_id = create.json()["id"]

        # Проверяем каждый переход статуса
        for expected_status in ["in_progress", "done"]:
            response = manager_client.patch(
                f"/projects/{demo_project}/tasks/api/{task_id}",
                json={"status": expected_status},
            )
            manager_client.assert_status(response, 200)
            manager_client.assert_json_contains(
                response, status=expected_status
            )
