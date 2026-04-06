"""
Celery application configuration for background task processing.

Handles PDF parsing, rule validation, OCR/CV, and LLM analysis.
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery application
celery_app = Celery(
    "eskd_validator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,  # Using Redis as result backend
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.TASK_TIME_LIMIT,
    worker_prefetch_multiplier=1,  # Important for memory management with large files
    task_acks_late=True,  # Acknowledge tasks after completion
    worker_send_task_events=True,
    task_send_sent_event=True,
)
