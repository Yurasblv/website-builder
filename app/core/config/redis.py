from pydantic import Field, model_validator

from app.core.config.base import BaseConfig


class RedisConfig(BaseConfig):
    MAX_CONNECTIONS: int = 1000
    host: str = Field(..., alias="REDIS_HOST")
    port: int = Field(..., alias="REDIS_PORT")
    username: str | None = Field(None, alias="REDIS_USERNAME")
    password: str | None = Field(None, alias="REDIS_PASSWORD")
    db: int = Field(0, alias="REDIS_DB")

    online_key: str = "online"
    ttl: int = 600
    count_to_collect: int = 100

    # WebSockets
    ws_ttl: int = 60
    message_key: str = "ws:message"
    message_watch_key: str = "ws:message:watch"

    # Celery
    broker_db: int = Field(0, alias="CELERY_BROKER_DB")
    backend_db: int = Field(1, alias="CELERY_BACKEND_DB")
    celery_broker: str = Field("", alias="CELERY_BROKER_URL")
    celery_backend: str = Field("", alias="CELERY_RESULT_BACKEND")

    @property
    def base_url(self) -> str:
        # Construct the Redis URL based on the provided settings
        host_port = f"{self.host}:{self.port}"

        if self.username and self.password:
            return f"redis://{self.username}:{self.password}@{host_port}"

        elif self.password:
            return f"redis://:{self.password}@{host_port}"

        else:
            return f"redis://{host_port}"

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.db}"

    @model_validator(mode="after")
    def validate_(self) -> "RedisConfig":
        """
        Validate the broker URL and backend URL.
        """
        # TODO: replace with f"{self.base_url}/{self.broker_db}" and f"{self.base_url}/{self.backend_db}" in local
        # self.celery_broker = f"{self.base_url}/{self.broker_db}"
        # self.celery_backend = f"{self.base_url}/{self.backend_db}"
        self.celery_broker = self.celery_broker or f"{self.base_url}/{self.broker_db}"
        self.celery_backend = self.celery_backend or f"{self.base_url}/{self.backend_db}"

        return self
