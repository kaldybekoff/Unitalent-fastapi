# Assignment 5 — Defense Preparation Guide

---

## Quick Summary (say this first if asked "what did you do?")

> "For Assignment 5 I added four middleware layers — CORS, custom logging, rate limiting, and profiling — and three Celery background tasks: email verification with password reset, image upload with Pillow compression stored as raw binary in PostgreSQL, and automatic email notifications when a recruiter changes an application status."

---

## Part 1 — Middleware

---

### 1a. CORS and TrustedHostMiddleware

**What it is:**
- CORS (Cross-Origin Resource Sharing) — controls which domains can call your API from a browser.
- TrustedHostMiddleware — rejects requests with a fake or unknown `Host` header (protects against Host header injection attacks).

**What I did:**
Added both as Starlette middleware in `src/main.py`. Configured via environment variables so values can be changed without code changes.

```python
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
```

**How the order works:**
Middleware is applied in reverse order of `add_middleware` calls. So `TrustedHostMiddleware` is outermost (runs first on incoming requests), then CORS, then Logging, then Profiling (innermost, closest to the actual handler).

**Expected question: "Why do you need CORS?"**
> "Without CORS, a browser running on `localhost:3000` cannot call an API on `localhost:8000` due to the same-origin policy. CORS headers tell the browser which origins are allowed. On the backend, the middleware adds these headers to every response automatically."

**Expected question: "What happens if the Host header is wrong?"**
> "TrustedHostMiddleware returns `400 Bad Request` before the request even reaches the router. This prevents Host header injection attacks where an attacker tricks the app into generating URLs with a forged domain."

---

### 1b. Custom Logging Middleware

**File:** `src/middleware/logging.py`

**What it does:**
Every HTTP request is logged with this format:
```
2026-04-05 12:00:01 | INFO    | 127.0.0.1:52341 - GET - /jobs - 200 - 12.34ms
2026-04-05 12:00:02 | WARNING | 127.0.0.1:52342 - POST - /auth/login - 401 - 5.10ms
2026-04-05 12:00:03 | ERROR   | 127.0.0.1:52343 - GET - /crash - 500 - 1.20ms
```

**How I built it:**
- Extended Starlette's `BaseHTTPMiddleware`
- In the `dispatch` method: record `time.perf_counter()` before calling `await call_next(request)`, then again after
- The difference gives processing time in milliseconds
- Log level is chosen based on HTTP status code: 2xx/3xx → INFO, 4xx → WARNING, 5xx → ERROR

**Where logs go:**
- Console (stdout) — visible in the terminal
- Rotating file `logs/app.log` — max 10 MB, 5 backup files

**Expected question: "Why BaseHTTPMiddleware and not a simple decorator?"**
> "BaseHTTPMiddleware integrates with FastAPI's ASGI lifecycle and runs for every request including ones that hit 404 or raise exceptions. A route decorator would only work on routes I explicitly decorate."

**Expected question: "Why three log levels and not just one?"**
> "Different log levels allow filtering. In production you can set the logger to WARNING and only see errors and 4xx without drowning in INFO noise. In development you keep INFO to see every request."

---

### 1c. Rate Limiting

**File:** `src/middleware/rate_limit.py`

**Library:** `fastapi-limiter` 0.2.0 with `pyrate-limiter` as the backend (in-memory per worker).

**Three tiers:**

| Tier | Limit | How applied |
|---|---|---|
| Global per IP/minute | 30 requests | `FastAPI(dependencies=[...])` — all routes |
| Global per IP/hour | 500 requests | `FastAPI(dependencies=[...])` — all routes |
| Write per IP/hour | 50 requests | `Depends(write_rate_limit())` on each POST/PATCH/DELETE route |

**Why GET is not write-limited:**
> "Read operations (GET) are idempotent and cheap. Write operations (POST/PATCH/DELETE) change data, can trigger background tasks, send emails, and write to the database. These have higher cost so they deserve a separate, stricter limit."

**How per-IP identification works:**
The `default_identifier` from `fastapi-limiter` reads the `X-Forwarded-For` header first (for clients behind a proxy/load balancer), then falls back to `request.client.host`. Each IP gets its own counter.

**What happens when the limit is exceeded:**
`HTTP 429 Too Many Requests` is returned automatically by the `RateLimiter` dependency.

**Expected question: "What is the difference between per-minute and per-hour limits?"**
> "The per-minute limit (30 req/min) prevents burst attacks — someone hammering the API 200 times in 10 seconds gets blocked. The per-hour limit (500 req/hr) prevents sustained abuse — someone slowly sending 1000 requests over an hour also gets blocked. Both limits run together."

