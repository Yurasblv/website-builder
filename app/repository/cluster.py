from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Cluster
from app.models.cluster import ClusterSettings
from app.repository.base import SQLAlchemyRepository


class ClusterRepository(SQLAlchemyRepository):
    model = Cluster
    base_stmt = select(model)
    settings_load = selectinload(model.settings)
    author_load = selectinload(model.author)
    pages_load = selectinload(model.pages)
    user_load = selectinload(model.user)


class ClusterSettingsRepository(SQLAlchemyRepository):
    model = ClusterSettings
    base_stmt = select(model)
