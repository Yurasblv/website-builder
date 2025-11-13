import asyncio
from typing import Any

from celery import Task, signals

from app.celery.utils import get_incoming_tasks, send_notification

from .building import cluster_building_task
from .creation import cluster_creation_failure_task, cluster_creation_success_task, cluster_creation_task
from .generation import cluster_generation_task
from .refresh import cluster_refreshing_failure_task, cluster_refreshing_success_task, cluster_refreshing_task

__all__ = (
    "cluster_building_task",
    "cluster_creation_failure_task",
    "cluster_creation_success_task",
    "cluster_creation_task",
    "cluster_generation_task",
    "cluster_refreshing_failure_task",
    "cluster_refreshing_success_task",
    "cluster_refreshing_task",
)


@signals.task_prerun.connect
def task_prerun_handler(sender: object, task_id: str, task: Task, *args: Any, **kwargs: Any) -> None:
    """
    Handle pre-run events for clusters tasks.
    Updates queue information and sends notifications to users.
    """

    handled_tasks = [
        cluster_building_task,
        cluster_creation_task,
        cluster_generation_task,
    ]

    if sender not in handled_tasks:
        return

    queue_name = task.request.delivery_info.get("routing_key", "celery")

    with asyncio.Runner() as runner:
        tasks = runner.run(get_incoming_tasks(queue_name))
        runner.run(send_notification(tasks))