**Expected question: "Why not use Redis for rate limiting?"**
> "For this assignment the in-memory limiter is sufficient. In a multi-instance production setup you'd use Redis so all instances share the same counters. The project already has Redis wired in, so migrating would only require changing the backend parameter."

---

### 1d. Profiling

**File:** `src/middleware/profiling.py`

**Library:** `pyinstrument` 5.x

**What it tracks:**
1. **Latency** — total wall-clock time per request in milliseconds
2. **Call stack** — which functions were called and how long each took

**How to enable:**
```env
PROFILING_ENABLED=true
SLOW_ENDPOINT_THRESHOLD_MS=500
```

**How it works:**
```python
profiler = Profiler(async_mode="enabled")
profiler.start()
response = await call_next(request)
profiler.stop()
elapsed_ms = profiler.last_session.duration * 1000
if elapsed_ms > settings.slow_endpoint_threshold_ms:
    logger.warning("SLOW ENDPOINT %s %s — %.0fms\n%s", ...)
```

**Identified slow endpoints:**

| Endpoint | Why it's slow | How to fix |
|---|---|---|
| `GET /applications` | `lazy="selectin"` on 4 relationships (`candidate`, `job`, `resume`, `interviews`) — fires 4+ extra queries per row | Use `joinedload` at the query level, or paginate aggressively |
| `GET /candidates/{id}` | Loads `user`, `applications[]`, `resumes[]` via selectin | Load only needed fields for the response schema |
| `GET /interview-sessions/{id}` | Each `Interview` in the list loads `application → candidate → user` chain | Eager-join the full chain in one query |

**Expected question: "What to do when the profiler itself is too slow?"**
> "Two options. First, completely disable it with `PROFILING_ENABLED=false` in production — the middleware becomes a zero-cost passthrough with a single `if` check. Second, use sampling: instead of profiling every request, profile only 10% by adding `if random.random() < 0.1:` around the profiler block. This reduces overhead by 10x while still giving you data on slow endpoints over time."

**Expected question: "What is call stack profiling?"**
> "Instead of just measuring how long a function took in total, call stack profiling shows you which specific lines inside the function consumed the time. For example: `list_applications` took 850ms, of which 820ms was in `session.exec()`. This tells you immediately that the bottleneck is the database query, not the Python logic."

---

## Part 2 — Background Tasks

---

### Setup

**Broker:** Redis (same instance already used for token blocklist and rate limiting)

**Worker start command:**
```bash
celery -A src.celery_app worker --loglevel=info --pool=solo
```

**Monitor:**
```bash
celery -A src.celery_app flower --port=5555
# Open http://localhost:5555
```

**Why Celery and not FastAPI's built-in `BackgroundTasks`?**
> "FastAPI's `BackgroundTasks` runs in the same process as the web server. If the task takes 5 seconds (email sending, image compression), the worker thread is occupied. Celery runs tasks in completely separate worker processes, so the web server always responds immediately. Also, Celery has retries, monitoring with Flower, and can scale to many workers."

---

### 2a. Email Confirmation and Password Reset

**Files:** `src/auth/tokens.py`, `src/auth/service.py`, `src/auth/router.py`, `src/tasks/email_tasks.py`

**Email library:** `fastapi-mail`
**Token mechanism:** JWT (same secret key as auth tokens, but with different `type` claim)

#### Email Verification

**Flow:**
1. User registers → `POST /auth/register`
2. User is created with `is_verified=False`
3. `send_confirmation_email.delay(user_id, email, token)` — queued in Redis, picked up by Celery worker
4. Worker sends email with link: `{FRONTEND_URL}/auth/verify-email/{JWT_TOKEN}` (valid 24 hours)
5. User clicks link → `POST /auth/verify-email/{token}`
6. Server decodes JWT, checks `type == "email_verify"`, sets `user.is_verified = True`

**Token structure:**
```json
{ "sub": "42", "type": "email_verify", "exp": 1743940800 }
```

**New endpoints:**
```
POST /auth/request-verification     → 204 (resend verification email)
POST /auth/verify-email/{token}     → UserRead
```

#### Password Reset

**Flow:**
1. `POST /auth/request-password-reset` with `{"email": "user@example.com"}`
2. If user exists: generate reset token (valid 1 hour), fire Celery task
3. If user NOT found: **still return 204** — prevents email enumeration attacks
4. Celery sends email with: `{FRONTEND_URL}/auth/reset-password/{token}`
5. `POST /auth/reset-password/{token}` with `{"new_password": "newpass123"}`
6. Token decoded, password hashed, `refresh_token` set to `null` (all sessions invalidated)

