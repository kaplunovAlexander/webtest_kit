# pages/example_page.py
"""
Пример Page Object для вашего приложения.

Скопируй этот файл, переименуй класс и адаптируй под свои страницы.
Полная документация: https://github.com/yourusername/webtest-kit/docs/writing_tests.md
"""
from webtest_kit.core.base_page import BasePage


class ExampleLoginPage(BasePage):
    """
    Страница логина.

    Адаптируй локаторы под вёрстку твоего приложения.
    Рекомендуем добавлять data-testid атрибуты в HTML — это самый
    стабильный способ находить элементы.
    """

    # Относительный путь страницы — используется в navigate()
    URL = "/login"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)

        # ── Локаторы ──────────────────────────────────────────────
        # Вариант 1: по data-testid (рекомендуется)
        self.username_input = self.by_testid("input-username")
        self.password_input = self.by_testid("input-password")
        self.submit_btn     = self.by_testid("btn-submit")
        self.error_alert    = self.by_testid("alert-error")

        # Вариант 2: по placeholder (если нет testid)
        # self.username_input = self.by_placeholder("Enter username")
        # self.password_input = self.by_placeholder("Enter password")

        # Вариант 3: по label
        # self.username_input = self.by_label("Username")

        # Вариант 4: по роли
        # self.submit_btn = self.by_role("button", name="Sign in")

    # ── Действия ──────────────────────────────────────────────────

    def login(self, username: str, password: str) -> None:
        """Заполняет форму логина и отправляет её."""
        self.navigate()
        self.fill(self.username_input, username)
        self.fill(self.password_input, password)
        self.click(self.submit_btn)

    # ── Проверки ───────────────────────────────────────────────────

    def expect_error(self, text: str | None = None) -> None:
        """Проверяет что отображается сообщение об ошибке."""
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)

    def expect_logged_in(self) -> None:
        """Проверяет успешный логин по изменению URL."""
        # Замени /dashboard на URL куда редиректит твоё приложение после логина
        self.wait_for_url("/dashboard")


class ExampleDashboardPage(BasePage):
    """
    Пример второй страницы — главная после логина.
    Создай отдельный класс для каждой страницы твоего приложения.
    """

    URL = "/dashboard"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.heading     = self.by_role("heading")
        self.logout_link = self.by_role("link", name="Logout")

    def logout(self) -> None:
        self.click(self.logout_link)
        self.wait_for_url("/login")
