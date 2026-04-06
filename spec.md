# Assignment 5 — UniTalent

## 1. Middleware

### 1a. CORS & TrustedHostMiddleware

**File:** `src/main.py`

I added two standard middlewares using `app.add_middleware(...)`:

- `TrustedHostMiddleware` — rejects requests with unrecognized `Host` headers. I configured it via the `TRUSTED_HOSTS` env var, defaulting to `["*"]` so everything works locally without extra setup.
- `CORSMiddleware` — configured via `CORS_ORIGINS` (default `["*"]`). In production, I'd set it to the actual frontend domain like `["https://app.unitalent.com"]`.

```python
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
```

---

### 1b. Custom Logging Middleware

**File:** `src/middleware/logging.py`

I wrote a custom middleware that logs every HTTP request. Here's what the output looks like:

```
2026-04-05 12:00:00,000 | INFO    | 127.0.0.1:54321 - GET - /jobs - 200 - 12.34ms
2026-04-05 12:00:01,000 | WARNING | 127.0.0.1:54322 - POST - /auth/login - 401 - 5.10ms
2026-04-05 12:00:02,000 | ERROR   | 127.0.0.1:54323 - GET - /broken - 500 - 1.20ms
```

I chose the log level based on the HTTP status code:

| HTTP Status | Log Level |
|---|---|
| 2xx / 3xx | INFO |
| 4xx | WARNING |
| 5xx | ERROR |

Logs go to both the console and a rotating file at `logs/app.log` (max 10 MB, 5 backups).

For the implementation I used `BaseHTTPMiddleware`, measured request time with `time.perf_counter()`, and grabbed the client IP from `request.client.host:port`.

---

### 1c. Rate Limiting

**File:** `src/middleware/rate_limit.py`

I used `fastapi-limiter` 0.2.0 with `pyrate-limiter` for in-memory per-worker rate limiting.

I set up three levels of limits:

| Limit | Value | Applies to |
|---|---|---|
| Per IP / minute | 30 req | All endpoints (app-level `dependencies`) |
| Per IP / hour | 500 req | All endpoints (app-level `dependencies`) |
| Write per IP / hour | 50 req | POST / PATCH / DELETE only (per-route `Depends`) |
| GET requests | No write limit | Read-only operations are unrestricted |

I wired the app-level limits through FastAPI's `dependencies`:

```python
app = FastAPI(dependencies=[
    Depends(rate_limit_per_minute()),   # 30/min
    Depends(rate_limit_per_hour()),     # 500/hr
])
```

For write endpoints I added the limit individually per route:

```python
@router.post("/{candidate_id}/photo", dependencies=[Depends(write_rate_limit())])
```

When the limit is exceeded, `429 Too Many Requests` is returned automatically.

To identify the client IP I check `X-Forwarded-For` first, then fall back to `request.client.host`. Each IP has its own counter keyed as `ip:route_index:dep_index`.

---

### 1d. Profiling

**File:** `src/middleware/profiling.py`

I added a profiling middleware using `pyinstrument` 5.x to find slow endpoints.

It's enabled via env vars:

```env
PROFILING_ENABLED=true
SLOW_ENDPOINT_THRESHOLD_MS=500
```

It tracks:
- **Latency** — wall-clock time via `profiler.last_session.duration`
- **Call stack** — pyinstrument records the full call stack per request

When a request is slower than the threshold, I see something like this in the logs:

```
WARNING | SLOW ENDPOINT GET /applications — 850ms
  File "src/applications/service.py", line 31
    list_applications  850ms
      session.exec     820ms   ← N+1 query chains
```

After running the profiler I found these slow spots:

| Endpoint | Typical Latency | Root Cause |
|---|---|---|
| `GET /applications` | 400–900ms | `selectin` on `candidate`, `job`, `resume`, `interviews` — 4 extra queries per row in the list |
| `GET /candidates/{id}` | 200–400ms | Loads `user`, `applications[]`, `resumes[]` via selectin |
| `GET /interview-sessions/{id}` | 300–600ms | Loads `interviews[]`, each with nested `application → candidate → user` |

