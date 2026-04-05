# UniTalent — Полный анализ проекта

## 1. Обзор проекта

**UniTalent Recruitment API** — RESTful backend-сервис на FastAPI для платформы найма, ориентированной на студентов и выпускников университетов. Система соединяет кандидатов с работодателями, предоставляя ролевую модель доступа для кандидатов, рекрутеров и администраторов.

**Цели:**
- Кандидаты: регистрация, профиль, резюме, отклик на вакансии
- Рекрутеры: управление компаниями, публикация вакансий, обработка откликов, назначение интервью
- Администраторы: полный доступ ко всем данным и операциям

---

## 2. Стек технологий

| Компонент         | Технология                   | Версия     |
|-------------------|------------------------------|------------|
| Framework         | FastAPI                      | 0.115.6    |
| Web Server        | Uvicorn                      | 0.34.0     |
| ORM               | SQLModel                     | 0.0.22     |
| Database          | PostgreSQL (Neon, облако)     | AsyncPG 0.30.0 |
| Async Support     | AsyncSession, aiosqlite      | —          |
| Authentication    | JWT, python-jose[cryptography]| —          |
| Password Hashing  | passlib[bcrypt]              | —          |
| Caching           | Redis                        | 4.6.0      |
| Migrations        | Alembic                      | latest     |
| Configuration     | Pydantic Settings            | 2.7.1      |
| Validation        | Pydantic, email-validator    | 2.2.0      |

---

## 3. Структура проекта

```
UniTalent/
├── src/
│   ├── main.py                          # Инициализация FastAPI приложения
│   ├── config.py                        # Настройки и переменные окружения
│   ├── db/
│   │   └── session.py                   # Управление сессиями БД
│   ├── cache/
│   │   └── client.py                    # Инициализация Redis клиента
│   ├── exceptions/
│   │   ├── custom_exceptions.py         # Кастомные классы исключений
│   │   └── handlers.py                  # Обработчики исключений
│   ├── auth/
│   │   ├── router.py                    # Эндпоинты аутентификации
│   │   ├── service.py                   # Бизнес-логика аутентификации
│   │   ├── schemas.py                   # Схемы запросов/ответов
│   │   ├── dependencies.py              # OAuth2 и ролевая аутентификация
│   │   └── utils.py                     # Генерация токенов, хэширование паролей
│   ├── users/
│   │   └── models.py                    # Модель пользователя
│   ├── candidates/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dependencies.py
│   ├── companies/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dependencies.py
│   ├── jobs/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dependencies.py
│   ├── resumes/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dependencies.py
│   ├── applications/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── router.py
│   │   ├── service.py
│   │   └── dependencies.py
│   └── interviews/
│       ├── models.py
│       ├── schemas.py
│       ├── router.py
│       ├── service.py
│       └── dependencies.py
├── alembic/
│   ├── env.py
│   └── versions/
│       └── d6d79cb46f27_initial_schema.py
├── assets/
│   └── erd.txt
├── .env
├── alembic.ini
├── requirements.txt
├── plan.md
└── .gitignore
```

---

## 4. Схема базы данных (7 сущностей)

### 4.1 User — пользователи и аккаунты

```
Таблица: users
- id             INTEGER, PK
- email          STRING, unique, indexed
- hashed_password STRING
- role           STRING, indexed  → "candidate" | "recruiter" | "admin"
- is_active      BOOLEAN, indexed, default=true
- refresh_token  STRING, nullable  (хранится для инвалидации при logout)
- created_at     DATETIME
- updated_at     DATETIME

Связи:
- 0..1 Candidate profile (one_to_one)
- N Companies (one_to_many)
```

### 4.2 Candidate — профили кандидатов

```
Таблица: candidates
- id          INTEGER, PK
- user_id     FK → users.id, unique, indexed
- full_name   STRING
- major       STRING, nullable
- year        INTEGER, nullable  (диапазон 1–8)
- created_at  DATETIME
- updated_at  DATETIME

Связи:
- 1 User
- N Resumes
- N Applications
```

### 4.3 Company — компании работодателей