**New endpoints:**
```
POST /auth/request-password-reset   → 204
POST /auth/reset-password/{token}   → UserRead
```

**Expected question: "Why invalidate refresh token after password reset?"**
> "If someone's account was compromised and they reset the password, the attacker may already have a valid refresh token. By setting `refresh_token = null`, all existing sessions are immediately invalidated everywhere."

**Expected question: "Why return 204 even when email is not found?"**
> "This is called preventing email enumeration. If we returned 404 for unknown emails, an attacker could send thousands of reset requests and learn which emails are registered in our system. Always returning 204 gives nothing away."

**Expected question: "What happens if Celery is down during registration?"**
> "Registration still succeeds. The email task is wrapped in a `try/except` — if Celery is unavailable, the exception is silently caught and the user is created normally. They can re-request verification via `POST /auth/request-verification` once Celery is back."

---

### 2b. Image Upload + Compression → stored as raw binary in PostgreSQL

**Files:** `src/candidates/router.py`, `src/tasks/image_tasks.py`

**Endpoint:** `POST /candidates/{id}/photo`
**Library:** `Pillow` for compression
**Storage:** PostgreSQL `BYTEA` column (`candidates.photo`)

#### Upload Flow

1. `POST /candidates/{id}/photo` with `multipart/form-data`
2. Server validates: only `image/jpeg` or `image/png`, max 5 MB, must be own profile
3. Raw bytes read: `raw = await file.read()`
4. Task queued: `compress_and_store_photo.delay(candidate_id, raw)`
5. Server immediately returns **202 Accepted** — the client does not wait

**Celery task `compress_and_store_photo` steps:**
```
1. Log original size:   "[photo] candidate=1 | original size: 2457600 bytes (2400.0 KB)"
2. PIL.open() → convert to RGB → thumbnail(800x800, LANCZOS)
3. Save as JPEG quality=75, optimize=True to BytesIO buffer
4. Log compressed size: "[photo] candidate=1 | compressed size: 148320 bytes (144.8 KB) — 6.0%, saved 2255.1 KB"
5. Write raw binary to candidates.photo (BYTEA) via sync SQLAlchemy session
6. Log: "[photo] candidate=1 | stored in PostgreSQL ✓"
```

**Example log output:**
```
[photo] candidate=1 | original size: 2457600 bytes (2400.0 KB)
[photo] candidate=1 | compressed size: 148320 bytes (144.8 KB) — 6.0% of original, saved 2255.1 KB
[photo] candidate=1 | stored in PostgreSQL ✓
```

**`CandidateRead` response:** `has_photo: bool` — `true` if photo exists, raw bytes never returned in JSON.

**Expected question: "Why sync SQLAlchemy in the Celery task?"**
> "Celery workers are synchronous by default. The web server uses `asyncpg` (async driver), but that requires a running event loop. Inside a Celery task there is no event loop, so I replace `+asyncpg` in the database URL and use a regular synchronous `Session`."

**Expected question: "Why store in PostgreSQL as BYTEA and not on disk?"**
> "Storing on disk breaks in multi-server deployments — each server has its own filesystem. PostgreSQL BYTEA keeps everything in one place, benefits from database backups, and requires no extra infrastructure. The image is compressed from ~2–5 MB to ~100–200 KB before storage, so the database size impact is acceptable for a profile photo."

**Expected question: "Why return 202 Accepted instead of 200?"**
> "202 means 'I received your request and it will be processed, but it's not done yet.' The compression and storage happen asynchronously in Celery. The client gets an immediate response and `has_photo` will become `true` once the task completes."

**Expected question: "What compression settings did you use?"**
> "Resize to maximum 800×800 pixels while preserving aspect ratio using `Image.thumbnail`, then save as JPEG with quality=75 and `optimize=True`. This typically reduces a 2–5 MB photo to under 200 KB — over 90% compression — while keeping the image visually acceptable for a profile photo."

---

### 2c. Application Status Notification (Creative Task)

**File:** `src/applications/service.py`, `src/tasks/email_tasks.py`

**Idea:** When a recruiter changes an application status, the candidate receives an automatic email.

**Where it triggers:**
Inside `patch_application()` in the applications service, after a successful database commit:

```python
if "status" in data and data["status"] != application.status:
    send_application_status_email.delay(
        application.candidate.user.email,
        application.candidate.full_name,
        application.job.title,
        application.job.company.name,
        application.status,
    )
```

**Status transitions that trigger the email:**
- `submitted → reviewing` → candidate notified their application is being reviewed
- `reviewing → accepted` → candidate notified they were accepted
- `reviewing → rejected` → candidate notified they were rejected

