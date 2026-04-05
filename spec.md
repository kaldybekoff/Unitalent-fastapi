# Assignment 5 — UniTalent Spec

## 1. Middleware

### 1a. CORS & TrustedHostMiddleware

**File:** `src/main.py`

Both middlewares are registered via `app.add_middleware(...)`:

- `TrustedHostMiddleware` — rejects requests with unrecognised `Host` headers. Configured via `TRUSTED_HOSTS` env var (default `["*"]` — allow all in dev).
- `CORSMiddleware` — configured via `CORS_ORIGINS` env var (default `["*"]`). In production set to the actual frontend domain (e.g. `["https://app.unitalent.com"]`).

```python
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```

---

### 1b. Custom Logging Middleware

**File:** `src/middleware/logging.py`

Log format:
```
2026-04-05 12:00:00,000 | INFO    | 127.0.0.1:54321 - GET - /jobs - 200 - 12.34ms
2026-04-05 12:00:01,000 | WARNING | 127.0.0.1:54322 - POST - /auth/login - 401 - 5.10ms
2026-04-05 12:00:02,000 | ERROR   | 127.0.0.1:54323 - GET - /broken - 500 - 1.20ms
```

**Log levels:**
| HTTP Status | Log Level |
|---|---|
| 2xx / 3xx | INFO |
| 4xx | WARNING |
| 5xx | ERROR |

**Output:** Console + rotating file `logs/app.log` (max 10 MB, 5 backups).

**Implementation:**
- `BaseHTTPMiddleware` wraps every request
- `time.perf_counter()` measures processing time in milliseconds
- `request.client.host:port` identifies the caller

---

### 1c. Rate Limiting

**File:** `src/middleware/rate_limit.py`

Library: `fastapi-limiter` 0.2.0 + `pyrate-limiter` (in-memory, per-worker).

| Limit | Value | Applies to |
|---|---|---|
| Per IP / minute | 30 req | All endpoints (app-level `dependencies`) |
| Per IP / hour | 500 req | All endpoints (app-level `dependencies`) |
| Write per IP / hour | 50 req | POST / PATCH / DELETE only (per-route `Depends`) |
| GET requests | No write limit | Read-only operations are unrestricted |

**App-level (all requests):**
```python
app = FastAPI(dependencies=[
    Depends(rate_limit_per_minute()),   # 30/min
    Depends(rate_limit_per_hour()),     # 500/hr
])
```

**Per-route (writes only):**
```python
@router.post("/{candidate_id}/photo", dependencies=[Depends(write_rate_limit())])
```

**On limit exceeded:** HTTP `429 Too Many Requests` is returned automatically.

**How per-IP works:** `fastapi_limiter` uses the `default_identifier` which reads `X-Forwarded-For` first, falls back to `request.client.host`. Each IP has its own counter keyed as `ip:route_index:dep_index`.

---

### 1d. Profiling

**File:** `src/middleware/profiling.py`

Library: `pyinstrument` 5.x

**How to enable:**
```env
PROFILING_ENABLED=true
SLOW_ENDPOINT_THRESHOLD_MS=500
```

**What it tracks:**
- **Latency** — wall-clock time via `profiler.last_session.duration`
- **Call stack** — pyinstrument records the full call stack per request

**Output for slow endpoints** (latency > threshold):
```
WARNING | SLOW ENDPOINT GET /applications — 850ms
  File "src/applications/service.py", line 31
    list_applications  850ms
      session.exec     820ms   ← N+1 query chains
```

**Identified slow endpoints and reasons:**

| Endpoint | Typical Latency | Root Cause |
|---|---|---|
| `GET /applications` | 400–900ms | `selectin` on `candidate`, `job`, `resume`, `interviews` → 4 extra queries per application in list |
| `GET /candidates/{id}` | 200–400ms | Loads `user`, `applications[]`, `resumes[]` via selectin |
| `GET /interview-sessions/{id}` | 300–600ms | Loads `interviews[]` each with nested `application → candidate → user` |

**How to make them faster:**
- Use `joinedload` at the query level instead of model-level `lazy="selectin"` for list responses
- Return only needed fields (projection) instead of full ORM objects
- Add a Redis cache layer for frequently-read public endpoints (`GET /jobs`, `GET /companies`)

**When the profiler itself is overhead:**
- Set `PROFILING_ENABLED=false` in production (zero-cost passthrough — single `if` check)
- Or enable sampling: change `if random.random() > 1.0:` to `> 0.9` to profile only 10% of requests
- Use pyinstrument in sampling mode (`interval=0.01`) which adds ~0.5ms overhead per request instead of full instrumentation

---

## 2. Background Tasks (Celery)

**Broker & Backend:** Redis (`REDIS_URL`, same instance used for rate limiting and token blocklist)

**Start worker:**
```bash
celery -A src.celery_app worker --loglevel=info --pool=solo
```

