# webtest_kit/core/fixtures.py
"""
Универсальные pytest-фикстуры webtest-kit.

Как это работает для пользователя:
    1. Пользователь добавляет в conftest.py своего проекта:
           pytest_plugins = ["webtest_kit.core.fixtures"]
    2. Все фикстуры отсюда становятся доступны во всех тестах.
    3. Для каждой роли из config.yaml автоматически создаются:
           {role}_page    — авторизованная страница браузера
           {role}_client  — авторизованный API-клиент

    Пример: если в config.yaml есть роли admin, manager, user — то
    в тестах будут доступны admin_page, manager_page, user_page,
    admin_client, manager_client, user_client.

Архитектурное решение:
    Фикстуры уровня session создаются один раз на весь прогон.
    Фикстуры уровня function создаются заново для каждого теста.
    Это баланс между скоростью (меньше логинов) и изоляцией
    (каждый тест получает чистую вкладку).
"""
from __future__ import annotations

from typing import Generator

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from webtest_kit.core.auth import AuthManager
from webtest_kit.core.base_client import BaseApiClient
from webtest_kit.core.config import get_config


# ───────────────────────── Playwright ─────────────────────────

@pytest.fixture(scope="session")
def webtest_playwright() -> Generator[Playwright, None, None]:
    """Запускает Playwright один раз на всю сессию."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def webtest_browser(webtest_playwright: Playwright) -> Generator[Browser, None, None]:
    """
    Запускает браузер согласно настройкам из config.yaml.
    Один экземпляр на всю тестовую сессию.
    """
    cfg = get_config()
    browser_type = getattr(webtest_playwright, cfg.browser.name)
    browser = browser_type.launch(
        headless=cfg.browser.headless,
        slow_mo=cfg.browser.slowmo,
    )
    yield browser
    browser.close()


# ───────────────────────── AuthManager ─────────────────────────

@pytest.fixture(scope="session")
def webtest_auth(webtest_browser: Browser) -> Generator[AuthManager, None, None]:
    """
    Создаёт AuthManager — управляет авторизованными контекстами.
    Живёт всю сессию: один логин для каждой роли на все тесты.
    """
    auth = AuthManager(webtest_browser)
    yield auth
    auth.close_all()


# ───────────────────────── Анонимные фикстуры ─────────────────────────

@pytest.fixture
def anon_context(webtest_browser: Browser) -> Generator[BrowserContext, None, None]:
    """Неавторизованный контекст браузера. Новый для каждого теста."""
    cfg = get_config()
    context = webtest_browser.new_context(
        viewport={
            "width": cfg.browser.viewport_width,
            "height": cfg.browser.viewport_height,
        }
    )
    yield context
    context.close()


@pytest.fixture
def anon_page(anon_context: BrowserContext) -> Generator[Page, None, None]:
    """Неавторизованная страница. Новая для каждого теста."""
    cfg = get_config()
    page = anon_context.new_page()
    page.set_default_timeout(cfg.browser.timeout)
    yield page

    # Скриншот при падении теста
    if cfg.report.screenshot_on_failure:
        _take_failure_screenshot(page, "anon")

    page.close()


@pytest.fixture
def anon_client() -> Generator[BaseApiClient, None, None]:
    """Неавторизованный API-клиент."""
    client = BaseApiClient()
    yield client
    client.close()


# ───────────────────────── Динамические фикстуры по ролям ─────────────────────────

def _make_page_fixture(role: str):
    """
    Фабрика фикстур для страниц.
    Создаёт фикстуру {role}_page для указанной роли.

    Каждый тест получает новую вкладку в авторизованном контексте роли.
    Cookie авторизации уже установлены — логин не нужен.
    """
    @pytest.fixture(name=f"{role}_page")
    def page_fixture(
        webtest_auth: AuthManager,
    ) -> Generator[Page, None, None]:
        cfg = get_config()
        page = webtest_auth.get_page(role)
        yield page

        # Скриншот при падении теста если включено в конфиге
        if cfg.report.screenshot_on_failure:
            _take_failure_screenshot(page, role)

        page.close()

    # Даём фикстуре уникальное имя для pytest
    page_fixture.__name__ = f"{role}_page"
    return page_fixture


def _make_client_fixture(role: str):
    """
    Фабрика фикстур для API-клиентов.
    Создаёт фикстуру {role}_client для указанной роли.

    Каждый тест получает новый HTTP-клиент с авторизацией роли.
    """
    @pytest.fixture(name=f"{role}_client")
    def client_fixture() -> Generator[BaseApiClient, None, None]:
        client = BaseApiClient(role=role)
        yield client
        client.close()

    client_fixture.__name__ = f"{role}_client"
    return client_fixture


def _register_role_fixtures(roles: list[str]) -> None:
    """
    Регистрирует фикстуры для всех ролей из конфига в глобальном модуле.
    Вызывается при импорте модуля.
    """
    import sys
    current_module = sys.modules[__name__]

    for role in roles:
        # Регистрируем {role}_page
        page_fixture = _make_page_fixture(role)
        setattr(current_module, f"{role}_page", page_fixture)

        # Регистрируем {role}_client
        client_fixture = _make_client_fixture(role)
        setattr(current_module, f"{role}_client", client_fixture)


# Регистрируем фикстуры при импорте модуля
try:
    cfg = get_config()
    _register_role_fixtures(list(cfg.credentials.keys()))
except SystemExit:
    # config.yaml ещё не создан — это нормально при инициализации проекта
    pass


# ───────────────────────── base_url фикстура ─────────────────────────

@pytest.fixture(scope="session")
def base_url() -> str:
    """Возвращает base_url из config.yaml. Используется в Page Object-ах."""
    return get_config().base_url


# ───────────────────────── вспомогательные ─────────────────────────

def _take_failure_screenshot(page: Page, role: str) -> None:
    """
    Делает скриншот если тест упал.
    Pytest передаёт информацию о провале через request.node,
    но в фикстуре без request мы проверяем через sys.exc_info.
    """
    import sys
    from pathlib import Path

    # Проверяем есть ли активное исключение (тест упал)
    if sys.exc_info()[0] is None:
        return

    try:
        screenshots_dir = Path("reports") / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # Имя файла: роль + URL страницы в момент падения
        safe_url = page.url.replace("://", "_").replace("/", "_")[:50]
        filename = f"{role}_{safe_url}.png"

        page.screenshot(
            path=str(screenshots_dir / filename),
            full_page=True,
        )
    except Exception:
        # Не прерываем teardown если скриншот не получился
        pass
