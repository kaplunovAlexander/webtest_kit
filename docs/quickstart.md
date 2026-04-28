# Quickstart

This guide walks you through setting up webtest-kit for your web application
from scratch in under 10 minutes.

## Prerequisites

- Python 3.11 or 3.12
- A running web application to test

## Step 1 — Install

```bash
pip install webtest-kit
playwright install chromium
```

## Step 2 — Create a test project

```bash
webtest-kit init my_app_tests
cd my_app_tests
```

You will get this structure:

```
my_app_tests/
├── config.yaml
├── conftest.py
├── pytest.ini
├── pages/
│   └── example_page.py
└── tests/
    ├── test_api_example.py
    └── test_ui_example.py
```

## Step 3 — Configure your application

Open `config.yaml` and fill in your application details:

```yaml
base_url: http://localhost:8000   # your app URL

credentials:
  admin:
    username: your_admin_username
    password: your_admin_password

auth:
  type: cookie_jwt        # see docs/configuration.md for other types
  login_url: /auth/login
  username_field: username
  password_field: password
```

## Step 4 — Add data-testid attributes to your HTML

webtest-kit uses `data-testid` attributes to find elements reliably.
Add them to the key elements in your application:

```html
<!-- Login form -->
<input name="username" data-testid="input-username" />
<input name="password" data-testid="input-password" />
<button type="submit" data-testid="btn-submit">Login</button>

<!-- Error message -->
<div class="alert" data-testid="alert-error">{{ error }}</div>
```

This makes your tests independent of CSS classes and element text.

## Step 5 — Describe your pages

Copy `pages/example_page.py` and adapt it for your application:

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
```

## Step 6 — Write your first test

```python
# tests/test_login.py
import pytest
from pages.login_page import LoginPage

pytestmark = pytest.mark.e2e

class TestLogin:

    def test_login_success(self, anon_page, base_url):
        page = LoginPage(anon_page, base_url)
        page.login("your_username", "your_password")
        page.wait_for_url("/dashboard")

    def test_wrong_password(self, anon_page, base_url):
        page = LoginPage(anon_page, base_url)
        page.login("your_username", "wrong")
        page.expect_error("Invalid")

    def test_admin_sees_dashboard(self, admin_page, base_url):
        # admin_page is already authenticated — no login needed
        admin_page.goto(f"{base_url}/dashboard")
```

## Step 7 — Run tests

```bash
# All tests
webtest-kit run

# Only API tests (fast, no browser)
webtest-kit run --api-only

# Only UI tests with visible browser
webtest-kit run --e2e-only --headed

# Generate and open HTML report
webtest-kit run --html-report
webtest-kit report --type html
```

## Next steps

- [Configuration reference](configuration.md) — all config.yaml options
- [Writing tests](writing_tests.md) — Page Object patterns and best practices