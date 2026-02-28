from fastapi import FastAPI

from src.db.init_db import init_db

from src.candidates.router import router as candidates_router
from src.companies.router import router as companies_router
from src.jobs.router import router as jobs_router
from src.applications.router import router as applications_router
from src.interviews.router import router as interviews_router


app = FastAPI(title="UniTalent Recruitment API")


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.get("/")
async def root():
    return {"message": "UniTalent Recruitment System API"}


app.include_router(candidates_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(interviews_router)