**Why this is a good creative task:**
> "Without this, candidates have to manually refresh the application list to check their status. This is a real-world requirement in every job platform. The notification is asynchronous — if email sending fails, the status update still succeeds and Celery retries the email up to 3 times."

---

## Database Changes

| Migration | What changed |
|---|---|
| `b3e1f2a4c5d6` | Add `interview_sessions` table, restructure `interviews` |
| `e1f2a3b4c5d6` | Add `users.is_verified BOOLEAN`, add `candidates.photo_url VARCHAR` |
| `f2a3b4c5d6e7` | Drop `candidates.photo_url`, add `candidates.photo BYTEA` |

---

## New Files Summary

| File | Purpose |
|---|---|
| `src/middleware/logging.py` | Custom access log middleware |
| `src/middleware/rate_limit.py` | Rate limiter instances and write limit dependency |
| `src/middleware/profiling.py` | pyinstrument call-stack profiling middleware |
| `src/celery_app.py` | Celery application with Redis broker |
| `src/email/config.py` | FastMail configuration |
| `src/email/templates/*.html` | Email HTML templates (3 files) |
| `src/tasks/email_tasks.py` | 3 Celery tasks: verify, reset, notify |
| `src/tasks/image_tasks.py` | Celery task: compress + store as BYTEA in PostgreSQL |
| `src/auth/tokens.py` | JWT token creation/decoding for email flows |
| `spec.md` | Assignment specification document |

---

## Common Questions & Answers

**Q: What is middleware?**
> "Middleware is a layer that wraps every incoming request and outgoing response. It runs before the route handler and after it. In FastAPI/Starlette, middleware is implemented as ASGI middleware — it receives the request, can modify it, calls the next layer, and can modify the response."

**Q: What is the order of your middleware?**
> "TrustedHost (outermost) → CORS → Logging → Profiling (innermost). Starlette processes middleware in reverse order of `add_middleware` calls, so the last one added is the first to execute."

**Q: What is Celery?**
> "Celery is a distributed task queue. You define tasks as Python functions decorated with `@celery_app.task`. When you call `task.delay(args)`, instead of executing immediately, the task is serialized to JSON and sent to a message broker — in our case Redis. A separate Celery worker process picks it up and executes it. The web server returns a response immediately without waiting."

**Q: What is the difference between `delay()` and `apply_async()`?**
> "`delay()` is shorthand for `apply_async()` with no extra options. They both queue the task. `apply_async()` lets you pass `countdown` (delay before execution), `eta` (absolute time), `retry_policy`, and other options."

**Q: Why store the image as BYTEA in PostgreSQL?**
> "It keeps the system self-contained — no external file server or object storage needed. The image is compressed from ~2–5 MB to ~100–200 KB before storage, so the impact on the database is minimal. For a profile photo this is a perfectly valid approach."

**Q: Why not return the image bytes in the API response?**
> "Returning raw binary in a JSON response would require base64 encoding which adds ~33% size overhead. Instead, `CandidateRead` returns `has_photo: bool`. To actually serve the image you would add a dedicated `GET /candidates/{id}/photo` endpoint that returns the bytes with a proper `image/jpeg` content type."

**Q: How do you prevent duplicate application submissions?**
> "The `applications` table has a database-level `UNIQUE(candidate_id, job_id)` constraint. If a candidate tries to apply twice, SQLAlchemy raises an `IntegrityError` which is caught and returned as a `409 Conflict` response."

**Q: What happens if Celery retries fail?**
> "After the maximum retries (3 attempts with 30-second delays for image tasks, 60-second delays for email tasks), the task is marked as FAILURE. You can see this in the Flower dashboard at `http://localhost:5555`. The web request itself already succeeded — only the background processing failed."

---

## Checklist Before Defense

- [ ] Redis is running (confirmed: Python ping returns True)
- [ ] App starts without errors: `uvicorn src.main:app --reload`
- [ ] Celery worker is running: `celery -A src.celery_app worker --pool=solo --loglevel=info`
- [ ] `.env` has `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER` set
- [ ] Alembic migrations applied: `alembic upgrade head`
- [ ] Can demo: `POST /auth/register` → see Celery log: `send_confirmation_email received`
- [ ] Can demo: `POST /candidates/{id}/photo` → see compression log in Celery terminal
- [ ] Can demo: `PATCH /applications/{id}` with new status → see `send_application_status_email` in Celery log
- [ ] Can show `logs/app.log` with formatted request logs
- [ ] Can show rate limit 429 by sending >30 requests in 1 minute
