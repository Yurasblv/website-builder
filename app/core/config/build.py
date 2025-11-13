from pydantic import Field

from app.core.config.base import BaseConfig
from app.enums import ProjectStage


class BuildConfig(BaseConfig):
    stage: ProjectStage = Field(ProjectStage.LOCAL, alias="STAGE")

    IMAGE_NAME: str = Field(default="nda-static-builder")
    BUILD_DATA_VOLUME_NAME: str = Field(default="build-data")

    @property
    def image(self) -> str:
        return f"{self.IMAGE_NAME}-{self.stage}"
