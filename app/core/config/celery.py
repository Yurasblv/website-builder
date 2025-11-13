from pydantic import Field

from app.core.config.base import BaseConfig


class CeleryConfig(BaseConfig):
    # Worker Configuration
    worker_timeout: int = Field(10, alias="CELERY_WORKER_TIMEOUT")
    max_workers: int = Field(5, alias="CELERY_MAX_WORKERS")
    max_queue_length: int = Field(10, alias="CELERY_MAX_QUEUE_LENGTH")
    wait_time: int = Field(10, alias="CELERY_WORKER_WAIT_TIME")
    worker_prefix: str = Field("celery-worker", alias="CELERY_WORKER_PREFIX")
    worker_concurrency: int = Field(5, alias="CELERY_WORKER_CONCURRENCY")

    # Docker Configuration
    docker_image: str = Field("celery_worker:latest", alias="CELERY_WORKER_DOCKER_IMAGE")
    network_name: str = Field("celery-network", alias="CELERY_DOCKER_NETWORK")
