# webtest-kit

A framework for automated functional testing of web applications using Python, pytest and Playwright.

## Installation

```bash
pip install webtest-kit
playwright install chromium
```

## Quickstart

```bash
# Create a new test project
webtest-kit init my_app_tests
cd my_app_tests

# Fill in your site URL and credentials
nano config.yaml

# Run tests
webtest-kit run

# View Allure report
webtest-kit run --allure
webtest-kit report
```

## Commands

| Command | Description |
|---|---|
| `webtest-kit init <name>` | Create new test project |
| `webtest-kit run` | Run all tests |
| `webtest-kit run --headed` | Run with visible browser |
| `webtest-kit run --api-only` | Run only API tests |
| `webtest-kit run --e2e-only` | Run only UI tests |
| `webtest-kit run --allure` | Run and generate Allure report |
| `webtest-kit report` | Open Allure report |
| `webtest-kit report --type html` | Open HTML report |

## Demo

See `demo/` folder for a complete example with TaskFlow application.
