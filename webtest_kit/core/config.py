# webtest_kit/core/config.py
"""
Загрузка и валидация конфигурации из config.yaml.

Архитектурное решение:
- Pydantic-модели дают валидацию с понятными сообщениями об ошибках.
- Singleton-паттерн: конфиг загружается один раз, доступен отовсюду.
- Поддержка переменных окружения: значения из config.yaml можно
  переопределить через ENV (удобно для CI/CD).

Пример использования:
    from webtest_kit.core.config import get_config
    cfg = get_config()
    print(cfg.base_url)
    print(cfg.credentials["admin"].username)
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator, model_validator
from rich.console import Console

console = Console()


# ───────────────────────── Pydantic-модели ─────────────────────────

class CredentialConfig(BaseModel):
    """Учётные данные одной роли пользователя."""
    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Cannot be empty")
        return v


class AuthConfig(BaseModel):
    """
    Настройки авторизации.

    type:
      - cookie_jwt   — POST на login_url, получаем JWT в cookie (наш случай)
      - session      — стандартная сессионная авторизация
      - basic        — HTTP Basic Auth
      - bearer       — Bearer token в заголовке Authorization
    """
    type: str = "cookie_jwt"
    login_url: str = "/auth/login"
    logout_url: str = "/auth/logout"
    username_field: str = "username"   # name атрибут поля username в форме
    password_field: str = "password"   # name атрибут поля password в форме

    @field_validator("type")
    @classmethod
    def valid_auth_type(cls, v: str) -> str:
        allowed = {"cookie_jwt", "session", "basic", "bearer"}
        if v not in allowed:
            raise ValueError(f"auth.type must be one of: {', '.join(allowed)}")
        return v


class BrowserConfig(BaseModel):
    """Настройки браузера для E2E-тестов."""
    name: str = "chromium"
    headless: bool = True
    slowmo: int = 0              # задержка между действиями в мс
    timeout: int = 8000          # таймаут ожидания элементов в мс
    viewport_width: int = 1280
    viewport_height: int = 720

    @field_validator("name")
    @classmethod
    def valid_browser(cls, v: str) -> str:
        allowed = {"chromium", "firefox", "webkit"}
        if v not in allowed:
            raise ValueError(f"browser.name must be one of: {', '.join(allowed)}")
        return v

    @field_validator("slowmo", "timeout")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Must be >= 0")
        return v


class ReportConfig(BaseModel):
    """Настройки отчётности."""
    output_dir: str = "reports"
    allure: bool = False
    html: bool = False
    screenshot_on_failure: bool = True   # скриншот при падении E2E-теста


class DatabaseConfig(BaseModel):
    """
    Опциональные настройки тестовой БД.
    Если указаны — фреймворк может создавать изолированную тестовую БД.
    """
    url: Optional[str] = None            # например: sqlite:///./test.db
    reset_between_tests: bool = False     # пересоздавать БД перед каждым тестом


class WebtestKitConfig(BaseModel):
    """Корневая конфигурация проекта."""
    base_url: str
    auth: AuthConfig = AuthConfig()
    browser: BrowserConfig = BrowserConfig()
    report: ReportConfig = ReportConfig()
    database: DatabaseConfig = DatabaseConfig()
    credentials: dict[str, CredentialConfig] = {}

    @field_validator("base_url")
    @classmethod
    def valid_base_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "base_url must start with http:// or https://"
            )
        return v

    @model_validator(mode="after")
    def credentials_not_empty(self) -> "WebtestKitConfig":
        if not self.credentials:
            raise ValueError(
                "At least one entry under 'credentials' is required. "
                "Example:\n"
                "  credentials:\n"
                "    admin:\n"
                "      username: admin\n"
                "      password: secret"
            )
        return self


# ───────────────────────── загрузка конфига ─────────────────────────

def _find_config_file() -> Path:
    """
    Ищет config.yaml начиная с текущей директории вверх по дереву.
    Это позволяет запускать webtest-kit run из любой поддиректории проекта.
    """
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / "config.yaml"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "config.yaml not found. "
        "Make sure you are in a webtest-kit project directory, "
        "or run 'webtest-kit init <name>' to create a new project."
    )


def _apply_env_overrides(data: dict) -> dict:
    """
    Переопределяет значения из config.yaml переменными окружения.

    Правило именования ENV-переменных:
        WEBTEST_BASE_URL          → base_url
        WEBTEST_BROWSER_HEADLESS  → browser.headless
        WEBTEST_AUTH_TYPE         → auth.type

    Это позволяет использовать инструмент в CI без изменения config.yaml.
    """
    overrides = {
        "WEBTEST_BASE_URL":             ("base_url",),
        "WEBTEST_BROWSER_NAME":         ("browser", "name"),
        "WEBTEST_BROWSER_HEADLESS":     ("browser", "headless"),
        "WEBTEST_BROWSER_SLOWMO":       ("browser", "slowmo"),
        "WEBTEST_BROWSER_TIMEOUT":      ("browser", "timeout"),
        "WEBTEST_AUTH_TYPE":            ("auth", "type"),
        "WEBTEST_AUTH_LOGIN_URL":       ("auth", "login_url"),
        "WEBTEST_REPORT_ALLURE":        ("report", "allure"),
        "WEBTEST_REPORT_HTML":          ("report", "html"),
        "WEBTEST_DB_URL":               ("database", "url"),
    }

    for env_key, path in overrides.items():
        env_val = os.environ.get(env_key)
        if env_val is None:
            continue

        # Конвертируем строку в нужный тип
        converted = _convert_env_value(env_val)

        # Записываем по пути в словарь
        node = data
        for key in path[:-1]:
            node = node.setdefault(key, {})
        node[path[-1]] = converted

    return data


def _convert_env_value(value: str) -> bool | int | str:
    """Конвертирует строку из ENV в нужный Python-тип."""
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _load_raw_config(config_path: Path) -> dict:
    """Читает YAML-файл и возвращает словарь."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"config.yaml must be a YAML mapping, got: {type(data)}")

    return data


@lru_cache(maxsize=1)
def get_config(config_path: Optional[str] = None) -> WebtestKitConfig:
    """
    Загружает и возвращает конфигурацию. Кешируется через lru_cache —
    при повторных вызовах возвращает тот же объект без повторного чтения файла.

    Args:
        config_path: явный путь к config.yaml.
                     Если не указан — ищется автоматически.

    Returns:
        WebtestKitConfig — валидированный объект конфигурации.

    Raises:
        FileNotFoundError: если config.yaml не найден.
        ValueError: если конфиг содержит ошибки валидации.
    """
    if config_path:
        path = Path(config_path)
    elif env_path := os.environ.get("WEBTEST_CONFIG"):
        path = Path(env_path)
    else:
        path = _find_config_file()

    raw = _load_raw_config(path)
    raw = _apply_env_overrides(raw)

    try:
        config = WebtestKitConfig(**raw)
    except Exception as e:
        console.print(f"\n[red]Config validation error in {path}:[/red]\n")
        if hasattr(e, "errors"):
            for err in e.errors():
                location = " → ".join(str(l) for l in err["loc"])
                console.print(f"  [yellow]{location}:[/yellow] {err['msg']}")
        else:
            console.print(f"  {e}")
        console.print()
        raise SystemExit(1)

    return config


def reset_config():
    """
    Сбрасывает кеш конфига. Используется в тестах самого фреймворка,
    чтобы каждый тест мог загрузить свой config.yaml.
    """
    get_config.cache_clear()
