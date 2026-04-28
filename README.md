# webtest-kit

A framework for automated functional testing of web applications built on Python, pytest and Playwright.

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org)
[![pytest](https://img.shields.io/badge/pytest-8.x-green)](https://pytest.org)
[![Playwright](https://img.shields.io/badge/playwright-1.x-orange)](https://playwright.dev/python)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## What is webtest-kit?

**webtest-kit** solves a common problem: setting up automated functional tests
for a web application takes time — configuring pytest, Playwright, authentication,
fixtures for different user roles, report generation.

webtest-kit gives you all of this out of the box. You describe your application
in a single `config.yaml` file, and the framework automatically provides:

- authenticated browser pages for each role (`admin_page`, `manager_page`, ...)
- authenticated API clients for each role (`admin_client`, `user_client`, ...)
- two-layer test architecture: fast API tests + full E2E browser tests
- screenshot on failure
- HTML and Allure report generation

---

## Installation

```bash
pip install webtest-kit
playwright install chromium
```

**Requirements:** Python 3.11 or 3.12

---

## Quickstart

```bash
# 1. Create a new test project
webtest-kit init my_app_tests
cd my_app_tests

# 2. Fill in your site URL and credentials
nano config.yaml

# 3. Run tests
webtest-kit run

# 4. View report
webtest-kit run --html-report
webtest-kit report --type html
```

---

## How it works

### 1. Describe your application in `config.yaml`

```yaml
base_url: http://localhost:8000

credentials:
  admin:
    username: admin
    password: secret
  user:
    username: regular
    password: pass123

auth:
  type: cookie_jwt
  login_url: /auth/login
  username_field: username
  password_field: password

browser:
  name: chromium
  headless: true
  timeout: 8000
```

### 2. Describe your pages using Page Object Model

```python
# pages/login_page.py
from webtest_kit.core.base_page import BasePage

class LoginPage(BasePage):
    URL = "/auth/login"

    def __init__(self, page, base_url=None):
        super().__init__(page, base_url)
        self.username_input = self.by_testid("input-username")
        self.password_input = self.by_testid("input-password")
        self.submit_btn     = self.by_testid("btn-submit")
        self.error_alert    = self.by_testid("alert-error")

    def login(self, username, password):
        self.navigate()
        self.fill(self.username_input, username)
        self.fill(self.password_input, password)
        self.click(self.submit_btn)

    def expect_error(self, text=None):
        self.expect_visible(self.error_alert)
        if text:
            self.expect_text(self.error_alert, text)
```

### 3. Write tests — fixtures are already there

```python
# tests/test_login.py
import pytest
from pages.login_page import LoginPage

pytestmark = pytest.mark.e2e

class TestLogin:

    def test_admin_is_authenticated(self, admin_page, base_url):
        # admin_page is already logged in — no manual login needed
        admin_page.goto(f"{base_url}/dashboard")
        assert "dashboard" in admin_page.url

    def test_wrong_password_shows_error(self, anon_page, base_url):
        page = LoginPage(anon_page, base_url)
        page.login("admin", "wrong")
        page.expect_error("Invalid username or password")

    def test_user_cannot_access_admin(self, user_page, base_url):
        user_page.goto(f"{base_url}/admin")
        assert "403" in user_page.locator("body").inner_text()
```

```python
# tests/test_api.py
import pytest

pytestmark = pytest.mark.api

class TestApi:

    def test_admin_can_create_resource(self, admin_client):
        response = admin_client.post("/api/items", json={"name": "Test"})
        admin_client.assert_status(response, 201)

    def test_user_cannot_create_resource(self, user_client):
        response = user_client.post("/api/items", json={"name": "Test"})
        user_client.assert_status(response, 403)

    def test_list_returns_array(self, admin_client):
        data = admin_client.get_json("/api/items")
        assert isinstance(data, list)
```

---

## CLI Commands

| Command | Description |
|---|---|
| `webtest-kit init <name>` | Create new test project with scaffold |
| `webtest-kit run` | Run all tests |
| `webtest-kit run --headed` | Run with visible browser window |
| `webtest-kit run --slowmo=500` | Slow down browser actions (ms) |
| `webtest-kit run --api-only` | Run only API tests (fast, no browser) |
| `webtest-kit run --e2e-only` | Run only UI browser tests |
| `webtest-kit run --html-report` | Generate HTML report |
| `webtest-kit run --allure` | Generate Allure report data |
| `webtest-kit run -k "test_login"` | Run tests matching keyword |
| `webtest-kit report` | Open Allure report in browser |
| `webtest-kit report --type html` | Open HTML report in browser |

---

## Project structure after `webtest-kit init`

```
my_app_tests/
├── config.yaml          ← your app URL, credentials, browser settings
├── conftest.py          ← ready to use, connects webtest-kit fixtures
├── pytest.ini           ← pytest configuration
├── pages/
│   └── example_page.py  ← copy and adapt for your pages
├── tests/
│   ├── test_api_example.py   ← API test examples
│   └── test_ui_example.py    ← UI test examples
└── reports/             ← test reports appear here
```

---

## Available fixtures

After adding `pytest_plugins = ["webtest_kit.core.fixtures"]` to your `conftest.py`,
these fixtures are available automatically:

| Fixture | Scope | Description |
|---|---|---|
| `{role}_page` | function | Authenticated Playwright page for role |
| `{role}_client` | function | Authenticated httpx API client for role |
| `anon_page` | function | Unauthenticated browser page |
| `anon_client` | function | Unauthenticated API client |
| `base_url` | session | Base URL from config.yaml |

Roles are defined in `config.yaml` under `credentials`.
If you define `admin`, `manager`, `user` — you get
`admin_page`, `manager_page`, `user_page`, `admin_client`, `manager_client`, `user_client`.

---

## Supported authentication types

| Type | Description |
|---|---|
| `cookie_jwt` | POST form login, JWT stored in cookie |
| `session` | POST form login, session cookie |
| `basic` | HTTP Basic Auth |
| `bearer` | Bearer token in Authorization header |

---

## Demo project

The `demo/` folder contains a complete working example:
a TaskFlow task manager application with full API and E2E test suites.

```bash
# Run the demo application
cd demo/backend
python seed.py
uvicorn app.main:app --reload

# Run demo tests (in another terminal)
cd demo
webtest-kit run --api-only
webtest-kit run --e2e-only --headed
```

---

## Documentation

- [Quickstart](docs/quickstart.md)
- [Configuration reference](docs/configuration.md)
- [Writing tests](docs/writing_tests.md)

---

## License

MIT — see [LICENSE](LICENSE)