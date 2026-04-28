# demo/pages/auth_page.py
"""
Page Object-ы для страниц авторизации TaskFlow.
Наследуются от BasePage из webtest-kit.
"""
from webtest_kit.core.base_page import BasePage


class LoginPage(BasePage):
    URL = "/auth/login"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.username_input = self.by_testid("input-username")
        self.password_input = self.by_testid("input-password")
        self.submit_btn     = self.by_testid("btn-login")
        self.error_alert    = self.by_testid("alert-error")
        self.success_alert  = self.by_testid("alert-success")

    def login(self, username: str, password: str) -> None:
        self.navigate()
        self.fill(self.username_input, username)
        self.fill(self.password_input, password)
        self.click(self.submit_btn)

    def expect_error(self, text: str | None = None) -> None:
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)

    def expect_success_message(self, text: str | None = None) -> None:
        self.expect_visible(self.success_alert)
        if text:
            self.expect_text(self.success_alert, text)

    def expect_redirected_to_projects(self) -> None:
        self.wait_for_url("/projects")


class RegisterPage(BasePage):
    URL = "/auth/register"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.email_input     = self.by_testid("input-email")
        self.username_input  = self.by_testid("input-username")
        self.password_input  = self.by_testid("input-password")
        self.full_name_input = self.by_testid("input-full-name")
        self.submit_btn      = self.by_testid("btn-register")
        self.error_alert     = self.by_testid("alert-error")

    def register(
        self,
        email: str,
        username: str,
        password: str,
        full_name: str = "",
    ) -> None:
        self.navigate()
        self.fill(self.email_input, email)
        self.fill(self.username_input, username)
        self.fill(self.password_input, password)
        if full_name:
            self.fill(self.full_name_input, full_name)
        self.click(self.submit_btn)

    def expect_error(self, text: str | None = None) -> None:
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)

    def expect_redirected_to_login(self) -> None:
        self.wait_for_url("/auth/login")
