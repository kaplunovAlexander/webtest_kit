# webtest_kit/cli.py
"""
CLI точка входа. Три команды:
  webtest-kit init <name>   — создать структуру тестового проекта
  webtest-kit run           — запустить тесты
  webtest-kit report        — открыть Allure-отчёт
"""
import shutil
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree

console = Console()

# Путь к папке с шаблонами внутри пакета
TEMPLATES_DIR = Path(__file__).parent / "templates"


# ───────────────────────── корневая группа ─────────────────────────

@click.group()
@click.version_option(package_name="webtest-kit")
def main():
    """
    webtest-kit — automated functional testing framework for web applications.

    \b
    Quickstart:
        webtest-kit init my_tests
        cd my_tests
        # fill in config.yaml with your site URL and credentials
        webtest-kit run
        webtest-kit report
    """
    pass


# ───────────────────────── init ─────────────────────────

@main.command()
@click.argument("project_name")
@click.option(
    "--dir",
    "target_dir",
    default=".",
    help="Directory where project will be created (default: current dir)",
)
def init(project_name: str, target_dir: str):
    """
    Create a new test project scaffold.

    \b
    Example:
        webtest-kit init my_app_tests
        webtest-kit init my_app_tests --dir /home/user/projects
    """
    target = Path(target_dir) / project_name

    # Проверяем что папка не существует
    if target.exists():
        console.print(
            f"[red]Error:[/red] Directory '[bold]{target}[/bold]' already exists."
        )
        sys.exit(1)

    console.print(f"\n[bold]Initializing webtest-kit project:[/bold] {project_name}\n")

    try:
        _create_project_structure(target)
    except Exception as e:
        console.print(f"[red]Failed to create project:[/red] {e}")
        if target.exists():
            shutil.rmtree(target)
        sys.exit(1)

    _print_success(project_name, target)


def _create_project_structure(target: Path):
    """Копирует шаблоны и создаёт структуру проекта."""

    # Создаём папки
    dirs = [
        target,
        target / "pages",
        target / "tests",
        target / "reports",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green]created[/green] {d.name}/")

    # Копируем шаблоны → реальные файлы
    template_map = {
        # (шаблон относительно TEMPLATES_DIR) → (путь в проекте)
        "config.yaml.tpl":                   target / "config.yaml",
        "conftest.py.tpl":                   target / "conftest.py",
        "pages/example_page.py.tpl":         target / "pages" / "example_page.py",
        "pages/__init__.py.tpl":             target / "pages" / "__init__.py",
        "tests/test_api_example.py.tpl":     target / "tests" / "test_api_example.py",
        "tests/test_ui_example.py.tpl":      target / "tests" / "test_ui_example.py",
        "tests/__init__.py.tpl":             target / "tests" / "__init__.py",
        "pytest.ini.tpl":                    target / "pytest.ini",
        "gitignore.tpl":                     target / ".gitignore",
    }

    for tpl_name, dest_path in template_map.items():
        tpl_path = TEMPLATES_DIR / tpl_name
        if not tpl_path.exists():
            raise FileNotFoundError(f"Template not found: {tpl_path}")
        shutil.copy(tpl_path, dest_path)
        console.print(f"  [green]created[/green] {dest_path.relative_to(dest_path.parents[1])}")


def _print_success(project_name: str, target: Path):
    """Выводит итоговое сообщение с деревом проекта и инструкциями."""

    # Дерево структуры
    tree = Tree(f"[bold]{project_name}/[/bold]")
    tree.add("[yellow]config.yaml[/yellow]         ← fill in your URL and credentials")
    tree.add("conftest.py               ← ready to use, no changes needed")
    tree.add("pytest.ini                ← pytest configuration")
    pages = tree.add("pages/")
    pages.add("example_page.py         ← copy and adapt for your pages")
    tests = tree.add("tests/")
    tests.add("test_api_example.py     ← API test example")
    tests.add("test_ui_example.py      ← UI test example")
    tree.add("reports/                  ← test reports will appear here")

    console.print(Panel(tree, title="[green]✓ Project created[/green]", border_style="green"))

    # Инструкции
    console.print("\n[bold]Next steps:[/bold]\n")
    console.print(f"  1. [cyan]cd {target.name}[/cyan]")
    console.print("  2. Open [yellow]config.yaml[/yellow] and fill in your site URL and credentials")
    console.print("  3. Install Playwright browsers: [cyan]playwright install chromium[/cyan]")
    console.print("  4. Describe your pages in [yellow]pages/[/yellow] following the example")
    console.print("  5. Run your tests: [cyan]webtest-kit run[/cyan]")
    console.print("  6. View report:    [cyan]webtest-kit report[/cyan]\n")


