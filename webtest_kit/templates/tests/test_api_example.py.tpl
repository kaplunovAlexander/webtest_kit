# tests/test_api_example.py
"""
Пример API-тестов с использованием webtest-kit.

Фикстуры {role}_client создаются автоматически для каждой роли
из вашего config.yaml. Просто используй их в параметрах теста.

Запуск только API-тестов:
    webtest-kit run --api-only
"""
import pytest


# Маркируем все тесты в файле как API-тесты
pytestmark = pytest.mark.api


class TestAuthApi:
    """Пример тестов авторизации через API."""

    def test_admin_is_authenticated(self, admin_client):
        """
        Проверяем что admin_client авторизован.
        Адаптируй URL под эндпоинт своего приложения который
        возвращает данные текущего пользователя.
        """
        response = admin_client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        # Замени "username" на поле которое возвращает твоё API
        assert "username" in data

    def test_anon_cannot_access_protected(self, anon_client):
        """Неавторизованный запрос получает 401."""
        response = anon_client.get("/auth/me")
        assert response.status_code == 401

    def test_login_success(self, anon_client):
        """
        Прямой тест логина через API.
        Адаптируй поля и URL под своё приложение.
        """
        response = anon_client.post(
            "/auth/login",
            data={
                "username": "your_username",   # замени
                "password": "your_password",   # замени
            },
        )
        # После успешного логина ожидаем редирект (303) или 200
        assert response.status_code in (200, 303)

    def test_login_wrong_password(self, anon_client):
        """Неверный пароль возвращает 401."""
        response = anon_client.post(
            "/auth/login",
            data={
                "username": "your_username",   # замени
                "password": "wrong_password",
            },
        )
        assert response.status_code == 401


class TestResourceApi:
    """
    Пример CRUD-тестов для любого ресурса.
    Замени /api/items на реальный URL твоего приложения.
    """

    def test_admin_can_create(self, admin_client):
        """Admin создаёт ресурс — ожидаем 201."""
        response = admin_client.post(
            "/api/items",               # замени на свой URL
            json={"name": "Test Item"},
        )
        assert response.status_code == 201
        assert "id" in response.json()

    def test_user_cannot_create(self, user_client):
        """Обычный user не может создать ресурс — ожидаем 403."""
        response = user_client.post(
            "/api/items",               # замени на свой URL
            json={"name": "Test Item"},
        )
        assert response.status_code == 403

    def test_list_returns_json_array(self, admin_client):
        """Список ресурсов возвращает JSON-массив."""
        response = admin_client.get("/api/items")  # замени на свой URL
        assert response.status_code == 200
        assert isinstance(response.json(), list)
