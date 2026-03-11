# Short URL Service

Сервис сокращения URL на FastAPI с архитектурой DDD (качестве реализации DDD, использовал Hexagonal Architecture с commands/handlers и т.д., так как основное время работал только с такой реализацией DDD). Добавил JWT авторизацию, через библиотеку `authx`.

Для написания `README.md` использовал LLM со следующим промптом:

```
Проанализируй весь проект и подготовь описание, обязательные пункты:

Описание API.
Примеры запросов.
Инструкцию по запуску.
Описание БД
```

## Возможности

- Создание коротких ссылок с опциональным пользовательским кодом
- Редирект на оригинальный URL
- Отслеживание статистики (количество кликов, дата последнего доступа)
- Поддержка срока действия ссылок
- Аутентификация пользователей с JWT токенами в HttpOnly cookies
- База данных PostgreSQL
- Кэширование Redis для высоконагруженных эндпоинтов
- Rate limiting для защиты от злоупотреблений

---

## Описание API

### Аутентификация

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/auth/register` | Регистрация нового пользователя | Нет |
| POST | `/auth/login` | Вход в систему | Нет |
| POST | `/auth/refresh` | Обновление токенов | Нет (refresh token в cookie) |
| POST | `/auth/logout` | Выход из системы | Нет |

### Короткие ссылки

| Метод | Эндпоинт | Описание | Авторизация |
|-------|----------|----------|-------------|
| POST | `/links/shorten` | Создать короткую ссылку | Опционально |
| GET | `/links/{short_code}` | Редирект на оригинальный URL | Нет |
| GET | `/links/{short_code}/stats` | Получить статистику ссылки | Требуется |
| PUT | `/links/{short_code}` | Обновить ссылку | Требуется (владелец) |
| DELETE | `/links/{short_code}` | Удалить ссылку | Требуется (владелец) |
| GET | `/links/search?original_url={url}` | Найти по оригинальному URL | Нет |
| GET | `/links/expired` | Список истёкших ссылок | Нет |
| POST | `/links/cleanup` | Очистка истёкших ссылок | Требуется |

### Health Check

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/health` | Проверка состояния сервиса |

---

## Примеры запросов

### Регистрация пользователя

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

> Токены автоматически устанавливаются в HttpOnly cookies.

### Вход в систему

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Создание короткой ссылки (без авторизации)

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/very/long/url/that/needs/shortening"
  }'
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "short_code": "abc123",
  "original_url": "https://example.com/very/long/url/that/needs/shortening",
  "short_url": "http://localhost:8000/links/abc123",
  "access_count": 0,
  "expires_at": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Создание ссылки с пользовательским кодом и сроком действия

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/promo",
    "custom_alias": "promo2025",
    "expires_at": "2025-12-31T23:59:00Z"
  }'
```

### Создание ссылки от авторизованного пользователя

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H "Content-Type: application/json" \
  -b "access_token=eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "url": "https://example.com/my-link"
  }'
```

### Редирект по короткому коду

```bash
curl -L http://localhost:8000/links/abc123
```

> Возвращает HTTP 307 с редиректом на оригинальный URL.

### Получение статистики ссылки (требуется авторизация)

```bash
curl http://localhost:8000/links/abc123/stats \
  -b "access_token=eyJhbGciOiJIUzI1NiIs..."
```

**Ответ:**
```json
{
  "original_url": "https://example.com/very/long/url",
  "created_at": "2025-01-15T10:30:00Z",
  "access_count": 42,
  "last_accessed_at": "2025-01-16T14:22:00Z"
}
```

### Обновление ссылки (только владелец)

```bash
curl -X PUT http://localhost:8000/links/abc123 \
  -H "Content-Type: application/json" \
  -b "access_token=eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "url": "https://example.com/new-url"
  }'
```

### Удаление ссылки (только владелец)

```bash
curl -X DELETE http://localhost:8000/links/abc123 \
  -b "access_token=eyJhbGciOiJIUzI1NiIs..."
```

