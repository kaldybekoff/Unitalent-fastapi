from celery import Celery

from src.config import settings

# Import all models so SQLAlchemy can resolve relationships in Celery workers
import src.users.models  # noqa: F401, E402
import src.candidates.models  # noqa: F401, E402
import src.companies.models  # noqa: F401, E402
import src.jobs.models  # noqa: F401, E402
import src.applications.models  # noqa: F401, E402
import src.resumes.models  # noqa: F401, E402
import src.interviews.models  # noqa: F401, E402

celery_app = Celery(
    "unitalent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.image_tasks",
        "src.tasks.email_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
