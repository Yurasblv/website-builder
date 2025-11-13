from typing import Any

from sqlalchemy.orm import selectinload

from app.models import Project
from app.repository.base import SQLAlchemyRepository


class ProjectRepository(SQLAlchemyRepository):
    model = Project

    clusters_load = selectinload(model.clusters)

    async def get_or_create(self, **kwargs: Any) -> Project:
        """
        Get or create a project by its name and user_id.
        """
        project = await self.get_one_or_none(**kwargs)

        if not project:
            kwargs["name"] = kwargs["type"].lower()
            project = await self.create(kwargs)

        return project
