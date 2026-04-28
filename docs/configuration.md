# Configuration Reference

All webtest-kit settings live in `config.yaml` in your project root.

## Full example

```yaml
base_url: http://localhost:8000

credentials:
  admin:
    username: admin
    password: secret123
  manager:
    username: manager
    password: secret456
  user:
    username: regularuser
    password: pass789

auth:
  type: cookie_jwt
  login_url: /auth/login
  logout_url: /auth/logout
  username_field: username
  password_field: password

browser:
  name: chromium
  headless: true
  slowmo: 0
  timeout: 8000
  viewport_width: 1280
  viewport_height: 720

report:
  output_dir: reports
  allure: false
  html: false
  screenshot_on_failure: true

database:
  url: sqlite:///./test.db
  reset_between_tests: false
```

## Settings reference

### `base_url` (required)

Base URL of the application under test.

```yaml
base_url: http://localhost:8000
```

Must start with `http://` or `https://`. Trailing slash is removed automatically.

---

### `credentials` (required)

One or more user roles. Each role generates a pair of fixtures automatically:
`{role}_page` and `{role}_client`.

```yaml
credentials:
  admin:
    username: admin
    password: secret
  user:
    username: regular
    password: pass
```

---

### `auth`

How webtest-kit logs in to your application.

| Field | Default | Description |
|---|---|---|
| `type` | `cookie_jwt` | Auth type: `cookie_jwt`, `session`, `basic`, `bearer` |
| `login_url` | `/auth/login` | URL of the login endpoint |
| `logout_url` | `/auth/logout` | URL of the logout endpoint |
| `username_field` | `username` | `name` attribute of the username input |
| `password_field` | `password` | `name` attribute of the password input |

**Auth types:**

- `cookie_jwt` — POST form to `login_url`, expects JWT in cookie response
- `session` — POST form to `login_url`, expects session cookie
- `basic` — HTTP Basic Auth sent with every request
- `bearer` — Bearer token in `Authorization` header

---

### `browser`

| Field | Default | Description |
|---|---|---|
| `name` | `chromium` | Browser: `chromium`, `firefox`, `webkit` |
| `headless` | `true` | Run without visible window |
| `slowmo` | `0` | Delay between actions in milliseconds |
| `timeout` | `8000` | Element wait timeout in milliseconds |
| `viewport_width` | `1280` | Browser viewport width |
| `viewport_height` | `720` | Browser viewport height |

---

### `report`

| Field | Default | Description |
|---|---|---|
| `output_dir` | `reports` | Directory for report files |
| `allure` | `false` | Generate Allure report data |
| `html` | `false` | Generate pytest-html report |
| `screenshot_on_failure` | `true` | Save screenshot when E2E test fails |

---

### `database` (optional)

Only needed if your tests require direct database access.

| Field | Default | Description |
|---|---|---|
| `url` | `null` | SQLAlchemy database URL |
| `reset_between_tests` | `false` | Drop and recreate DB before each test |

---

## Environment variable overrides

Any setting can be overridden via environment variable without editing `config.yaml`.
Useful for CI/CD pipelines.

| Variable | Config field |
|---|---|
| `WEBTEST_BASE_URL` | `base_url` |
| `WEBTEST_BROWSER_NAME` | `browser.name` |
| `WEBTEST_BROWSER_HEADLESS` | `browser.headless` |
| `WEBTEST_BROWSER_SLOWMO` | `browser.slowmo` |
| `WEBTEST_BROWSER_TIMEOUT` | `browser.timeout` |
| `WEBTEST_AUTH_TYPE` | `auth.type` |
| `WEBTEST_AUTH_LOGIN_URL` | `auth.login_url` |
| `WEBTEST_REPORT_ALLURE` | `report.allure` |
| `WEBTEST_REPORT_HTML` | `report.html` |
| `WEBTEST_DB_URL` | `database.url` |

Example for CI:

```bash
export WEBTEST_BASE_URL=https://staging.myapp.com
export WEBTEST_BROWSER_HEADLESS=true
webtest-kit run --allure
```