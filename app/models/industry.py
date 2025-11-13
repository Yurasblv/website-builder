from sqlalchemy.orm import Mapped, relationship

from app.models.base import Base, UUIDModel


class Industry(UUIDModel, Base):
    __tablename__ = "industry"

    title_us: Mapped[str]
    title_fr: Mapped[str]

    authors = relationship("Author", back_populates="industry")
    clusters = relationship("Cluster", back_populates="industry")
