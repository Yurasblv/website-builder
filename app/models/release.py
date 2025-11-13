from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Release(Base):
    __tablename__ = "release"

    version: Mapped[str] = mapped_column(nullable=False, primary_key=True)
