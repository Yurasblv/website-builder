from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums.project import ProjectType
from app.models.base import Base, TimestampModel, UUIDModel


class Project(UUIDModel, TimestampModel, Base):
    __tablename__ = "project"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ProjectType] = mapped_column(
        ENUM(ProjectType), default=ProjectType.CUSTOM, server_default=ProjectType.CUSTOM
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user_info.id"), nullable=False, index=True)

    user = relationship("UserInfo", back_populates="projects", cascade="all, delete")
    clusters = relationship("Cluster", back_populates="project")

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_project_user_id_name"),)

    @property
    def is_custom(self) -> bool:
        """
        Check if the project is of type CUSTOM.

        Returns:
            bool: True if the project type is CUSTOM, False otherwise.
        """
        return self.type == ProjectType.CUSTOM
