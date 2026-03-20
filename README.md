# Amount API

API-сервис учёта личных финансов. Стек: **FastAPI**, **PostgreSQL**, **SQLAlchemy** (async), **Alembic**.

---

## Окружение и зависимости

### Создание виртуального окружения

```bash
python -m venv .amount
source .amount/bin/activate   # Linux/macOS
# .amount\Scripts\activate    # Windows
```

### Установка зависимостей

```bash
pip install fastapi "sqlalchemy[asyncio]" asyncpg uvicorn alembic
```

### Переменные окружения

| Переменная      | Описание                    | По умолчанию |
|-----------------|----------------------------|--------------|
| `DATABASE_URL`  | URL подключения к PostgreSQL (asyncpg) | `postgresql+asyncpg://postgres:postgres@localhost:5432/amount` |

Пример для `.env` или экспорта:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/amount"
```

---

## Запуск приложения

### Режим разработки (с автоперезагрузкой)

```bash
uvicorn main:app --reload
```

### Обычный запуск

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

После запуска: API — `http://localhost:8000`, документация — `http://localhost:8000/docs`.

---

## База данных

### Создание БД и пользователя (PostgreSQL)

```bash
psql -U postgres -c "CREATE ROLE amount WITH LOGIN PASSWORD 'amount';"
psql -U postgres -c "CREATE DATABASE amount OWNER amount;"
```

При использовании другого пользователя/пароля задайте их в `DATABASE_URL`.

### Инициализация таблиц (без миграций)

При старте приложения вызывается `init_db()`: создаются таблицы, если их ещё нет. Отдельная команда не нужна.

---

## Миграции (Alembic)

Миграции используют тот же `DATABASE_URL` (из окружения или `alembic.ini`).

### Применить все миграции

```bash
alembic upgrade head
```

### Откатить последнюю миграцию

```bash
alembic downgrade -1
```

### Откатить все миграции

```bash
alembic downgrade base
```

### Текущая ревизия в БД

```bash
alembic current
```

### История ревизий

```bash
alembic history
alembic history -v
```

### Создать новую миграцию (autogenerate по моделям)

```bash
alembic revision --autogenerate -m "описание изменений"
```

### Создать пустую миграцию (ручное описание)

```bash
alembic revision -m "описание изменений"
```

После создания отредактируйте файл в `migrations/versions/`.

---

## Полезные команды

| Действие | Команда |
|----------|---------|
| Проверка API | `curl http://localhost:8000/ping` |
| Запуск с другим портом | `uvicorn main:app --reload --port 9000` |
| Показать SQL миграций без применения | `alembic upgrade head --sql` |
| Помощь по Alembic | `alembic --help` |

---

## Структура проекта

```
amount-server/
├── main.py           # Точка входа FastAPI, эндпоинты
├── database.py       # Подключение к БД, engine, сессия, init_db
├── models.py         # Модели SQLAlchemy
├── alembic.ini       # Конфиг Alembic
└── migrations/       # Скрипты миграций
    ├── env.py        # Окружение миграций (async)
    └── versions/     # Файлы ревизий
```
