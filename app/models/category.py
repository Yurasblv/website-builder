from sqlalchemy.orm import Mapped, relationship

from app.models.base import Base, UUIDModel


class Category(UUIDModel, Base):
    __tablename__ = "category"

    title: Mapped[str]

    domains = relationship("Domain", back_populates="category")