### Поиск по оригинальному URL

```bash
curl "http://localhost:8000/links/search?original_url=https://example.com/long-url"
```

### Очистка истёкших ссылок (требуется авторизация)

```bash
curl -X POST http://localhost:8000/links/cleanup \
  -b "access_token=eyJhbGciOiJIUzI1NiIs..."
```

**Ответ:**
```json
{
  "deleted_count": 15
}
```

### Выход из системы

```bash
curl -X POST http://localhost:8000/auth/logout
```

---

## Инструкция по запуску

### Быстрый старт с Docker

**Требования:**
- Docker & Docker Compose

**Запуск:**

1. Скопируйте файл окружения:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` и установите `JWT_SECRET`:
   ```bash
   # Обязательно измените JWT_SECRET на надёжное значение!
   JWT_SECRET=your-super-secret-key-change-me
   ```

3. Запустите все сервисы:
   ```bash
   docker compose up -d
   ```

4. Проверьте доступность:
   - API: http://localhost:8000
   - Swagger UI (только в debug режиме): http://localhost:8000/docs
   - ReDoc (только в debug режиме): http://localhost:8000/redoc

**Остановка сервисов:**

```bash
docker compose down
```

Для удаления томов (данных базы):
```bash
docker compose down -v
```

### Локальная разработка

**Требования:**
- Python 3.13+
- uv (менеджер пакетов)
- PostgreSQL 16+
- Redis 7+

**Установка:**

1. Установите зависимости:
   ```bash
   uv sync
   ```

2. Создайте базу данных PostgreSQL:
   ```sql
   CREATE DATABASE shorturl_db;
   CREATE USER shorturl WITH PASSWORD 'shorturl_secret';
   GRANT ALL PRIVILEGES ON DATABASE shorturl_db TO shorturl;
   ```

3. Скопируйте и настройте `.env`:
   ```bash
   cp .env.example .env
   ```
   
   Для локальной разработки измените:
   ```bash
   DATABASE_URL=postgresql+asyncpg://shorturl:shorturl_secret@localhost:5432/shorturl_db
   REDIS_HOST=localhost
   REDIS_URL=redis://localhost:6379/0
   DEBUG=true
   ```

4. Примените миграции:
   ```bash
   uv run alembic upgrade head
   ```

5. Запустите приложение:
   ```bash
   uv run uvicorn main:app --reload
   ```

`Swagger` доступен по ссылке: `http://localhost:8000/docs`

---

## Описание базы данных

### Таблица `users`

Хранит данные пользователей.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Первичный ключ |
| `email` | VARCHAR(255) | Email пользователя (уникальный) |
| `password_hash` | VARCHAR(255) | Хеш пароля (Argon2) |
| `is_active` | BOOLEAN | Активен ли аккаунт |
| `created_at` | TIMESTAMP | Дата создания |
| `updated_at` | TIMESTAMP | Дата обновления |

**Индексы:**
- `ix_users_id` — индекс по ID
- `ix_users_email` — уникальный индекс по email

### Таблица `short_urls`

Хранит короткие ссылки.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | UUID | Первичный ключ |
| `original_url` | VARCHAR(2048) | Оригинальный URL |
| `short_code` | VARCHAR(10) | Короткий код (уникальный) |
| `owner_id` | UUID | ID владельца (FK → users.id, может быть NULL) |
| `access_count` | INTEGER | Количество переходов |
| `expires_at` | TIMESTAMP | Дата истечения (NULL = бессрочно) |
| `deleted_at` | TIMESTAMP | Дата удаления (soft delete) |
| `deleted_reason` | VARCHAR(32) | Причина удаления (`user`, `expired`) |
| `created_at` | TIMESTAMP | Дата создания |
| `updated_at` | TIMESTAMP | Дата обновления |

