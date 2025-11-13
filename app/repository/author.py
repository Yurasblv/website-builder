from typing import Any, Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import with_polymorphic

from app.core.exc import RestrictedAuthorDeleting
from app.enums import SocialNetworkType
from app.models import Author, SocialNetwork
from app.repository.base import PaginateRepositoryMixin, SQLAlchemyRepository
from app.schemas.utils.ordering import Ordering


class AuthorRepository(SQLAlchemyRepository, PaginateRepositoryMixin):
    model = Author
    restrict_error_class = RestrictedAuthorDeleting

    def get_statement(self, filters: dict) -> select:
        created_by_id = filters.pop("created_by_id", None)
        clauses = self.get_where_clauses(filters)

        if created_by_id:
            clauses.append(or_(self.model.created_by_id == None, self.model.created_by_id == created_by_id))

        return select(self.model).where(*clauses)

    async def get_all(self, join_load_list: list = None, ordering: Ordering = None, **filters: Any) -> Sequence[Author]:
        """
        Get all objects

        Args:
            join_load_list: list of joined models
            ordering: ordering of the result
            filters: filters

        Returns:
            List of objects
        """

        statement = self.get_statement(filters)

        if field := getattr(self.model, self.default_order_by, None):
            statement = statement.order_by(field.desc())

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def get_one(self, **filters) -> Author:  # type: ignore
        statement = self.get_statement(filters)
        return await self.execute(statement=statement, action=lambda result: result.scalars().one())

    async def get_authors_by_social_network(
        self, social_network_type: SocialNetworkType, **filters: Any
    ) -> Sequence[Author]:
        social_network = with_polymorphic(SocialNetwork, "*", aliased=True)

        statement = (
            select(self.model, social_network)
            .outerjoin(self.model.social_networks.of_type(social_network))
            .where(
                *self.get_where_clauses(filters),
                self.model.social_networks.any(social_network.social_network_type == social_network_type),
            )
        )

        return await self.execute(statement, action=lambda result: result.unique().all())
