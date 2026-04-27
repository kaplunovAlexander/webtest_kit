# webtest_kit/core/auth.py
"""
AuthManager — менеджер авторизации для браузерных контекстов.

Отвечает за:
- создание авторизованного контекста браузера для каждой роли
- кеширование состояния авторизации (storageState) между тестами
- поддержку разных типов авторизации из конфига

Почему кешируем storageState:
    Без кеша каждый тест открывал бы браузер, заходил на /login,
    заполнял форму — это медленно. Playwright позволяет сохранить
    cookie и localStorage в файл и восстановить их мгновенно.
    Один логин на всю сессию — все тесты роли используют его результат.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page

from webtest_kit.core.config import get_config, WebtestKitConfig


class AuthManager:
    """
    Управляет авторизованными контекстами браузера.

    Использование в фикстурах:
        auth = AuthManager(browser)
        context = auth.get_context("admin")
        page = context.new_page()
    """

    # Папка для хранения storageState файлов
    STATE_DIR = Path(".webtest_cache")

    def __init__(self, browser: Browser, config: Optional[WebtestKitConfig] = None):
        self._browser = browser
        self._cfg = config or get_config()
        self._contexts: dict[str, BrowserContext] = {}

        # Создаём папку для кеша если нет
        self.STATE_DIR.mkdir(exist_ok=True)

    def get_context(self, role: str) -> BrowserContext:
        """
        Возвращает авторизованный контекст браузера для роли.
        При первом вызове — логинится и кеширует.
        При повторном — возвращает существующий контекст.

        Args:
            role: имя роли из config.yaml (admin, manager, user, ...)

        Returns:
            BrowserContext с установленными cookie авторизации
        """
        if role not in self._contexts:
            self._contexts[role] = self._create_context(role)
        return self._contexts[role]

    def get_page(self, role: str) -> Page:
        """
        Создаёт новую страницу в авторизованном контексте роли.
        Используется в фикстурах уровня function — каждый тест
        получает чистую вкладку но с сохранёнными cookie.
        """
        context = self.get_context(role)
        page = context.new_page()
        page.set_default_timeout(self._cfg.browser.timeout)
        return page

    def _create_context(self, role: str) -> BrowserContext:
        """
        Создаёт новый контекст, логинится и сохраняет storageState.
        """
        if role not in self._cfg.credentials:
            available = list(self._cfg.credentials.keys())
            raise ValueError(
                f"Role '{role}' not found in config.yaml. "
                f"Available: {available}"
            )

        state_file = self.STATE_DIR / f"auth_{role}.json"

        # Если есть сохранённый state — восстанавливаем без логина
        if state_file.exists():
            context = self._browser.new_context(
                storage_state=str(state_file),
                viewport={
                    "width": self._cfg.browser.viewport_width,
                    "height": self._cfg.browser.viewport_height,
                },
            )
            # Проверяем что сессия ещё валидна
            if self._is_session_valid(context):
                return context
            # Сессия истекла — логинимся заново
            context.close()
            state_file.unlink(missing_ok=True)

        # Создаём чистый контекст и логинимся
        context = self._browser.new_context(
            viewport={
                "width": self._cfg.browser.viewport_width,
                "height": self._cfg.browser.viewport_height,
            }
        )
        self._login(context, role)

        # Сохраняем состояние для следующих запусков
        context.storage_state(path=str(state_file))

        return context

    def _login(self, context: BrowserContext, role: str) -> None:
        """Выполняет логин через браузер для указанной роли."""
        creds = self._cfg.credentials[role]
        auth = self._cfg.auth
        base_url = self._cfg.base_url

        page = context.new_page()
        try:
            page.goto(f"{base_url}{auth.login_url}")

            if auth.type in ("cookie_jwt", "session"):
                self._login_form(page, creds.username, creds.password)
            elif auth.type == "basic":
                # Basic Auth передаётся в URL — браузер сохраняет в context
                page.goto(
                    f"{base_url.replace('://', f'://{creds.username}:{creds.password}@')}"
                    f"{auth.login_url}"
                )
            elif auth.type == "bearer":
                self._login_bearer(page, creds.username, creds.password)

        finally:
            page.close()

    def _login_form(self, page: Page, username: str, password: str) -> None:
        """Заполняет и отправляет форму логина."""
        auth = self._cfg.auth
        base_url = self._cfg.base_url

        page.get_by_label(auth.username_field).or_(
            page.locator(f"[name='{auth.username_field}']")
        ).fill(username)

        page.get_by_label(auth.password_field).or_(
            page.locator(f"[name='{auth.password_field}']")
        ).fill(password)

        page.locator("button[type='submit']").click()

        # Ждём навигации после логина
        try:
            page.wait_for_url(
                lambda url: url != f"{base_url}{auth.login_url}",
                timeout=8000,
            )
        except Exception:
            raise RuntimeError(
                f"Login failed: still on {page.url} after form submit. "
                f"Check credentials in config.yaml."
            )

    def _login_bearer(self, page: Page, username: str, password: str) -> None:
        """
        Получает Bearer-токен через форму и сохраняет в localStorage.
        Это позволяет Playwright подхватить токен через storageState.
        """
        self._login_form(page, username, password)
        # Если приложение сохраняет токен в localStorage — он попадёт в state

    def _is_session_valid(self, context: BrowserContext) -> bool:
        """
        Проверяет что сохранённая сессия ещё действительна.
        Делает тихий запрос на защищённый эндпоинт.
        """
        import httpx
        cookies = {c["name"]: c["value"] for c in context.cookies()}
        try:
            response = httpx.get(
                f"{self._cfg.base_url}/auth/me",
                cookies=cookies,
                timeout=3.0,
                follow_redirects=False,
            )
            return response.status_code == 200
        except Exception:
            return False

    def close_all(self) -> None:
        """Закрывает все контексты. Вызывается в teardown сессии."""
        for context in self._contexts.values():
            context.close()
        self._contexts.clear()

    def clear_cache(self) -> None:
        """Удаляет все сохранённые storageState файлы."""
        for f in self.STATE_DIR.glob("auth_*.json"):
            f.unlink()