```
Таблица: companies
- id         INTEGER, PK
- owner_id   FK → users.id, indexed
- name       STRING, unique, indexed
- industry   STRING, nullable
- website    STRING, nullable
- created_at DATETIME
- updated_at DATETIME

Связи:
- 1 User (owner)
- N Jobs
```

### 4.4 Job — вакансии

```
Таблица: jobs
- id          INTEGER, PK
- title       STRING, indexed
- location    STRING, nullable, indexed
- description STRING  (max 5000 chars)
- is_open     BOOLEAN, indexed, default=true
- company_id  FK → companies.id, indexed
- created_at  DATETIME
- updated_at  DATETIME

Связи:
- 1 Company
- N Applications
```

### 4.5 Resume — резюме

```
Таблица: resumes
- id           INTEGER, PK
- candidate_id FK → candidates.id, indexed
- title        STRING
- summary      STRING, nullable  (max 3000 chars)
- skills       STRING, nullable  (max 3000 chars)
- education    STRING, nullable  (max 3000 chars)
- experience   STRING, nullable  (max 3000 chars)
- is_active    BOOLEAN, indexed, default=true
- created_at   DATETIME
- updated_at   DATETIME

Связи:
- 1 Candidate
- N Applications
```

### 4.6 Application — отклики на вакансии

```
Таблица: applications
- id           INTEGER, PK
- candidate_id FK → candidates.id, indexed
- job_id       FK → jobs.id, indexed
- resume_id    FK → resumes.id, indexed
- status       STRING, indexed  → "submitted" | "reviewing" | "accepted" | "rejected"
- cover_letter STRING, nullable  (max 5000 chars)
- created_at   DATETIME
- updated_at   DATETIME

Ограничения:
- UNIQUE(candidate_id, job_id)  — один кандидат не может подать 2 отклика на одну вакансию

Связи:
- 1 Candidate
- 1 Job
- 1 Resume
- N Interviews
```

### 4.7 Interview — интервью

```
Таблица: interviews
- id             INTEGER, PK
- application_id FK → applications.id, indexed
- scheduled_at   DATETIME
- mode           STRING  → "online" | "offline"
- location       STRING, nullable  (обязателен если mode='offline')
- meeting_link   STRING, nullable  (обязателен если mode='online')
- result         STRING, nullable
- notes          STRING, nullable  (max 2000 chars)
- created_at     DATETIME
- updated_at     DATETIME

Связи:
- 1 Application
```

---

## 5. API Эндпоинты

### 5.1 Аутентификация (`/auth`)

| Метод | Путь              | Описание                                  | Доступ    |
|-------|-------------------|-------------------------------------------|-----------|
| POST  | /auth/register    | Регистрация нового пользователя           | Публичный |
| POST  | /auth/login       | Вход (возвращает access + refresh токены) | Публичный |
| POST  | /auth/refresh     | Обновление access токена                  | Публичный |
| POST  | /auth/logout      | Выход (инвалидация токена)                | Авториз.  |
| GET   | /auth/me          | Текущий пользователь                      | Авториз.  |

### 5.2 Кандидаты (`/candidates`)

| Метод  | Путь                                  | Описание                              | Доступ                |
|--------|---------------------------------------|---------------------------------------|-----------------------|
| GET    | /candidates                           | Список кандидатов                     | Admin/Recruiter       |
| GET    | /candidates/{id}                      | Данные кандидата                      | Публичный             |
| POST   | /candidates                           | Создать профиль                       | Авториз. (candidate)  |
| PATCH  | /candidates/{id}                      | Обновить свой профиль                 | Владелец/Admin        |
| DELETE | /candidates/{id}                      | Удалить свой профиль                  | Владелец/Admin        |
| GET    | /candidates/{id}/applications         | Отклики кандидата                     | Владелец/Admin        |

### 5.3 Компании (`/companies`)

| Метод  | Путь                      | Описание                              | Доступ                        |
|--------|---------------------------|---------------------------------------|-------------------------------|
| GET    | /companies                | Список компаний                       | Публичный                     |
| GET    | /companies/{id}           | Данные компании                       | Публичный                     |
| POST   | /companies                | Создать компанию                      | Recruiter/Admin               |
| PATCH  | /companies/{id}           | Обновить компанию                     | Владелец/Admin                |
| DELETE | /companies/{id}           | Удалить компанию (если нет вакансий)  | Владелец/Admin                |
| GET    | /companies/{id}/jobs      | Вакансии компании                     | Публичный                     |

