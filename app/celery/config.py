from typing import Any

from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core import init_sentry_worker, settings

from .utils import CeleryTask, CustomCelery

celery_app: CustomCelery = CustomCelery(
    "worker",
    broker=settings.redis.celery_broker,
    backend=settings.redis.celery_backend,
    include=[
        "app.celery.tasks.backlinks",
        "app.celery.tasks.clusters",
        "app.celery.tasks.pbns",
        "app.celery.tasks.social_networks",
    ],
    task_cls=CeleryTask,
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # 1h expiration time for results
    result_backend_transport_options={"visibility_timeout": 3600},
)


# https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#entries
# Define the periodic tasks and their execution schedule
celery_app.conf.beat_schedule = {
    "backlink_publish_task": {
        "task": "app.celery.tasks.backlinks.run_pbn_backlink_publish_task",
        "schedule": crontab(hour=0, minute=0),
    },
    "pbns_redeploy_task": {
        "task": "app.celery.tasks.pbns.run_failure_redeploy_task",
        "schedule": crontab(hour=0, minute=0),
    },
    "post_x_daily_task": {
        "task": "app.celery.tasks.social_networks.create_post_x_task",
        "schedule": crontab(hour=15, minute=0),  # 3 PM UTC (8 AM PT)
    },
}

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-routes
# Define task routes for routing tasks to specific queues

periodic_tasks: list[str] = [
    "app.celery.tasks.backlinks.run_pbn_backlink_publish_task",
    "app.celery.tasks.pbns.run_failure_redeploy_task",
    "app.celery.tasks.social_networks.create_post_x_task",
]

celery_app.conf.task_routes = {task: "periodic" for task in periodic_tasks}


@worker_process_init.connect
def init_worker(*args: Any, **kwargs: Any) -> None:
    init_sentry_worker()
