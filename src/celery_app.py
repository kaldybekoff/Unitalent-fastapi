from celery import Celery

from src.config import settings

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
