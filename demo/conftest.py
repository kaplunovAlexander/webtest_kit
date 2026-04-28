# demo/conftest.py
import os
from pathlib import Path
import pytest

# Говорим webtest-kit где искать config.yaml
os.environ.setdefault(
    "WEBTEST_CONFIG",
    str(Path(__file__).parent / "config.yaml"),
)

pytest_plugins = ["webtest_kit.core.fixtures"]


@pytest.fixture
def demo_project(manager_client):
    response = manager_client.post(
        "/projects/api/create",
        json={"title": "Demo Project", "description": "Created by webtest-kit fixture"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]
    yield project_id
    manager_client.delete(f"/projects/api/{project_id}")


@pytest.fixture
def demo_task(manager_client, demo_project):
    response = manager_client.post(
        f"/projects/{demo_project}/tasks/api/create",
        json={
            "title": "Demo Task",
            "status": "todo",
            "priority": "medium",
        },
    )
    assert response.status_code == 201
    yield response.json()["id"]
