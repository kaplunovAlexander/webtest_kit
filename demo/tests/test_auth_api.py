# demo/tests/test_auth_api.py
"""
API-тесты авторизации TaskFlow через webtest-kit.

Демонстрирует использование:
- admin_client, user_client  — из webtest-kit fixtures
- BaseApiClient.assert_status — из webtest-kit BaseApiClient
"""
import pytest

pytestmark = pytest.mark.api


class TestAuthApi:

    def test_admin_client_is_authenticated(self, admin_client):
        """admin_client авторизован — /auth/me возвращает данные."""
        response = admin_client.get("/auth/me")
        admin_client.assert_status(response, 200)
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_manager_client_has_correct_role(self, manager_client):
        """manager_client имеет роль manager."""
        response = manager_client.get("/auth/me")
        manager_client.assert_status(response, 200)
        assert response.json()["role"] == "manager"

    def test_user_client_has_correct_role(self, user_client):
        """user_client имеет роль user."""
        response = user_client.get("/auth/me")
        user_client.assert_status(response, 200)
        assert response.json()["role"] == "user"

    def test_anon_client_gets_401(self, anon_client):
        """Без авторизации /auth/me возвращает 401."""
        response = anon_client.get("/auth/me")
        anon_client.assert_status(response, 401)

    def test_login_success(self, anon_client):
        """Успешный логин возвращает редирект с cookie."""
        response = anon_client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 303
        assert "access_token" in response.cookies

    def test_login_wrong_password(self, anon_client):
        """Неверный пароль — 401."""
        response = anon_client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrongpass"},
        )
        anon_client.assert_status(response, 401)

    def test_login_nonexistent_user(self, anon_client):
        """Несуществующий пользователь — 401."""
        response = anon_client.post(
            "/auth/login",
            data={"username": "ghost", "password": "password"},
        )
        anon_client.assert_status(response, 401)

    def test_register_success(self, anon_client):
        """Новый пользователь успешно регистрируется."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        response = anon_client.post(
            "/auth/register",
            data={
                "email": f"webtest_{unique}@demo.dev",
                "username": f"webtest_{unique}",
                "password": "secure123",
            },
        )
        assert response.status_code == 303
        assert "registered=1" in response.headers.get("location", "")

    def test_register_duplicate_username(self, anon_client):
        """Дубликат username — 422."""
        response = anon_client.post(
            "/auth/register",
            data={
                "email": "new@demo.dev",
                "username": "admin",          # уже существует
                "password": "password123",
            },
        )
        anon_client.assert_status(response, 422)

    def test_register_short_password(self, anon_client):
        """Пароль короче 6 символов — 422."""
        response = anon_client.post(
            "/auth/register",
            data={
                "email": "short@demo.dev",
                "username": "short_pass_u",
                "password": "123",
            },
        )
        anon_client.assert_status(response, 422)
