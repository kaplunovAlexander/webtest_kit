# conftest.py
"""
Корневой conftest.py вашего тестового проекта.

Подключает все фикстуры webtest-kit. После этого в ваших тестах
автоматически доступны фикстуры для каждой роли из config.yaml:

    Если в config.yaml есть роли admin, manager, user — доступны:
    - admin_page, manager_page, user_page     (браузерные страницы)
    - admin_client, manager_client, user_client  (API-клиенты)
    - anon_page, anon_client                  (без авторизации)
    - base_url                                (из config.yaml)

Не изменяй этот файл без необходимости.
Для своих фикстур создай conftest.py в папке tests/.
"""

# Подключаем все универсальные фикстуры webtest-kit
pytest_plugins = ["webtest_kit.core.fixtures"]
