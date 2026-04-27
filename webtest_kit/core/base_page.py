# webtest_kit/core/base_page.py
"""
BasePage — базовый класс для всех Page Object-ов.

Пользователь наследуется от него и описывает свою страницу:

    from webtest_kit.core.base_page import BasePage

    class LoginPage(BasePage):
        URL = "/auth/login"

        def __init__(self, page, base_url):
            super().__init__(page, base_url)
            self.username_input = self.by_testid("input-username")
            self.password_input = self.by_testid("input-password")
            self.submit_btn     = self.by_testid("btn-submit")

        def login(self, username, password):
            self.navigate()
            self.username_input.fill(username)
            self.password_input.fill(password)
            self.submit_btn.click()

Почему такой подход:
- Все локаторы — в одном месте (классе страницы).
- Тесты не знают про CSS, xpath, testid — они вызывают методы.
- При изменении вёрстки правишь только класс страницы, не тесты.
"""
from __future__ import annotations

import re
from typing import Optional

from playwright.sync_api import Page, Locator, expect, TimeoutError as PlaywrightTimeout

from webtest_kit.core.config import get_config


class BasePage:
    """
    Базовый класс для Page Object Model.

    Attributes:
        URL: относительный путь страницы. Переопределяется в подклассах.
             Используется методом navigate().
    """

    URL: str = "/"

    def __init__(self, page: Page, base_url: Optional[str] = None):
        self.page = page
        self._base_url = (base_url or get_config().base_url).rstrip("/")
        self._timeout = get_config().browser.timeout

    # ───────────────────────── навигация ─────────────────────────

    def navigate(self, url: Optional[str] = None) -> "BasePage":
        """
        Переходит на страницу.
        Если url не указан — использует self.URL.

        Returns:
            self — для цепочки вызовов: page.navigate().fill_form()
        """
        target = url or self.URL
        if not target.startswith("http"):
            target = f"{self._base_url}{target}"
        self.page.goto(target)
        return self

    def navigate_to(self, path: str) -> "BasePage":
        """Переходит на произвольный путь относительно base_url."""
        self.page.goto(f"{self._base_url}{path}")
        return self

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    # ───────────────────────── локаторы ─────────────────────────

    def by_testid(self, testid: str) -> Locator:
        """
        Локатор по data-testid атрибуту.
        Рекомендуемый способ — не зависит от CSS и текста.

        Пример в HTML: <button data-testid="btn-submit">Save</button>
        """
        return self.page.get_by_test_id(testid)

    def by_text(self, text: str, exact: bool = False) -> Locator:
        """Локатор по видимому тексту элемента."""
        return self.page.get_by_text(text, exact=exact)

    def by_label(self, label: str) -> Locator:
        """Локатор поля формы по тексту его label."""
        return self.page.get_by_label(label)

    def by_placeholder(self, placeholder: str) -> Locator:
        """Локатор поля по placeholder атрибуту."""
        return self.page.get_by_placeholder(placeholder)

    def by_role(self, role: str, name: Optional[str] = None) -> Locator:
        """
        Локатор по ARIA-роли. Наиболее доступный способ.

        Примеры:
            self.by_role("button", name="Submit")
            self.by_role("link", name="Register")
            self.by_role("heading", name="Dashboard")
        """
        kwargs = {}
        if name:
            kwargs["name"] = name
        return self.page.get_by_role(role, **kwargs)

    def by_css(self, selector: str) -> Locator:
        """Локатор по CSS-селектору. Используй только если нет лучшего варианта."""
        return self.page.locator(selector)

    def by_xpath(self, xpath: str) -> Locator:
        """Локатор по XPath. Используй только в крайнем случае."""
        return self.page.locator(f"xpath={xpath}")

    # ───────────────────────── действия ─────────────────────────

    def click(self, locator: Locator) -> None:
        """Клик с ожиданием видимости элемента."""
        locator.wait_for(state="visible", timeout=self._timeout)
        locator.click()

    def fill(self, locator: Locator, value: str) -> None:
        """Очищает поле и вводит значение."""
        locator.wait_for(state="visible", timeout=self._timeout)
        locator.clear()
        locator.fill(value)

    def select(self, locator: Locator, value: str) -> None:
        """Выбирает опцию в select по значению value атрибута."""
        locator.select_option(value)

    def submit_form(self, locator: Locator) -> None:
        """Нажимает кнопку submit и ждёт окончания навигации."""
        with self.page.expect_navigation():
            locator.click()

    def accept_dialog(self) -> None:
        """
        Регистрирует обработчик для автоматического принятия
        следующего confirm/alert диалога.
        """
        self.page.once("dialog", lambda d: d.accept())

    def dismiss_dialog(self) -> None:
        """Автоматически отклоняет следующий диалог."""
        self.page.once("dialog", lambda d: d.dismiss())

    def scroll_to_bottom(self) -> None:
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_to_top(self) -> None:
        self.page.evaluate("window.scrollTo(0, 0)")

    # ───────────────────────── ожидания ─────────────────────────

    def wait_for_url(self, pattern: str, timeout: Optional[int] = None) -> None:
        """
        Ждёт пока URL совпадёт с паттерном (строка или regex).

        Примеры:
            self.wait_for_url("/dashboard")
            self.wait_for_url(r"/projects/\d+")
        """
        ms = timeout or self._timeout
        if re.search(r"[\^\$\.\*\+\?\{\}\[\]\|\\]", pattern):
            self.page.wait_for_url(re.compile(pattern), timeout=ms)
        else:
            self.page.wait_for_url(f"**{pattern}**", timeout=ms)

    def wait_for_element(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """Ждёт пока элемент станет видимым."""
        locator.wait_for(state="visible", timeout=timeout or self._timeout)

    def wait_for_element_hidden(self, locator: Locator, timeout: Optional[int] = None) -> None:
        """Ждёт пока элемент скроется."""
        locator.wait_for(state="hidden", timeout=timeout or self._timeout)

    def wait_for_network_idle(self) -> None:
        """Ждёт завершения всех сетевых запросов."""
        self.page.wait_for_load_state("networkidle")

    # ───────────────────────── проверки ─────────────────────────

    def expect_url_contains(self, substring: str) -> None:
        """Проверяет что текущий URL содержит подстроку."""
        expect(self.page).to_have_url(re.compile(re.escape(substring)))

    def expect_title(self, text: str) -> None:
        """Проверяет заголовок страницы."""
        expect(self.page).to_have_title(re.compile(text))

    def expect_visible(self, locator: Locator) -> None:
        expect(locator).to_be_visible()

    def expect_hidden(self, locator: Locator) -> None:
        expect(locator).not_to_be_visible()

    def expect_text(self, locator: Locator, text: str) -> None:
        expect(locator).to_contain_text(text)

    def expect_value(self, locator: Locator, value: str) -> None:
        expect(locator).to_have_value(value)

    def expect_enabled(self, locator: Locator) -> None:
        expect(locator).to_be_enabled()

    def expect_disabled(self, locator: Locator) -> None:
        expect(locator).to_be_disabled()

    # ───────────────────────── скриншоты ─────────────────────────

    def screenshot(self, path: str) -> None:
        """Сохраняет скриншот страницы."""
        self.page.screenshot(path=path, full_page=True)

    def screenshot_element(self, locator: Locator, path: str) -> None:
        """Сохраняет скриншот конкретного элемента."""
        locator.screenshot(path=path)

    # ───────────────────────── утилиты ─────────────────────────

    def is_visible(self, locator: Locator) -> bool:
        """Возвращает True если элемент виден, без броска исключения."""
        try:
            return locator.is_visible()
        except PlaywrightTimeout:
            return False

    def get_text(self, locator: Locator) -> str:
        """Возвращает текстовое содержимое элемента."""
        return locator.inner_text()

    def get_value(self, locator: Locator) -> str:
        """Возвращает значение поля ввода."""
        return locator.input_value()

    def get_all_texts(self, locator: Locator) -> list[str]:
        """Возвращает текст всех элементов совпадающих с локатором."""
        return locator.all_inner_texts()

    def count(self, locator: Locator) -> int:
        """Возвращает количество элементов совпадающих с локатором."""
        return locator.count()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(url={self.current_url!r})"
