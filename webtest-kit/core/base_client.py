# webtest_kit/core/base_client.py
"""
BaseApiClient — базовый класс для API-тестов.

Пользователь наследуется и добавляет методы под своё API:

    from webtest_kit.core.base_client import BaseApiClient

    class MyAppClient(BaseApiClient):

        def get_projects(self):
            return self.get("/projects/api/list")

        def create_project(self, title, description=""):
            return self.post("/projects/api/create", json={
                "title": title,
                "description": description,
            })

        def delete_project(self, project_id):
            return self.delete(f"/projects/api/{project_id}")

Особенности:
- Авторизация через cookie автоматически применяется ко всем запросам.
- Все методы возвращают httpx.Response — можно проверять status_code,
  .json(), .text() прямо в тесте.
- Автоматические повторные попытки при сетевых ошибках.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from webtest_kit.core.config import get_config, AuthConfig


class ApiError(Exception):
    """Выбрасывается когда API вернул неожиданный статус-код."""

    def __init__(self, response: httpx.Response):
        self.response = response
        self.status_code = response.status_code
        super().__init__(
            f"API error {response.status_code}: {response.text[:200]}"
        )


class BaseApiClient:
    """
    Базовый HTTP-клиент для API-тестов.

    Args:
        role: имя роли из config.yaml (например 'admin', 'user').
              Если указан — клиент автоматически авторизуется.
        base_url: переопределяет base_url из конфига.
        timeout: таймаут запросов в секундах.
        max_retries: количество повторных попыток при сетевой ошибке.
    """

    def __init__(
        self,
        role: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        cfg = get_config()
        self._base_url = (base_url or cfg.base_url).rstrip("/")
        self._auth_config: AuthConfig = cfg.auth
        self._timeout = timeout
        self._max_retries = max_retries
        self._role = role

        # httpx.Client сохраняет cookie между запросами
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            follow_redirects=False,
        )

        # Авторизуемся если указана роль
        if role:
            self._authenticate(role)

    # ───────────────────────── авторизация ─────────────────────────

    def _authenticate(self, role: str) -> None:
        """Выполняет вход и сохраняет cookie в клиент."""
        cfg = get_config()

        if role not in cfg.credentials:
            available = list(cfg.credentials.keys())
            raise ValueError(
                f"Role '{role}' not found in config.yaml. "
                f"Available roles: {available}"
            )

        creds = cfg.credentials[role]
        auth_cfg = cfg.auth

        if auth_cfg.type in ("cookie_jwt", "session"):
            self._login_form(
                login_url=auth_cfg.login_url,
                username=creds.username,
                password=creds.password,
                username_field=auth_cfg.username_field,
                password_field=auth_cfg.password_field,
            )
        elif auth_cfg.type == "basic":
            self._client.auth = (creds.username, creds.password)
        elif auth_cfg.type == "bearer":
            token = self._get_bearer_token(
                login_url=auth_cfg.login_url,
                username=creds.username,
                password=creds.password,
            )
            self._client.headers["Authorization"] = f"Bearer {token}"

    def _login_form(
        self,
        login_url: str,
        username: str,
        password: str,
        username_field: str = "username",
        password_field: str = "password",
    ) -> None:
        """
        Отправляет форму логина.
        Сохраняет cookie из ответа — они будут в каждом следующем запросе.
        """
        response = self._client.post(
            login_url,
            data={
                username_field: username,
                password_field: password,
            },
        )
        # Ожидаем редирект (303) как признак успешного логина
        if response.status_code not in (200, 302, 303):
            raise RuntimeError(
                f"Login failed for role '{self._role}': "
                f"status {response.status_code}, "
                f"body: {response.text[:300]}"
            )

    def _get_bearer_token(
        self,
        login_url: str,
        username: str,
        password: str,
    ) -> str:
        """
        Получает Bearer-токен через POST на login_url с JSON-телом.
        Ожидает ответ вида: {"access_token": "..."}
        """
        response = self._client.post(
            login_url,
            json={"username": username, "password": password},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Token request failed: {response.status_code} {response.text[:200]}"
            )
        data = response.json()
        if "access_token" not in data:
            raise RuntimeError(
                f"No 'access_token' in response: {data}"
            )
        return data["access_token"]

    # ───────────────────────── HTTP методы ─────────────────────────

    def get(
        self,
        path: str,
        params: Optional[dict] = None,
        **kwargs,
    ) -> httpx.Response:
        return self._request("GET", path, params=params, **kwargs)

    def post(
        self,
        path: str,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        **kwargs,
    ) -> httpx.Response:
        return self._request("POST", path, json=json, data=data, **kwargs)

    def patch(
        self,
        path: str,
        json: Optional[dict] = None,
        **kwargs,
    ) -> httpx.Response:
        return self._request("PATCH", path, json=json, **kwargs)

    def put(
        self,
        path: str,
        json: Optional[dict] = None,
        **kwargs,
    ) -> httpx.Response:
        return self._request("PUT", path, json=json, **kwargs)

    def delete(
        self,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        return self._request("DELETE", path, **kwargs)

    def _request(
        self,
        method: str,
        path: str,
        retries: int = 0,
        **kwargs,
    ) -> httpx.Response:
        """
        Выполняет HTTP-запрос с повторными попытками при сетевых ошибках.
        Логирует запрос и ответ для удобства отладки тестов.
        """
        url = path if path.startswith("http") else path
        try:
            response = self._client.request(method, url, **kwargs)
            return response
        except httpx.NetworkError as e:
            if retries < self._max_retries:
                time.sleep(0.5 * (retries + 1))
                return self._request(method, path, retries=retries + 1, **kwargs)
            raise RuntimeError(
                f"Network error after {self._max_retries} retries: {e}"
            ) from e

    # ───────────────────────── утилиты ─────────────────────────

    def assert_status(self, response: httpx.Response, expected: int) -> None:
        """
        Проверяет статус-код ответа с понятным сообщением об ошибке.

        Пример:
            response = self.client.post("/api/create", json={...})
            self.client.assert_status(response, 201)
        """
        if response.status_code != expected:
            raise AssertionError(
                f"Expected status {expected}, "
                f"got {response.status_code}.\n"
                f"URL: {response.url}\n"
                f"Body: {response.text[:500]}"
            )

    def assert_json_contains(self, response: httpx.Response, **fields) -> None:
        """
        Проверяет что JSON-ответ содержит указанные поля с указанными значениями.

        Пример:
            self.client.assert_json_contains(response, title="My Project")
        """
        data = response.json()
        for key, expected_value in fields.items():
            assert key in data, f"Key '{key}' not found in response: {data}"
            assert data[key] == expected_value, (
                f"Expected {key}={expected_value!r}, got {data[key]!r}"
            )

    def get_json(self, path: str, **kwargs) -> Any:
        """GET-запрос который сразу возвращает распарсенный JSON."""
        response = self.get(path, **kwargs)
        self.assert_status(response, 200)
        return response.json()

    def close(self) -> None:
        """Закрывает HTTP-соединение. Вызывается автоматически из фикстур."""
        self._client.close()

    def __enter__(self) -> "BaseApiClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"base_url={self._base_url!r}, "
            f"role={self._role!r})"
        )
