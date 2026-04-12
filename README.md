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
pip install -r requirements.txt
```

(Для тестов: `pip install -r requirements-dev.txt`.)

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | URL подключения к PostgreSQL (asyncpg) | `postgresql+asyncpg://postgres:postgres@localhost:5432/amount` |
| `JWT_SECRET` | Секрет подписи JWT; в продакшене — длинная случайная строка | значение для разработки в коде |
| `JWT_ALGORITHM` | Алгоритм JWT | `HS256` |
| `JWT_EXPIRE_MINUTES` | Время жизни токена (минуты) | `10080` (7 суток) |
| `AUTH_COOKIE_NAME` | Имя httpOnly-cookie с токеном | `access_token` |
| `AUTH_COOKIE_SECURE` | Отдавать cookie только по HTTPS | `false` |
| `AUTH_COOKIE_SAMESITE` | `lax` / `strict` / `none` | `lax` |

Параметры JWT и cookie читаются из окружения и при наличии `.env` в каталоге сервера.

Пример для `.env` или экспорта:

```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/amount"
export JWT_SECRET="замените-на-длинную-случайную-строку"
```

---

## Авторизация

Регистрация и вход по **email** и **паролю**; подтверждение почты не используется.

- Email приводится к виду `trim` + нижний регистр, в БД уникален.
- Пароль хранится как **bcrypt**-хеш.
- После **`POST /auth/register`** или **`POST /auth/login`** клиент получает **httpOnly** cookie с JWT.
- **`GET /auth/me`** — текущий пользователь (нужна cookie).
- **`POST /auth/logout`** — сброс cookie (`204`).
- После **регистрации** у пользователя всегда есть **хотя бы один workspace**; при **входе** для «старых» пользователей без workspace он создаётся автоматически.

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/auth/register` | JSON: `email`, `password` (мин. 8 символов), опционально `name`. Ответ `201` + cookie. Занятый email — `409`. Создаётся **первый workspace** (`{name} — workspace`) и связь в `workspace_users`. |
| `POST` | `/auth/login` | JSON: `email`, `password`. Ошибка — `401`. Если у пользователя ещё нет workspace (старые данные), создаётся такой же дефолтный workspace. |
| `POST` | `/auth/logout` | `204`, cookie удаляется. |
| `GET` | `/auth/me` | Профиль (`id`, `name`, `email`) без пароля; без сессии — `401`. |

Эндпоинты **`/category`** и **`/operation`** требуют той же cookie с JWT. Поле **`user_id` в теле запросов не используется** — автор записи берётся из сессии. Доступ только к workspace, где пользователь состоит в `workspace_users` (чужой workspace — `403` при создании категории; операции и категории из чужого workspace — ответ `404`).

### Операции (`/operation`)

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/operation` | JSON: `workspace_id`, `category_id`, `title`, `amount` (целое; дробное округляется), опционально `created` (дата/время). Категория должна принадлежать этому workspace. `201` + объект операции. |
| `GET` | `/operation` | Query: **`workspace_id`** (обязательно); опционально `category_id`, `user_id`, `date_from`, `date_to`, `limit`, `offset`. Ответ: `{ "items": [...], "total": N }`, сортировка по `created` убыв. |
| `GET` | `/operation/{id}` | Одна операция; нет доступа к workspace — `404`. |
| `PATCH` | `/operation/{id}` | Частичное обновление: `category_id`, `title`, `amount`, `created` (все опциональны; при смене категории она должна быть в том же workspace, что и операция). |
| `DELETE` | `/operation/{id}` | `204`. |

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
├── auth/             # JWT, cookie, роуты /auth/*
├── category/         # Категории
├── user/             # Модель пользователя
├── workspace/        # Рабочие пространства
├── operation/        # Операции
├── models/           # Сборка моделей для Alembic / init_db
├── alembic.ini       # Конфиг Alembic
└── migrations/       # Скрипты миграций
    ├── env.py        # Окружение миграций (async)
    └── versions/     # Файлы ревизий
```
