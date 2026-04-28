# Writing Tests

## Project structure

```
my_app_tests/
├── config.yaml
├── conftest.py
├── pages/            ← Page Objects — one file per page
│   ├── login_page.py
│   ├── dashboard_page.py
│   └── settings_page.py
└── tests/            ← Test files
    ├── test_auth_api.py
    ├── test_auth_ui.py
    └── test_dashboard_ui.py
```

## Two test layers

webtest-kit encourages two layers of tests:

**API tests** — fast, no browser, test business logic directly:
```python
pytestmark = pytest.mark.api   # run with: webtest-kit run --api-only
```

**E2E tests** — full browser, test user scenarios end-to-end:
```python
pytestmark = pytest.mark.e2e   # run with: webtest-kit run --e2e-only
```

Run API tests on every change (seconds). Run E2E tests before releases (minutes).

---

## Page Object Model

Create one class per page. Keep all locators inside the class.

```python
from webtest_kit.core.base_page import BasePage

class DashboardPage(BasePage):
    URL = "/dashboard"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)

        # Locators — prefer data-testid
        self.heading     = self.by_testid("dashboard-heading")
        self.new_btn     = self.by_role("button", name="New item")
        self.items_table = self.by_testid("items-table")

    # Actions — one method per user action
    def open_new_item_form(self):
        self.click(self.new_btn)

    def get_item_count(self):
        return self.count(self.by_testid("item-row"))

    # Assertions — one method per check
    def expect_heading(self, text):
        self.expect_text(self.heading, text)

    def expect_item_visible(self, name):
        self.expect_visible(
            self.by_testid("item-link").filter(has_text=name)
        )
```

---

## Locator strategies (best to worst)

```python
# 1. data-testid — best, stable, not affected by style changes
self.by_testid("btn-submit")

# 2. ARIA role — accessible, semantic
self.by_role("button", name="Submit")
self.by_role("link", name="Dashboard")

# 3. Label — good for form fields
self.by_label("Email address")

# 4. Placeholder — acceptable for inputs
self.by_placeholder("Enter your email")

# 5. Text — fragile, breaks on copy changes
self.by_text("Submit")

# 6. CSS — avoid if possible
self.by_css(".btn-primary")

# 7. XPath — last resort only
self.by_xpath("//button[@type='submit']")
```

---

## API client

```python
from webtest_kit.core.base_client import BaseApiClient

class MyAppClient(BaseApiClient):

    def get_items(self):
        return self.get("/api/items")

    def create_item(self, name):
        return self.post("/api/items", json={"name": name})

    def delete_item(self, item_id):
        return self.delete(f"/api/items/{item_id}")
```

Use in tests:

```python
def test_create_item(self, admin_client):
    response = admin_client.post("/api/items", json={"name": "Test"})
    admin_client.assert_status(response, 201)
    admin_client.assert_json_contains(response, name="Test")
```

---

## Fixtures

```python
# Pre-built fixtures from webtest-kit (defined by roles in config.yaml)
def test_example(
    admin_page,      # authenticated Playwright Page for admin role
    manager_client,  # authenticated httpx client for manager role
    anon_page,       # unauthenticated browser page
    anon_client,     # unauthenticated API client
    base_url,        # base_url from config.yaml
):
    ...
```

Add custom fixtures in `conftest.py`:

```python
# conftest.py
import pytest

pytest_plugins = ["webtest_kit.core.fixtures"]

@pytest.fixture
def existing_item(admin_client):
    """Creates an item and deletes it after the test."""
    response = admin_client.post("/api/items", json={"name": "Fixture Item"})
    item_id = response.json()["id"]
    yield item_id
    admin_client.delete(f"/api/items/{item_id}")
```

---

## Test isolation best practices

**Use unique names** to avoid conflicts between test runs:

```python
import uuid

def test_create_user(self, admin_client):
    unique = uuid.uuid4().hex[:8]
    response = admin_client.post("/api/users", json={
        "username": f"testuser_{unique}",
        "email": f"test_{unique}@example.com",
    })
    admin_client.assert_status(response, 201)
```

**Use fixtures for shared resources:**

```python
@pytest.fixture
def project(manager_client):
    response = manager_client.post("/api/projects", json={"title": "Test"})
    project_id = response.json()["id"]
    yield project_id
    manager_client.delete(f"/api/projects/{project_id}")
```

---

## Running tests

```bash
webtest-kit run                    # all tests
webtest-kit run --api-only         # API only (fast)
webtest-kit run --e2e-only         # E2E only
webtest-kit run --headed           # visible browser
webtest-kit run --headed --slowmo=1000   # slow for debugging
webtest-kit run -k "test_login"    # by name
webtest-kit run --html-report      # with HTML report
```