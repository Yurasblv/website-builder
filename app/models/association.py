from sqlalchemy import Column, ForeignKey, Index, String

from app.models.base import Base


class MoneySiteServiceAccountAssociation(Base):
    __tablename__ = "moneysite_serviceaccount_association"

    money_site_id = Column(ForeignKey("money_site.id"), primary_key=True)
    service_account_id = Column(ForeignKey("service_account.id"), primary_key=True)
    money_site_domain = Column(String, nullable=False)

    Index("ix_serviceaccount_association_domain", money_site_domain)


class MoneySiteServerAssociation(Base):
    __tablename__ = "moneysite_server_association"

    money_site_id = Column(ForeignKey("money_site.id"), primary_key=True)
    server_provider_id = Column(ForeignKey("server_provider.id"), primary_key=True)
    money_site_domain = Column(String, nullable=False)

    Index("ix_server_association_domain", money_site_domain)
