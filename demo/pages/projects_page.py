# demo/pages/projects_page.py
from webtest_kit.core.base_page import BasePage


class ProjectsListPage(BasePage):
    URL = "/projects"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.new_project_btn = self.by_testid("btn-new-project")
        self.projects_table  = self.by_testid("projects-table")
        self.empty_state     = self.by_testid("empty-state")

    def open_new_project_form(self) -> "ProjectFormPage":
        self.click(self.new_project_btn)
        return ProjectFormPage(self.page, self._base_url)

    def find_project_link(self, title: str):
        return self.by_testid("project-link").filter(has_text=title)

    def expect_project_visible(self, title: str) -> None:
        self.expect_visible(self.find_project_link(title))

    def expect_project_not_visible(self, title: str) -> None:
        self.expect_hidden(self.find_project_link(title))

    def get_project_count(self) -> int:
        return self.count(self.by_testid("project-row"))


class ProjectFormPage(BasePage):

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.title_input       = self.by_testid("input-title")
        self.description_input = self.by_testid("input-description")
        self.submit_btn        = self.by_testid("btn-submit")
        self.cancel_btn        = self.by_testid("btn-cancel")
        self.error_alert       = self.by_testid("alert-error")
        self.delete_btn        = self.by_testid("btn-delete-project")

    def fill_and_submit(self, title: str, description: str = "") -> None:
        self.fill(self.title_input, title)
        if description:
            self.fill(self.description_input, description)
        self.click(self.submit_btn)

    def expect_error(self, text: str | None = None) -> None:
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)

    def delete_project(self) -> None:
        self.accept_dialog()
        self.click(self.delete_btn)


class ProjectDetailPage(BasePage):

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.project_title = self.by_testid("project-title")
        self.edit_btn      = self.by_testid("btn-edit")
        self.new_task_btn  = self.by_testid("btn-new-task")
        self.tasks_table   = self.by_testid("tasks-table")
        self.tasks_empty   = self.by_testid("tasks-empty")

    def navigate_to(self, project_id: int) -> "ProjectDetailPage":
        self.navigate(f"/projects/{project_id}")
        return self

    def open_edit_form(self) -> ProjectFormPage:
        self.click(self.edit_btn)
        return ProjectFormPage(self.page, self._base_url)

    def open_new_task_form(self) -> None:
        self.click(self.new_task_btn)

    def expect_title(self, text: str) -> None:
        self.expect_text(self.project_title, text)

    def expect_task_visible(self, title: str) -> None:
        self.expect_visible(
            self.by_testid("task-link").filter(has_text=title)
        )

    def get_task_count(self) -> int:
        return self.count(self.by_testid("task-row"))
