from fastapi import FastAPI

from src.exceptions.handlers import register_exception_handlers

from src.auth.router import router as auth_router
from src.candidates.router import router as candidates_router
from src.companies.router import router as companies_router
from src.jobs.router import router as jobs_router
from src.resumes.router import router as resumes_router
from src.applications.router import router as applications_router
from src.interviews.router import router as interviews_router

app = FastAPI(title="UniTalent Recruitment API")





@app.get("/")
async def root():
    return {"message": "UniTalent Recruitment System API"}


register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(candidates_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(resumes_router)
app.include_router(applications_router)
app.include_router(interviews_router)