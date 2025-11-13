from pathlib import Path

from pydantic import Field

from app.core.config.base import BaseConfig
from app.enums.base import ProjectStage, StorageBackend


class S3StorageConfig(BaseConfig):
    # Bucket names
    stage: ProjectStage = Field(ProjectStage.LOCAL, alias="STAGE")
    project: str = Field("NDA", alias="S3_PROJECT_NAME")
    APPLICATION: str = Field("applications", alias="S3_APPLICATIONS_BUCKET")
    ASSETS: str = Field("assets", alias="S3_ASSETS_BUCKET")
    AUTHORS: str = Field("authors", alias="S3_AUTHORS_BUCKET")
    TOPICS: str = Field("topics", alias="S3_TOPICS_BUCKET")
    PBN_ASSETS: str = Field("NDA-pbn-assets", alias="S3_PBN_ASSETS_BUCKET")

    # Credentials
    REGION: str = Field(..., alias="S3_REGION")
    ENDPOINT_URL: str = Field(..., alias="S3_ENDPOINT_URL")
    SECRET_KEY: str = Field(..., alias="S3_SECRET_KEY")
    ACCESS_KEY: str = Field(..., alias="S3_ACCESS_KEY")

    # Upload settings
    UPLOAD_RETRIES: int = Field(3, alias="S3_UPLOAD_RETRIES")
    UPLOAD_DELAY: int = Field(1, alias="S3_UPLOAD_DELAY")

    LINK_EXPIRES: int = Field(3600, alias="S3_LINK_EXPIRES")

    @property
    def pattern(self) -> str:
        return f"{self.project}-{{}}-{self.stage}"

    @property
    def applications(self) -> str:
        return self.pattern.format(self.APPLICATION)

    @property
    def assets(self) -> str:
        return self.pattern.format(self.ASSETS)

    @property
    def authors(self) -> str:
        return self.pattern.format(self.AUTHORS)

    @property
    def pbn_assets(self) -> str:
        return self.PBN_ASSETS

    @property
    def topics(self) -> str:
        return self.pattern.format(self.TOPICS)

    @property
    def authors_uri(self) -> str:
        return f"https://{self.authors}.{self.ENDPOINT_URL}"

    @property
    def applications_uri(self) -> str:
        return f"https://{self.applications}.{self.ENDPOINT_URL}"

    @property
    def assets_uri(self) -> str:
        return f"https://{self.assets}.{self.ENDPOINT_URL}"

    @property
    def topics_uri(self) -> str:
        return f"https://{self.topics}.{self.ENDPOINT_URL}"

    @property
    def pbn_assets_uri(self) -> str:
        return f"https://{self.pbn_assets}.{self.ENDPOINT_URL}"


class LocalStorageConfig(BaseConfig):
    media: str = Field("media", alias="LOCAL_STORAGE_MEDIA_FOLDER")
    APPLICATIONS: str = Field("applications", alias="LOCAL_STORAGE_APPLICATIONS_FOLDER")
    ASSETS: str = Field("assets", alias="LOCAL_STORAGE_ASSETS_FOLDER")
    AUTHORS: str = Field("authors", alias="LOCAL_STORAGE_AUTHORS_FOLDER")
    TOPICS: str = Field("topics", alias="LOCAL_STORAGE_TOPICS_FOLDER")

    @property
    def base(self) -> Path:
        return Path(__file__).resolve().parents[3] / self.media

    @property
    def applications(self) -> str:
        return self.APPLICATIONS

    @property
    def assets(self) -> str:
        return self.ASSETS

    @property
    def authors(self) -> str:
        return self.AUTHORS

    @property
    def topics(self) -> str:
        return self.TOPICS

    @property
    def topics_uri(self) -> str:
        return (self.base / self.topics).as_uri()

    @property
    def authors_uri(self) -> str:
        return (self.base / self.authors).as_uri()

    @property
    def applications_uri(self) -> str:
        return (self.base / self.applications).as_uri()

    @property
    def assets_uri(self) -> str:
        return (self.base / self.assets).as_uri()


class StorageConfig(BaseConfig):
    backend_type: StorageBackend = Field(StorageBackend.S3, alias="STORAGE_BACKEND", examples=StorageBackend.list())

    s3: S3StorageConfig = S3StorageConfig()
    local: LocalStorageConfig = LocalStorageConfig()

    @property
    def backend(self) -> S3StorageConfig | LocalStorageConfig:
        return getattr(self, self.backend_type)

    @property
    def applications(self) -> str:
        return self.backend.applications

    @property
    def assets(self) -> str:
        return self.backend.assets

    @property
    def authors(self) -> str:
        return self.backend.authors

    @property
    def topics(self) -> str:
        return self.backend.topics

    @property
    def topics_uri(self) -> str:
        return self.backend.topics_uri

    @property
    def authors_uri(self) -> str:
        return self.backend.authors_uri

    @property
    def applications_uri(self) -> str:
        return self.backend.applications_uri

    @property
    def assets_uri(self) -> str:
        return self.backend.assets_uri

    @property
    def pbn_assets(self) -> str:
        return self.backend.pbn_assets
