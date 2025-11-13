from app.models import ServiceAccount
from app.repository.base import SQLAlchemyRepository


class ServiceAccountRepository(SQLAlchemyRepository):
    model = ServiceAccount