**Monitor with Flower:**
```bash
celery -A src.celery_app flower --port=5555
```

---

### 2a. Email Confirmation & Password Reset

**Files:** `src/tasks/email_tasks.py`, `src/auth/tokens.py`, `src/auth/service.py`, `src/auth/router.py`

**Email library:** `fastapi-mail` + `aiosmtplib`
**Token library:** `python-jose` JWT (same key as auth tokens, different `type` claim)

#### Email Verification Flow

1. User registers → `POST /auth/register`
2. `register_user()` creates user with `is_verified=False`
3. `send_confirmation_email.delay(user_id, email, token)` fires in background
4. Celery worker sends email with link: `{FRONTEND_URL}/auth/verify-email/{token}` (token valid 24h)
5. User clicks link → `POST /auth/verify-email/{token}`
6. `verify_email()` decodes JWT, sets `user.is_verified=True`

**Resend:** `POST /auth/request-verification` (authenticated) re-sends the email.

#### Password Reset Flow

1. User calls `POST /auth/request-password-reset` with `{"email": "..."}`
2. If email exists: `send_password_reset_email.delay(...)` fires (token valid 1h)
3. If email not found: same 204 response (prevents email enumeration)
4. User clicks link → `POST /auth/reset-password/{token}` with `{"new_password": "..."}`
5. `reset_password()` decodes JWT, updates password hash, clears refresh token (invalidates all sessions)

**New endpoints:**
```
POST /auth/request-verification      → 204
POST /auth/verify-email/{token}      → UserRead
POST /auth/request-password-reset    → 204
POST /auth/reset-password/{token}    → UserRead
```

---

### 2b. Image Upload + Compression (stored as raw binary in PostgreSQL)

**Files:** `src/tasks/image_tasks.py`, `src/candidates/router.py`

**Storage:** PostgreSQL `BYTEA` column (`candidates.photo`)

**Endpoint:** `POST /candidates/{id}/photo`
- Auth required (own profile or admin)
- Accepts: `image/jpeg`, `image/png`
- Max size: 5 MB
- Returns **202 Accepted** immediately — processing happens in background

**Celery task `compress_and_store_photo`:**

1. Log original size in bytes and KB
2. Open with Pillow, convert to RGB, resize to max 800×800 (preserving aspect ratio)
3. Save as JPEG quality=75 with optimize=True
4. Log compressed size, ratio, and KB saved
5. Write compressed bytes directly to `candidates.photo` (BYTEA) via sync SQLAlchemy session

**Example log output:**
```
[photo] candidate=1 | original size: 2457600 bytes (2400.0 KB)
[photo] candidate=1 | compressed size: 148320 bytes (144.8 KB) — 6.0% of original, saved 2255.1 KB
[photo] candidate=1 | stored in PostgreSQL ✓
```

**Database column:** `candidates.photo BYTEA NULL`

**Why sync SQLAlchemy in the Celery task?**
Celery workers are synchronous. The web server uses `asyncpg` (async driver) which requires a running event loop. Inside a Celery task there is no event loop, so the database URL is converted from `postgresql+asyncpg://...` to `postgresql://...` and a regular sync `Session` is used.

**Why BYTEA and not a file path?**
Storing binary directly in PostgreSQL keeps the system self-contained — no external file server or object storage needed. The image is compressed from ~2–5 MB to ~100–200 KB before storage, so the size impact on the database is acceptable for a profile photo use case.

**`CandidateRead` response field:** `has_photo: bool` — derived from whether `photo` is non-null. Raw binary is never returned in JSON responses.

---

### 2c. Application Status Notification (Creative Task)

**File:** `src/applications/service.py`, `src/tasks/email_tasks.py`

**Idea:** When a recruiter changes an application status, the candidate automatically receives an email notification via Celery.

**Trigger:** Inside `patch_application()` — after successful database commit, if `status` changed:

```python
send_application_status_email.delay(
    candidate_email, candidate_name, job_title, company_name, new_status
)
```

**When it fires:** On any status transition: `submitted→reviewing`, `reviewing→accepted`, `reviewing→rejected`

**Email content:**
```
Subject: Application update: ACCEPTED — Backend Developer

Hi John Smith,

Your application for Backend Developer at TechCorp has been updated to:

ACCEPTED
```

**Why this is useful:** Candidates don't need to poll the API — they get real-time email updates when recruiters take action on their applications. The notification is fire-and-forget: if Celery is unavailable, the status update still succeeds.

---

## Database Changes (Alembic migrations)

| Migration | Changes |
|---|---|
| `b3e1f2a4c5d6` | Add `interview_sessions` table, restructure `interviews` table |
| `e1f2a3b4c5d6` | Add `users.is_verified BOOLEAN`, add `candidates.photo_url VARCHAR` |
| `f2a3b4c5d6e7` | Drop `candidates.photo_url`, add `candidates.photo BYTEA` |

```bash
alembic upgrade head
```
