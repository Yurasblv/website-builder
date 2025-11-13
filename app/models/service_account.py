from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDModel


class ServiceAccount(UUIDModel, Base):
    __tablename__ = "service_account"

    email: Mapped[str]
    password: Mapped[str]
    session: Mapped[str] = mapped_column(nullable=True)

    money_sites: Mapped[set["MoneySite"]] = relationship(  # noqa: F821
        "MoneySite",
        secondary="moneysite_serviceaccount_association",
        back_populates="service_accounts",  # noqa: F821
    )
    pbn = relationship("PBN", back_populates="service_account", cascade="all", passive_deletes=True)