### 5.4 Вакансии (`/jobs`)

| Метод  | Путь                       | Описание                                | Доступ                |
|--------|----------------------------|-----------------------------------------|-----------------------|
| GET    | /jobs                      | Список вакансий                         | Публичный             |
| GET    | /jobs/{id}                 | Данные вакансии                         | Публичный             |
| POST   | /jobs                      | Создать вакансию                        | Recruiter/Admin       |
| PATCH  | /jobs/{id}                 | Обновить вакансию                       | Владелец/Admin        |
| DELETE | /jobs/{id}                 | Удалить (если нет откликов)             | Владелец/Admin        |
| GET    | /jobs/{id}/applications    | Отклики на вакансию                     | Recruiter/Admin       |

### 5.5 Резюме (`/resumes`)

| Метод  | Путь              | Описание                                | Доступ                |
|--------|-------------------|-----------------------------------------|-----------------------|
| GET    | /resumes          | Список резюме                           | Публичный             |
| GET    | /resumes/{id}     | Данные резюме                           | Публичный             |
| POST   | /resumes          | Создать резюме                          | Candidate только      |
| PATCH  | /resumes/{id}     | Обновить своё резюме                    | Владелец/Admin        |
| DELETE | /resumes/{id}     | Удалить (если не используется)          | Владелец/Admin        |

### 5.6 Отклики (`/applications`)

| Метод  | Путь                              | Описание                              | Доступ                |
|--------|-----------------------------------|---------------------------------------|-----------------------|
| GET    | /applications                     | Список откликов                       | Candidate (только своих), Recruiter/Admin |
| GET    | /applications/{id}                | Данные отклика                        | Владелец/Recruiter/Admin |
| POST   | /applications                     | Создать отклик                        | Candidate             |
| PATCH  | /applications/{id}                | Обновить (статус или cover letter)    | Recruiter/Admin (статус), Candidate (cover_letter) |
| DELETE | /applications/{id}                | Удалить (если нет интервью)           | Владелец/Admin        |
| GET    | /applications/{id}/interviews     | Интервью по отклику                   | Recruiter/Admin/Candidate |

### 5.7 Интервью (`/interviews`)

| Метод  | Путь                  | Описание              | Доступ        |
|--------|-----------------------|-----------------------|---------------|
| GET    | /interviews           | Список интервью       | Recruiter/Admin |
| GET    | /interviews/{id}      | Данные интервью       | Recruiter/Admin/Candidate |
| POST   | /interviews           | Создать интервью      | Recruiter/Admin |
| PATCH  | /interviews/{id}      | Обновить интервью     | Recruiter/Admin |
| DELETE | /interviews/{id}      | Удалить интервью      | Recruiter/Admin |

### 5.8 Корневой эндпоинт

| Метод | Путь | Описание       |
|-------|------|----------------|
| GET   | /    | Health check   |

---

## 6. Аутентификация и авторизация

### 6.1 Механизм аутентификации

