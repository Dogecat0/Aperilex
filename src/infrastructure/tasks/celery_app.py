"""Celery application configuration for background task processing."""

from celery import Celery

from src.shared.config.settings import settings


def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    celery_app = Celery(
        "aperilex",
        broker=settings.celery_broker_url or settings.redis_url,
        backend=settings.celery_result_backend or settings.redis_url,
        include=[
            "src.infrastructure.tasks.filing_tasks",
            "src.infrastructure.tasks.analysis_tasks",
        ],
    )

    # Configuration
    celery_app.conf.update(
        task_serializer=settings.celery_task_serializer,
        result_serializer=settings.celery_result_serializer,
        accept_content=settings.celery_accept_content,
        timezone=settings.celery_timezone,
        enable_utc=settings.celery_enable_utc,
        task_track_started=settings.celery_task_track_started,
        task_time_limit=settings.celery_task_time_limit,
        task_soft_time_limit=settings.celery_task_soft_time_limit,
        worker_concurrency=settings.celery_worker_concurrency,
        # Task routing
        task_routes={
            "src.infrastructure.tasks.filing_tasks.*": {"queue": "filing_queue"},
            "src.infrastructure.tasks.analysis_tasks.*": {"queue": "analysis_queue"},
        },
        # Task result expiration
        result_expires=3600,  # 1 hour
        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        # Monitoring
        task_send_sent_event=True,
        worker_send_task_events=True,
    )

    return celery_app


# Create the Celery app instance
celery_app = create_celery_app()

# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "src.infrastructure.tasks",
    ]
)
