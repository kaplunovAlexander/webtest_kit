[pytest]
# webtest-kit project — pytest configuration

# Directories with tests
testpaths = tests

# Markers — use to run subsets of tests
# webtest-kit run --api-only    → runs only tests marked with @pytest.mark.api
# webtest-kit run --e2e-only    → runs only tests marked with @pytest.mark.e2e
markers =
    api: API tests via httpx (fast, no browser)
    e2e: UI tests via Playwright (slower, requires browser)
    slow: tests that take more than 10 seconds

# Show local variables in tracebacks
# Remove if output becomes too noisy
log_cli = false
