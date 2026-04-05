from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.config import settings
from src.exceptions.handlers import register_exception_handlers
from src.middleware.logging import LoggingMiddleware
from src.middleware.profiling import ProfilingMiddleware
from src.middleware.rate_limit import rate_limit_per_hour, rate_limit_per_minute

from src.auth.router import router as auth_router
from src.candidates.router import router as candidates_router
from src.companies.router import router as companies_router
from src.jobs.router import router as jobs_router
from src.resumes.router import router as resumes_router
from src.applications.router import router as applications_router
from src.interviews.router import router as interviews_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="UniTalent Recruitment API",
    lifespan=lifespan,
    dependencies=[
        Depends(rate_limit_per_minute()),
        Depends(rate_limit_per_hour()),
    ],
)

# ── Middleware (outermost → innermost) ────────────────────────────────────────
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ProfilingMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(candidates_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(resumes_router)
app.include_router(applications_router)
app.include_router(interviews_router)


@app.get("/")
async def root():
    return {"message": "UniTalent Recruitment System API"}
