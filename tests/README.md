# Тесты API

Интеграционные тесты HTTP-роутов: отдельное приложение FastAPI, изолированная БД в памяти, без поднятого PostgreSQL и без вызова `init_db()` из `main.py`. В `conftest.py` подключены роутеры **category** и **auth** (тесты авторизации — `test_auth_routes.py`).

**Коллекция категорий** в API: `GET` / `POST` на **`/category`** без завершающего слэша. Раньше путь был `/category/`; при запросе фронта на `/category` Starlette отвечал **307** редиректом на URL со слэшем, что ломало часть клиентов (особенно при CORS или `fetch` без следования редиректам). Сейчас базовый путь совпадает с типичным URL фронта.

## Как запустить

Из корня репозитория:

```bash
# один раз: зависимости для разработки (pytest, pytest-asyncio, aiosqlite)
pip install -r requirements-dev.txt

# все тесты
pytest

# подробный вывод
pytest -v

# только файл с тестами категорий
pytest tests/test_category_routes.py -v

# один тест по имени
pytest tests/test_category_routes.py::test_create_category -v
```

Активируйте виртуальное окружение проекта (например `.amount/bin/activate`), если оно используется.

## Где что лежит

| Файл / каталог | Назначение |
|----------------|------------|
| [`requirements-dev.txt`](../requirements-dev.txt) | Зависимости **только для разработки**: раннер тестов, asyncio-плагин, драйвер SQLite для async. В продакшен-сборку обычно не входят. |
| [`pytest.ini`](../pytest.ini) | Настройки pytest для всего проекта (см. ниже). |
| [`tests/conftest.py`](conftest.py) | Общие фикстуры: движок БД, приложение, HTTP-клиент, тестовые данные. |
| [`tests/test_category_routes.py`](test_category_routes.py) | Сценарии для `/category` и `/category/{id}`. |

## Настройка `pytest.ini`

| Опция | Зачем |
|-------|--------|
| `pythonpath = .` | Корень проекта в `sys.path`, чтобы работали импорты вроде `import models` без установки пакета через `pip install -e .`. |
| `asyncio_mode = auto` | Асинхронные тесты (`async def test_...`) выполняются через pytest-asyncio без ручной разметки каждого теста. |
| `asyncio_default_fixture_loop_scope = function` | У каждого теста свой event loop и своя жизнь асинхронных фикстур — изоляция между тестами. |
| `testpaths = tests` | По умолчанию собираются только тесты из каталога `tests/`. |
| `filterwarnings` для `SAWarning` | SQLAlchemy предупреждает о пересечениях relationship’ов при первом обращении к моделям; на результат тестов это не влияет, шум в логе отключается. |

## Настройка `tests/conftest.py`

| Фикстура | Что делает |
|----------|------------|
| **`engine`** | Создаёт async-движок **SQLite в памяти** с `StaticPool`, чтобы все соединения видели одну и ту же базу. Выполняет `create_all` по `Base.metadata` (нужны все модели — поэтому в начале файла `import models`). После теста движок закрывается. |
| **`session_factory`** | `async_sessionmaker` для сессий, привязанных к этому движку. |
| **`app`** | Минимальное `FastAPI()` с роутерами **auth** и **category**. **`get_db`** подменяется через `dependency_overrides`: вместо боевого `AsyncSessionLocal` из `database.py` в запросы попадает сессия от тестового движка. Так тесты не трогают реальный `DATABASE_URL` и не требуют Postgres. |
| **`client`** | Асинхронный **HTTPX** `AsyncClient` с **ASGITransport** — запросы идут в приложение в памяти, без сети и без отдельного процесса uvicorn. |
| **`workspace_id`** | Создаёт в БД строку `Workspace` и возвращает `id`. Нужна для **FK** при создании категории (`workspace_id` обязателен в модели). |

Тесты, которым нужен воркспейс, объявляют параметр `workspace_id`; остальным достаточно `client`.

## Зависимости из `requirements-dev.txt`

| Пакет | Роль |
|-------|------|
| **pytest** | Запуск и отчёт тестов. |
| **pytest-asyncio** | Поддержка `async def` тестов и асинхронных фикстур. |
| **aiosqlite** | Драйвер SQLite для SQLAlchemy async (`sqlite+aiosqlite://`). |

Основной код приложения уже тянет **httpx** (часто как зависимость FastAPI/Starlette) — клиент в тестах использует его.

## Что именно проверяют тесты

Файл `test_category_routes.py` покрывает сценарии для роутов категорий: создание, список (в том числе с фильтром `type`), получение по id, 404, частичное обновление (PATCH), удаление (DELETE) и снова 404 после удаления.

При добавлении новых роутеров можно завести отдельный файл `tests/test_<name>_routes.py` и при необходимости расширить `conftest.py` общими фикстурами.
