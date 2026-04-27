# tests/test_ui_example.py
"""
Пример E2E UI-тестов с использованием webtest-kit.

Фикстуры {role}_page создаются автоматически для каждой роли
из вашего config.yaml. Каждый тест получает новую вкладку
с уже установленными cookie авторизации.

Запуск только E2E-тестов:
    webtest-kit run --e2e-only

Запуск с видимым браузером (удобно при написании тестов):
    webtest-kit run --e2e-only --headed
"""
import pytest
from playwright.sync_api import expect

# Импортируй свои Page Object-ы
# from pages.example_page import ExampleLoginPage

pytestmark = pytest.mark.e2e


class TestLoginUi:
    """Пример UI-тестов страницы логина."""

    def test_login_page_loads(self, anon_page, base_url):
        """Страница логина открывается без ошибок."""
        anon_page.goto(f"{base_url}/login")   # замени на свой URL логина
        # Замени на заголовок твоей страницы
        expect(anon_page).to_have_title("Login")

    def test_admin_sees_dashboard(self, admin_page, base_url):
        """
        Admin открывает главную страницу и видит контент.
        admin_page уже авторизован — логин не нужен.
        """
        admin_page.goto(f"{base_url}/dashboard")  # замени на свой URL
        # Замени на элемент который видит только авторизованный пользователь
        expect(admin_page.get_by_role("heading")).to_be_visible()

    def test_anon_redirected_to_login(self, anon_page, base_url):
        """Неавторизованный пользователь перенаправляется на логин."""
        anon_page.goto(f"{base_url}/dashboard")  # замени на защищённый URL
        # После редиректа должны оказаться на странице логина
        expect(anon_page).to_have_url(f"{base_url}/login")


class TestAccessControl:
    """Пример тестов разграничения прав доступа."""

    def test_admin_sees_admin_panel(self, admin_page, base_url):
        """Admin видит административный раздел."""
        admin_page.goto(f"{base_url}/admin")    # замени на свой URL
        expect(admin_page.locator("body")).not_to_contain_text("403")

    def test_user_cannot_see_admin_panel(self, user_page, base_url):
        """Обычный user получает отказ в доступе."""
        user_page.goto(f"{base_url}/admin")     # замени на свой URL
        # Ожидаем 403 или редирект
        expect(user_page.locator("body")).to_contain_text("403")
