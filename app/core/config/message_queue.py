from app.core.config.base import BaseConfig


class MessageQueueConfig(BaseConfig):
    GLOBAL_QUEUE_NAME: str = "global_message_queue"
    KEYS_EXPIRATION_TIME: int = 3600  # 1 hour
