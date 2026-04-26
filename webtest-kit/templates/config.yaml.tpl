# config.yaml — webtest-kit project configuration
# Documentation: https://github.com/yourusername/webtest-kit/docs/configuration.md

# ── Required ────────────────────────────────────────────────────────────────

# Base URL of the application under test
base_url: http://localhost:8000

# ── Credentials ─────────────────────────────────────────────────────────────
# Define one or more user roles.
# Each role becomes an authenticated fixture in your tests:
#   admin_page, admin_client, manager_page, manager_client, etc.

credentials:
  admin:
    username: admin
    password: changeme

  # Add more roles as needed:
  # manager:
  #   username: manager
  #   password: changeme
  #
  # user:
  #   username: regularuser
  #   password: changeme

# ── Authentication ───────────────────────────────────────────────────────────
# How the framework should log in to your application.
#
# type options:
#   cookie_jwt  — POST form to login_url, expects JWT cookie in response
#   session     — POST form to login_url, expects session cookie
#   basic       — HTTP Basic Auth (sent with every request)
#   bearer      — Bearer token in Authorization header

auth:
  type: cookie_jwt
  login_url: /auth/login
  logout_url: /auth/logout
  username_field: username    # name= attribute of the username input
  password_field: password    # name= attribute of the password input

# ── Browser ──────────────────────────────────────────────────────────────────

browser:
  name: chromium              # chromium | firefox | webkit
  headless: true              # false = show browser window
  slowmo: 0                   # ms delay between actions (useful for debugging)
  timeout: 8000               # ms to wait for elements
  viewport_width: 1280
  viewport_height: 720

# ── Reporting ─────────────────────────────────────────────────────────────────

report:
  output_dir: reports
  allure: false               # generate Allure report data
  html: false                 # generate pytest-html report
  screenshot_on_failure: true # capture screenshot when E2E test fails

# ── Database (optional) ───────────────────────────────────────────────────────
# Fill this section only if your tests need direct database access
# (e.g. for test data setup or teardown).

# database:
#   url: sqlite:///./test.db
#   reset_between_tests: false
