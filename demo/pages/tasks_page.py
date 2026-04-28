# demo/pages/tasks_page.py
from webtest_kit.core.base_page import BasePage


class TaskFormPage(BasePage):

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.title_input       = self.by_testid("input-title")
        self.description_input = self.by_testid("input-description")
        self.status_select     = self.by_testid("select-status")
        self.priority_select   = self.by_testid("select-priority")
        self.due_date_input    = self.by_testid("input-due-date")
        self.assignee_select   = self.by_testid("select-assignee")
        self.submit_btn        = self.by_testid("btn-submit")
        self.error_alert       = self.by_testid("alert-error")

    def fill(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
        priority: str = "medium",
        due_date: str = "",
    ) -> "TaskFormPage":
        super().fill(self.title_input, title)
        if description:
            super().fill(self.description_input, description)
        self.select(self.status_select, status)
        self.select(self.priority_select, priority)
        if due_date:
            super().fill(self.due_date_input, due_date)
        return self

    def submit(self) -> None:
        self.click(self.submit_btn)

    def fill_and_submit(self, title: str, **kwargs) -> None:
        self.fill(title, **kwargs)
        self.submit()

    def click_quick_status(self, status: str) -> None:
        btn = self.by_testid(f"quick-status-{status}")
        self.expect_visible(btn)
        self.click(btn)

    def expect_error(self, text: str | None = None) -> None:
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)