**Индексы:**
- `ix_short_urls_id` — индекс по ID
- `ix_short_urls_short_code` — уникальный индекс по короткому коду
- `ix_short_urls_deleted_at` — индекс для фильтрации удалённых записей

**Связи:**
- `owner_id` → `users.id` (CASCADE DELETE)

---

## Архитектура проекта

```
src/
├── domain/              # Доменный слой
│   ├── entities/        # Сущности (User, ShortUrl)
│   ├── repositories/    # Интерфейсы репозиториев
│   └── services/        # Доменные сервисы (генератор кодов)
├── application/         # Прикладной слой
│   ├── commands/        # Команды (CQRS)
│   ├── handlers/        # Обработчики команд
│   └── dto/             # Data Transfer Objects
├── infrastructure/      # Инфраструктурный слой
│   ├── auth/            # JWT сервис, хеширование паролей
│   ├── persistence/     # Реализации репозиториев, модели SQLAlchemy
│   ├── config.py        # Конфигурация (pydantic-settings)
│   ├── database.py      # Подключение к БД
│   ├── cache.py         # Redis клиент
│   ├── cache_service.py # Сервис кэширования
│   └── rate_limit.py    # Rate limiting (slowapi)
└── presentation/        # Слой представления
    └── api/
        ├── routes/      # REST эндпоинты
        └── schemas/     # Pydantic схемы валидации
```

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATABASE_URL` | — | URL подключения к PostgreSQL (обязательно) |
| `POSTGRES_USER` | shorturl | Имя пользователя БД |
| `POSTGRES_PASSWORD` | shorturl_secret | Пароль БД |
| `POSTGRES_DB` | shorturl_db | Имя базы данных |
| `REDIS_HOST` | redis | Хост Redis |
| `REDIS_PORT` | 6379 | Порт Redis |
| `REDIS_URL` | redis://redis:6379/0 | URL подключения к Redis |
| `JWT_SECRET` | — | Секретный ключ JWT (**обязательно**) |
| `JWT_ALGORITHM` | HS256 | Алгоритм подписи JWT |
| `JWT_EXPIRATION` | 3600 | Время жизни access токена (секунды) |
| `DEBUG` | false | Режим отладки (включает Swagger UI) |
| `SHORT_CODE_LENGTH` | 6 | Длина генерируемого короткого кода |
| `SHORT_URL_BASE` | http://localhost:8000 | Базовый URL для коротких ссылок |
| `CORS_ALLOW_ORIGINS` | http://localhost:8000 | Разрешённые origins (через запятую) |
| `CORS_ALLOW_CREDENTIALS` | false | Разрешить credentials для CORS |
| `COOKIE_SECURE` | false | Флаг Secure для cookies |
| `COOKIE_HTTPONLY` | true | Флаг HttpOnly для cookies |
| `COOKIE_SAMESITE` | lax | Политика SameSite для cookies |

---

## Кэширование

Сервис использует Redis для кэширования:

| Данные | TTL | Ключ |
|--------|-----|------|
| Данные короткой ссылки | 10 минут | `short_url:{short_code}` |
| Статистика ссылки | 1 минута | `stats:{short_code}` |

**Инвалидация кэша:**
- При обновлении ссылки
- При удалении ссылки
- При истечении срока действия

---

## Rate Limiting

Защита от злоупотреблений:

| Эндпоинт | Лимит |
|----------|-------|
| `POST /auth/register` | 5 запросов в минуту |
| `POST /auth/login` | 10 запросов в минуту |
| `POST /links/shorten` | 20 запросов в минуту |

---

## Безопасность

- **HttpOnly cookies** — защита от XSS атак на токены
- **CSRF защита** — SameSite=lax для cookies
- **Rate limiting** — защита от брутфорса и флуда
- **Валидация URL** — блокировка `javascript:`, `data:` схем и приватных IP
- **Надёжное хеширование паролей** — Argon2
- **Генерация коротких кодов** — `secrets` вместо `random`

---

## Лицензия

См. файл [LICENSE](LICENSE).