How to fix them:
- Use `joinedload` at the query level instead of model-level `lazy="selectin"` for list responses
- Return only needed fields (projection) instead of full ORM objects
- Add a Redis cache layer for frequently-read public endpoints (`GET /jobs`, `GET /companies`)

To avoid profiling overhead in production I can set `PROFILING_ENABLED=false` — it's a single `if` check, so zero cost. Or I can enable sampling: change `if random.random() > 1.0:` to `> 0.9` to profile only 10% of requests.

---

## 2. Background Tasks (Celery)

**Broker & Backend:** Redis (`REDIS_URL` — the same instance used for rate limiting and the token blocklist)

**Email provider:** Gmail SMTP via Google App Password (`myaccount.google.com/apppasswords`). No third-party sandbox needed — emails are delivered to real inboxes.

Start the worker:
```bash
celery -A src.celery_app worker --loglevel=info --pool=solo
```



---

### 2a. Email Confirmation & Password Reset

**Files:** `src/tasks/email_tasks.py`, `src/auth/tokens.py`, `src/auth/service.py`, `src/auth/router.py`

For sending emails I used `fastapi-mail` + `aiosmtplib` over Gmail SMTP (port 587, STARTTLS). Authentication uses a Google App Password — a 16-character app-specific password generated at `myaccount.google.com/apppasswords`, so the main Google account password is never exposed. For tokens I used `python-jose` JWT — same signing key as auth tokens, but with a different `type` claim.

#### Email Verification Flow

Here's the flow I implemented:

1. User registers via `POST /auth/register`
2. `register_user()` creates the user with `is_verified=False`
3. `send_confirmation_email.delay(user_id, email, token)` fires in the background
4. The Celery worker sends an email with a link: `{FRONTEND_URL}/auth/verify-email/{token}` (token valid for 24h)
5. User clicks the link → `POST /auth/verify-email/{token}`
6. `verify_email()` decodes the JWT and sets `user.is_verified=True`

Resend: `POST /auth/request-verification` (requires auth) re-sends the email.

#### Password Reset Flow

1. User calls `POST /auth/request-password-reset` with `{"email": "..."}`
2. If the email exists: `send_password_reset_email.delay(...)` fires (token valid for 1h)
3. If email not found: I still return `204` — this prevents email enumeration
4. User clicks the link → `POST /auth/reset-password/{token}` with `{"new_password": "..."}`
5. `reset_password()` decodes the JWT, updates the password hash, and clears the refresh token (invalidating all sessions)

New endpoints I added:
```
POST /auth/request-verification      → 204
POST /auth/verify-email/{token}      → UserRead
POST /auth/request-password-reset    → 204
POST /auth/reset-password/{token}    → UserRead
```

---

### 2b. Image Upload + Compression (stored as raw binary in PostgreSQL)

**Files:** `src/tasks/image_tasks.py`, `src/candidates/router.py`

I decided to store photos directly in PostgreSQL in the `candidates.photo` column as `BYTEA`.

**Endpoint:** `POST /candidates/{id}/photo`
- Auth required (own profile or admin)
- Accepts: `image/jpeg`, `image/png`
- Max size: 5 MB
- Returns **202 Accepted** immediately — compression and storage happen in the background

**Celery task `compress_and_store_photo`:**

1. Log the original size in bytes and KB
2. Open with Pillow, convert to RGB, resize to max 800×800 (preserving aspect ratio)
3. Save as JPEG quality=75 with optimize=True
4. Log the compressed size, ratio, and KB saved
5. Write compressed bytes directly to `candidates.photo` (BYTEA) via a sync SQLAlchemy session

