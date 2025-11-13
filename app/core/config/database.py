from pydantic import Field

from app.core.config.base import BaseConfig


class DataBaseConfig(BaseConfig):
    USER: str = Field(..., alias="DB_USER")
    PASSWORD: str = Field(..., alias="DB_PASSWORD")
    HOST: str = Field(..., alias="DB_HOST")
    PORT: str = Field(..., alias="DB_PORT")
    NAME: str = Field(..., alias="DB_NAME")
    DATA_VOLUME_NAME: str = "pg_volume"

    POOL_SIZE: int = 50
    MAX_OVERFLOW: int = 30
    POOL_RECYCLE: int = 1800
    BATCH_INSERT_SIZE: int = 10_000

    @property
    def url(self) -> str:
        """Constructs the SQLAlchemy URL using the database configuration."""
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"