# ───────────────────────── run ─────────────────────────

@main.command()
@click.option("--headed", is_flag=True, default=False, help="Run browser in headed mode")
@click.option("--slowmo", default=0, help="Slow down browser actions by N milliseconds")
@click.option("--api-only", is_flag=True, default=False, help="Run only API tests")
@click.option("--e2e-only", is_flag=True, default=False, help="Run only E2E tests")
@click.option("--html-report", is_flag=True, default=False, help="Generate HTML report")
@click.option("--allure", is_flag=True, default=False, help="Generate Allure report")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Verbose output")
@click.option("-k", "keyword", default=None, help="Run tests matching keyword")
def run(
    headed: bool,
    slowmo: int,
    api_only: bool,
    e2e_only: bool,
    html_report: bool,
    allure: bool,
    verbose: bool,
    keyword: str | None,
):
    """
    Run tests in current project directory.

    \b
    Examples:
        webtest-kit run
        webtest-kit run --headed
        webtest-kit run --headed --slowmo=500
        webtest-kit run --api-only
        webtest-kit run --e2e-only --headed
        webtest-kit run --allure
        webtest-kit run -k "test_login"
    """
    # Проверяем что мы в директории проекта
    if not Path("config.yaml").exists():
        console.print(
            "[red]Error:[/red] config.yaml not found. "
            "Are you in a webtest-kit project directory?"
        )
        sys.exit(1)

    # Строим команду pytest
    cmd = [sys.executable, "-m", "pytest"]

    # Маркеры
    if api_only:
        cmd += ["-m", "api"]
    elif e2e_only:
        cmd += ["-m", "e2e"]

    # Playwright опции
    if headed:
        cmd += ["--headed"]
    if slowmo:
        cmd += [f"--slowmo={slowmo}"]

    # Отчёты
    if html_report:
        cmd += ["--html=reports/report.html", "--self-contained-html"]
    if allure:
        cmd += ["--alluredir=reports/allure-results"]

    # Прочее
    if verbose:
        cmd += ["-v"]
    if keyword:
        cmd += ["-k", keyword]

    console.print(f"\n[bold]Running:[/bold] {' '.join(cmd)}\n")

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# ───────────────────────── report ─────────────────────────

@main.command()
@click.option(
    "--type",
    "report_type",
    type=click.Choice(["allure", "html"]),
    default="allure",
    help="Report type to open",
)
def report(report_type: str):
    """
    Open test report in browser.

    \b
    Examples:
        webtest-kit report
        webtest-kit report --type html
    """
    if report_type == "allure":
        results_dir = Path("reports/allure-results")
        if not results_dir.exists() or not any(results_dir.iterdir()):
            console.print(
                "[red]Error:[/red] No Allure results found. "
                "Run tests first with: [cyan]webtest-kit run --allure[/cyan]"
            )
            sys.exit(1)

        # Проверяем что allure CLI установлен
        import shutil
        if not shutil.which("allure"):
            console.print(
                "[red]Error:[/red] Allure CLI not found.\n\n"
                "Install it with one of:\n"
                "  [cyan]scoop install allure[/cyan]           (Windows, recommended)\n"
                "  [cyan]npm install -g allure-commandline[/cyan]\n"
                "  [cyan]brew install allure[/cyan]             (macOS)\n\n"
                "Or use HTML report instead:\n"
                "  [cyan]webtest-kit run --html-report[/cyan]\n"
                "  [cyan]webtest-kit report --type html[/cyan]"
            )
            sys.exit(1)

        console.print("\n[bold]Opening Allure report...[/bold]")
        subprocess.run(["allure", "serve", str(results_dir)])

    elif report_type == "html":
        report_file = Path("reports/report.html")
        if not report_file.exists():
            console.print(
                "[red]Error:[/red] No HTML report found. "
                "Run tests first with: [cyan]webtest-kit run --html-report[/cyan]"
            )
            sys.exit(1)

        import webbrowser
        console.print(f"\n[bold]Opening:[/bold] {report_file.resolve()}")
        webbrowser.open(f"file://{report_file.resolve()}")