Example log output:
```
[photo] candidate=1 | original size: 2457600 bytes (2400.0 KB)
[photo] candidate=1 | compressed size: 148320 bytes (144.8 KB) — 6.0% of original, saved 2255.1 KB
[photo] candidate=1 | stored in PostgreSQL ✓
```

**Why sync SQLAlchemy inside a Celery task?**
Celery workers are synchronous. The web server uses `asyncpg` which requires a running event loop — but there's no event loop inside a Celery task. So I convert the DB URL from `postgresql+asyncpg://...` to `postgresql://...` and use a regular sync `Session`.

**Why BYTEA and not a file path?**
Storing the binary directly in PostgreSQL keeps the system self-contained — no need for an external file server or object storage. I compress photos from ~2–5 MB down to ~100–200 KB before writing, so the impact on the database is acceptable for profile photos.

In `CandidateRead` I added a `has_photo: bool` field — it tells you whether a photo exists, but the raw binary is never returned in JSON responses.

---

### 2c. Application Status Notification (Creative Task)

**File:** `src/applications/service.py`, `src/tasks/email_tasks.py`

My idea here: whenever a recruiter changes an application status, the candidate automatically gets an email notification via Celery.

**Trigger:** Inside `patch_application()` — after the database commit, if `status` changed:

```python
send_application_status_email.delay(
    candidate_email, candidate_name, job_title, company_name, new_status
)
```

It fires on any status transition: `submitted→reviewing`, `reviewing→accepted`, `reviewing→rejected`.

Example email:
```
Subject: Application update: ACCEPTED — Backend Developer

Hi John Smith,

Your application for Backend Developer at TechCorp has been updated to:

ACCEPTED
```

**Why I think this is useful:** Candidates don't need to keep polling the API — they get real-time email updates when a recruiter acts on their application. The notification is fire-and-forget: if Celery is unavailable, the status update still goes through successfully.

---

## 3. Demo Run & Bug Fixes (2026-04-06)

### 3a. End-to-End Demo Walkthrough

The full system was tested manually via Postman using the following environment variables:

| Variable        | Value                  |
|-----------------|------------------------|
| base_url        | http://localhost:8000  |
| candidate_token | (set after login)      |
| recruiter_token | (set after login)      |

Three terminals were running simultaneously:
- **Terminal 1** — FastAPI server: `uvicorn src.main:app --reload`
- **Terminal 2** — Celery worker: `celery -A src.celery_app worker --loglevel=info --pool=solo`
- **Terminal 3** — Log monitoring: `tail -f logs/app.log`

**Steps completed:**

1. `GET /` → 200 `{"message": "UniTalent Recruitment System API"}`
2. `POST /auth/register` with `role: candidate` → 201, verification email sent to real inbox
3. `POST /auth/register` with `role: recruiter` → 201, no email sent (by design)
4. `POST /auth/login` for both users → access tokens saved to Postman variables
5. `POST /auth/verify-email/{token}` → `is_verified: true`
6. `POST /auth/request-password-reset` → 204, reset email delivered
7. `POST /auth/reset-password/{token}` → 200, password updated, sessions invalidated
8. Rate limit test via Postman Collection Runner (35 iterations on `GET /`) → first 30 returned 200, from request 31 onwards → 429
9. Confirmed `logs/app.log` contains lines with format: `IP - METHOD - PATH - STATUS - Xms`
10. `POST /candidates` (candidate token) → candidate profile created
11. `POST /companies` (recruiter token) → company created
12. `POST /jobs` (recruiter token) → job vacancy created
13. `POST /resumes` (candidate token) → resume created (hit 429 initially — waited 1 minute for rate limit reset)
14. `POST /candidates/1/photo` (form-data, .jpg file) → 202, Celery compressed and stored photo
15. `POST /applications` → application submitted
16. `PATCH /applications/1` `{"status": "reviewing"}` → email sent to candidate
17. `PATCH /applications/1` `{"status": "accepted"}` → email sent to candidate

All 17 checklist items passed successfully.

---