- **JWT-токены**: access + refresh
- **Access Token TTL**: 30 минут (настраивается через `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Refresh Token TTL**: 7 дней (настраивается через `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Алгоритм**: HS256

**Структура токена:**
```json
{
  "sub": "user_id",
  "role": "candidate|recruiter|admin",
  "type": "access|refresh",
  "exp": "<timestamp>"
}
```

### 6.2 Управление токенами

- При refresh — генерируется новая пара токенов
- При logout — access токен добавляется в Redis blocklist с TTL до истечения
- Refresh токен хранится в поле `User.refresh_token` для валидации

### 6.3 Ролевая модель доступа (RBAC)

**Candidate:**
- Создаёт и управляет своим профилем, резюме
- Откликается на открытые вакансии своим резюме
- Видит только свои отклики
- Может обновлять только `cover_letter` в своих откликах
- Не может менять статус отклика
- Не имеет доступа к списку кандидатов

**Recruiter:**
- Создаёт и управляет своими компаниями
- Создаёт вакансии только для своих компаний
- Видит отклики только на свои вакансии
- Меняет статус откликов на свои вакансии
- Создаёт и управляет интервью для своих вакансий
- Видит список кандидатов

**Admin:**
- Полный доступ без ограничений по владению
- Обходит все проверки ролей и владения

### 6.4 Публичный доступ (без аутентификации)

```
GET /
GET /companies
GET /companies/{id}
GET /companies/{id}/jobs
GET /jobs
GET /jobs/{id}
GET /candidates/{id}
GET /resumes
GET /resumes/{id}
POST /auth/register
POST /auth/login
POST /auth/refresh
```

---

## 7. Бизнес-логика и валидация

### 7.1 Пользователи

- Email должен быть уникальным (409 Conflict при дубликате)
- Минимальная длина пароля — 6 символов
- Роль: `candidate`, `recruiter`, `admin`
- Неактивный пользователь не может войти

### 7.2 Кандидаты

- Один пользователь — один профиль кандидата (409 при повторном создании)
- Нельзя удалить профиль, если есть резюме или отклики (400)

### 7.3 Компании

- Название компании уникально (409 при дубликате)
- Нельзя удалить компанию с вакансиями (400)

### 7.4 Вакансии

- Рекрутер не может создать вакансию для чужой компании (403)
- Нельзя удалить вакансию с откликами (400)

### 7.5 Резюме

- Только кандидаты могут создавать резюме
- Нельзя создать без профиля кандидата (400)
- Нельзя удалить резюме, используемое в отклике (400)

### 7.6 Отклики

- Только кандидат может подавать отклики
- Нельзя подать отклик на закрытую вакансию (400)
- Нельзя подать 2 отклика на одну вакансию (400)
- Нельзя использовать чужое резюме (403)
- Кандидат не может менять статус отклика (403)

**Переходы статусов:**
```
submitted  → reviewing | rejected
reviewing  → accepted  | rejected
accepted   → (финальный)
rejected   → (финальный)
```
Недопустимый переход → 400 Bad Request.

### 7.7 Интервью

- Нельзя создать интервью для отклонённого отклика (400)
- Если `mode='online'` → обязателен `meeting_link`
- Если `mode='offline'` → обязателен `location`
- Рекрутер управляет только интервью своих вакансий (403)
- Нельзя удалить отклик с интервью (400)

---

## 8. Обработка ошибок

**Кастомные исключения (`src/exceptions/custom_exceptions.py`):**

| Класс                | HTTP код | Назначение                              |
|----------------------|----------|-----------------------------------------|
| `AppException`       | —        | Базовый класс                           |
| `NotFoundException`  | 404      | Ресурс не найден                        |
| `ConflictException`  | 409      | Конфликт (дубликат, нарушение ограничения) |
| `BadRequestException`| 400      | Некорректный запрос / нарушение логики  |
| `UnauthorizedException` | 401   | Ошибка аутентификации                   |
| `ForbiddenException` | 403      | Ошибка авторизации                      |

Все исключения зарегистрированы в `src/exceptions/handlers.py` и возвращают JSON с соответствующим HTTP статусом.

---

## 9. Конфигурация

### Переменные окружения (`.env`)

```
DATABASE_URL=postgresql+asyncpg://user:password@host/database?ssl=require
DB_ECHO=false
SECRET_KEY=super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379/0
```

**Класс Settings** (`src/config.py`) использует Pydantic Settings с поддержкой `.env` файла. Все поля валидируются при старте приложения.

---

## 10. Redis

**Назначение:** blocklist для инвалидации access токенов при logout.

**Клиент** (`src/cache/client.py`):
- `decode_responses=True`
- `socket_connect_timeout=3`
- `socket_timeout=3`

**Ключ:** `blocklist:{access_token}`
**TTL:** рассчитывается из времени истечения токена

**Graceful degradation:** ошибки Redis перехватываются и не прерывают работу приложения.

---

## 11. Миграции базы данных

**Инструмент:** Alembic  
**Конфиг:** `alembic.ini`, `alembic/env.py`  
**Асинхронные миграции:** `async_engine_from_config`

**Начальная миграция:** `d6d79cb46f27_initial_schema.py` (создана 2026-03-16)

**Порядок создания таблиц (upgrade):**
1. `users`
2. `candidates` (FK → users)
3. `companies` (FK → users)
4. `jobs` (FK → companies)
5. `resumes` (FK → candidates)
6. `applications` (FK → candidates, jobs, resumes)
7. `interviews` (FK → applications)

---

## 12. Паттерны и архитектурные решения

### 12.1 Async/Await

Все операции с БД, сервисы и роутеры — асинхронные.

### 12.2 Service Layer Pattern

Каждый модуль содержит:
- `models.py` — SQLModel модели
- `schemas.py` — Pydantic схемы запросов/ответов
- `service.py` — бизнес-логика
- `router.py` — API эндпоинты
- `dependencies.py` — dependency injection

### 12.3 Dependency Injection

Каждый модуль имеет функции извлечения и валидации path-параметров:
- `candidate_by_id` — валидирует `candidate_id > 0`
- `company_by_id` — валидирует `company_id > 0`
- `job_by_id` — валидирует `job_id > 0`
- `resume_by_id` — валидирует `resume_id > 0`
- `application_by_id` — валидирует `app_id > 0`
- `interview_by_id` — валидирует `interview_id > 0`

**Auth dependencies:**
- `get_current_user` — извлекает и валидирует JWT
- `require_roles(*roles)` — фабрика ролевых проверок

### 12.4 Eager Loading (Selectin)

Все связи используют `sa_relationship_kwargs={"lazy": "selectin"}` для предотвращения N+1 запросов.

### 12.5 Ownership-Based Authorization

- Рекрутеры управляют только своими компаниями и вакансиями
- Кандидаты управляют только своими профилями, резюме и откликами
- Администраторы обходят все ограничения по владению

---

## 13. Типичные сценарии использования

### Подача отклика на вакансию (кандидат)

1. `POST /auth/register` с `role="candidate"`
2. `POST /candidates` — создание профиля
3. `POST /resumes` — создание резюме
4. `POST /applications` с `job_id` и `resume_id`
5. Система проверяет: вакансия открыта, резюме принадлежит кандидату, нет дубликата
6. Отклик создаётся со статусом `submitted`
7. Рекрутер меняет статус: `PATCH /applications/{id}` → `reviewing`
8. Рекрутер назначает интервью: `POST /interviews`
9. Итог: `reviewing` → `accepted` или `rejected`

### Публикация вакансии (рекрутер)

1. `POST /auth/register` с `role="recruiter"`
2. `POST /companies` — создание компании
3. `POST /jobs` с `company_id` — создание вакансии
4. Система проверяет: рекрутер является владельцем компании
5. Вакансия создаётся с `is_open=true`
6. Кандидаты видят вакансию в `GET /jobs` и могут откликаться

---

## 14. Git история

**Последние коммиты:**
```
9d41050  .
810f5d2  updated plam.md
5a0ea6a  Changed plan.md and added new erd png photo
eb143c1  changed redis version
c13144b  migration table order and remove sqlmodel dependency for upgrade head
115853f  added 2 entities and migration
9fb7234  job's service changed
8448434  minimal changes
f133626  just
ee94d8d  deleted unneeded photo
```

**Текущее состояние (незакоммиченные изменения):**
```
M  src/auth/dependencies.py   (изменён)
 M src/auth/service.py        (изменён)
 D src/db/init_db.py          (удалён)
 D src/redis/client.py        (удалён)
?? src/auth/__init__.py       (новый)
?? src/cache/                 (новая директория)
?? src/users/__init__.py      (новый)
```

**Ветка:** `main`

---

## 15. Деплой и окружение

- **База данных:** Neon PostgreSQL (облако, EU Central 1)
- **Подключение:** SSL обязателен (`?ssl=require`)
- **Connection pool:** pre-ping включён (проверка соединения перед использованием)
- **Redis:** локальный (`redis://localhost:6379/0`) или облачный
- **SQL логирование:** отключено (`DB_ECHO=false`)
