# demo/tests/test_auth_ui.py
"""
UI E2E-тесты авторизации TaskFlow через webtest-kit.

Демонстрирует использование:
- BasePage через LoginPage, RegisterPage
- admin_page, anon_page фикстуры из webtest-kit
"""
import pytest
from playwright.sync_api import expect
from demo.pages.auth_page import LoginPage, RegisterPage

pytestmark = pytest.mark.e2e


class TestLoginUi:

    def test_login_page_renders(self, anon_page, base_url):
        """Страница логина загружается корректно."""
        page = LoginPage(anon_page, base_url)
        page.navigate()
        page.expect_title("Login")
        page.expect_visible(page.username_input)
        page.expect_visible(page.password_input)
        page.expect_visible(page.submit_btn)

    def test_login_success_redirects(self, anon_page, base_url):
        """Успешный логин → редирект на /projects."""
        page = LoginPage(anon_page, base_url)
        page.login("admin", "admin123")
        page.expect_redirected_to_projects()

    def test_login_wrong_password_shows_error(self, anon_page, base_url):
        """Неверный пароль — alert с ошибкой."""
        page = LoginPage(anon_page, base_url)
        page.login("admin", "wrongpass")
        page.expect_error("Invalid username or password")
        page.expect_url_contains("/auth/login")

    def test_admin_page_already_logged_in(self, admin_page, base_url):
        """
        admin_page уже авторизован через webtest-kit AuthManager.
        Переход на /projects не требует логина.
        """
        admin_page.goto(f"{base_url}/projects")
        expect(admin_page).to_have_url(f"{base_url}/projects/")

    def test_logout_clears_session(self, anon_page, base_url):
        """После логаута доступ к /projects закрыт."""
        login = LoginPage(anon_page, base_url)
        login.login("testuser", "user1234")
        login.expect_redirected_to_projects()

        anon_page.goto(f"{base_url}/auth/logout")
        anon_page.goto(f"{base_url}/projects")
        expect(anon_page).not_to_have_url(f"{base_url}/projects")


class TestRegisterUi:

    def test_register_success(self, anon_page, base_url):
        """Успешная регистрация → редирект на логин."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        page = RegisterPage(anon_page, base_url)
        page.register(
            email=f"ui_{unique}@webtest.kit",
            username=f"ui_{unique}",
            password="password123",
            full_name="UI Demo",
        )
        page.expect_redirected_to_login()

    def test_register_duplicate_shows_error(self, anon_page, base_url):
        """Дубликат username — alert с ошибкой."""
        page = RegisterPage(anon_page, base_url)
        page.register(
            email="any@email.com",
            username="admin",          # уже существует
            password="password123",
        )
        page.expect_error("already taken")
