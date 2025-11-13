import re
from abc import ABC, abstractmethod
from numbers import Number
from typing import Any, Callable, Generic, Literal, Sequence, Type, TypeVar

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    ColumnClause,
    Executable,
    Result,
    UnaryExpression,
    asc,
    delete,
    desc,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_loader_criteria

from app.core import settings
from app.core.exc import (
    DBConnectionException,
    ForeignKeyViolationException,
    ObjectExistsException,
    ObjectNotFoundException,
)
from app.enums import ExecutionMode, OrderDirection
from app.models.base import Base
from app.schemas.utils.ordering import Ordering
from app.schemas.utils.paginator import PaginatedOutput
from app.utils.paginator import paginate

ModelType = TypeVar("ModelType", bound=Base)
OperatorType = Callable[[Column, Any], ColumnClause]


action_map = {
    "gt": "__gt__",
    "lt": "__lt__",
    "ge": "__ge__",
    "le": "__le__",
    "in": "in_",
    "not_in": "notin_",
    "contains": "contains",
    "icontains": "ilike",
    "eq": "__eq__",
    "ne": "__ne__",
}


def get_obj_from_integrity_error(e: IntegrityError) -> str:
    match = re.search(r"Key \((.*?)\)=\((.*?)\) already exists", str(e.orig))
    if match:
        return f"{match.group(1)}={match.group(2)}"
    return ""


class AbstractRepository(ABC, Generic[ModelType]):
    @abstractmethod
    async def get_all(self, **filters: Any) -> Sequence[ModelType]:
        raise NotImplementedError

    @abstractmethod
    async def get_one(self, **filters: Any) -> ModelType | None:
        raise NotImplementedError

    @abstractmethod
    async def get_one_or_none(self, **filters: Any) -> ModelType | None:
        raise NotImplementedError

    @abstractmethod
    async def get_first(self, **filters: Any) -> ModelType | None:
        raise NotImplementedError

    @abstractmethod
    async def get_random(self, limit: int = 50) -> Sequence[ModelType]:
        raise NotImplementedError

    @abstractmethod
    async def get_multi(self, offset: int, limit: int, **filters: Any) -> Sequence[ModelType]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, obj_in: BaseModel | dict[str, Any]) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self, obj_in: BaseModel | dict[str, Any], *, return_object: bool = False, **filters: Any
    ) -> int | ModelType:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, return_object: bool = False, **filters: Any) -> int | ModelType:
        raise NotImplementedError


class SQLAlchemyRepository(AbstractRepository, Generic[ModelType]):
    model: Type[ModelType]
    default_order_by: str = "created_at"
    duplicate_error_class = ObjectExistsException
    object_not_found_error_class = ObjectNotFoundException
    restrict_error_class = ForeignKeyViolationException

    def __init__(self, session: AsyncSession):
        self.literal_log: bool = settings.EXECUTION_MODE == ExecutionMode.TEST
        self.session = session
        self.model_name = self.model.__name__

    def _build_query(
        self, stmt: Executable | None = None, join_load_list: list = None, join_filters: dict = None, **filters: Any
    ) -> Executable:
        statement = select(self.model)

        if stmt is not None:
            statement = stmt

        join_load_list = join_load_list or []

        statement = statement.options(*self.get_join_load_options(join_load_list, join_filters))

        statement = statement.where(*self.get_where_clauses(filters))

        return statement

    def _compile_statement(self, statement: Executable) -> Executable:
        """
        Compile statement

        Args:
            statement: statement

        Returns:
            Compiled statement
        """

        if self.literal_log:
            return statement.compile(compile_kwargs={"literal_binds": True})  # type:ignore[attr-defined]
        return statement

    async def execute(self, statement: Executable, action: Callable[[Any], Any] | None = None) -> Any:
        """
        Execute statement

        Args:
            statement: statement
            action: action

        Returns:
            Result of the statement

        """
        try:
            result: Result = await self.session.execute(statement)
            return action(result) if action else result

        except IntegrityError as e:
            if "duplicate" in str(e):
                raise self.duplicate_error_class(class_name=self.model_name, obj=get_obj_from_integrity_error(e))

            elif "ForeignKeyViolationError" in str(e):
                raise self.restrict_error_class(class_name=self.model_name, obj=get_obj_from_integrity_error(e))

            raise e

        except NoResultFound:
            raise self.object_not_found_error_class(
                class_name=self.model_name,
                statement=self._compile_statement(statement),
            )

        except OSError as e:
            raise DBConnectionException(detail=str(e))

    async def get_all(
        self, join_load_list: list = None, ordering: Ordering = None, **filters: Any
    ) -> Sequence[ModelType]:
        """
        Get all objects

        Kwargs:
            filters: filters

        Returns:
            Objects
        """

        statement = self._build_query(join_load_list=join_load_list, **filters)
        statement = statement.order_by(*self.get_ordering_clause(ordering))

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def get_one(self, join_load_list: list = None, **filters: Any) -> ModelType:
        """
        Get one object

        Kwargs:
            filters: filters

        Returns:
            Object
        """
        statement = self._build_query(join_load_list=join_load_list, **filters)
        return await self.execute(statement=statement, action=lambda result: result.scalars().one())

    async def get_one_or_none(self, join_load_list: list = None, **filters: Any) -> ModelType | None:
        """
        Get one object or None

        Kwargs:
            filters: filters

        Returns:
            Object or None
        """

        statement = self._build_query(join_load_list=join_load_list, **filters)
        return await self.execute(statement=statement, action=lambda result: result.scalars().one_or_none())

    async def get_first(self, join_load_list: list = None, **filters: Any) -> ModelType:
        stmt = self._build_query(join_load_list=join_load_list, **filters)

        return await self.execute(statement=stmt, action=lambda result: result.scalars().first())

    async def get_random(self, limit: int = 50, **filters: Any) -> Sequence[ModelType]:
        subquery = (select(self.model.id).order_by(func.random()).limit(limit)).subquery()

        statement = select(self.model).where(self.model.id.in_(select(subquery)))
        statement = statement.where(*self.get_where_clauses(filters))
        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def get_multi(self, offset: int = 0, limit: int = 50, /, **filters: Any) -> Sequence[ModelType]:
        """
        Get multiple objects

        Args:
            offset: offset
            limit: limit

        Kwargs:
            filters: filters

        Returns:
            List of objects
        """
        statement = select(self.model).where(*self.get_where_clauses(filters)).offset(offset).limit(limit)

        if field := getattr(self.model, self.default_order_by, None):
            statement = statement.order_by(field.desc())

        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    def get_where_clauses(self, filters: dict[str, Any], model: type[ModelType] = None) -> list[ColumnClause]:
        """
        Get where clauses for model

        Args:
            filters: dict with filters
            model: model to use, if None, use self.model

        Raises:
            ValueError: if operator is not supported
            ValueError: if column is not found

        Returns:
            list of where clauses
        """

        model = model or self.model
        clauses: list[ColumnClause] = []

        for key, value in filters.items():
            if "__" not in key:
                key = f"{key}__eq"

            column_name, action_name = key.split("__", 1)

            column: Column | None = getattr(model, column_name, None)
            if column is None:
                raise ValueError(f"Invalid column '{column_name}' for model '{model.__name__}'.")

            action_method: str | None = action_map.get(action_name)
            if action_method is None:
                raise ValueError(
                    f"Unsupported action '{action_name}'. Supported actions: {', '.join(action_map.keys())}."
                )

            clause: ColumnClause = getattr(column, action_method)(value)
            clauses.append(clause)

        return clauses

    def get_ordering_clause(self, order: Ordering = None) -> list[UnaryExpression]:
        """
        Builds a SQLAlchemy ordering clause based on the provided ordering configuration.

        Args:
            order: An instance of the Ordering model specifying the field and direction.

        Returns:
            A list containing one SQLAlchemy ordering expression, or an empty list if the field is not found.
        """

        if not order:
            field = getattr(self.model, self.default_order_by, None)
            return [desc(field)] if field else []

        direction = asc if order.order_direction == OrderDirection.ASC else desc
        field = getattr(self.model, order.order_by, None)
        return [direction(field)] if field else []

    @staticmethod
    def _get_nested_model(model: type[ModelType], path: list[str]) -> type[ModelType]:
        """
        Recursively resolves the nested model class given a path of relationship names.

        Args:
            model: The starting model class.
            path: A list of relationship names to traverse.

        Raises:
            ValueError: If a relationship is invalid or not found.

        Returns:
            The final model class after traversing the path.
        """

        for rel in path:
            rel_attr = getattr(model, rel, None)

            if rel_attr is None or not hasattr(rel_attr, "property"):
                raise ValueError(f"Invalid relationship '{rel}' for model '{model.__name__}'.")

            model = rel_attr.property.mapper.class_

        return model

    def get_join_load_options(self, join_load_list: list[Any], filters: dict[str, Any] = None) -> list:
        """
        Get load options with filters for relationships.

        Args:
            join_load_list: list of relationships to eager load
            filters: dict with filters, including nested filters like 'relationship__column__eq'

        Returns:
            List of load options
        """

        options = []
        filters = filters or {}

        for load_obj in join_load_list:
            rel_path = [rel.key for rel in load_obj.path if hasattr(rel, "key")]
            relation_prefix = "__".join(rel_path)

            rel_model = self._get_nested_model(self.model, rel_path)

            rel_filters = {
                key.replace(f"{relation_prefix}__", ""): value
                for key, value in filters.items()
                if key.startswith(f"{relation_prefix}__")
            }

            options.append(load_obj)

            if not rel_filters:
                continue

            clauses = self.get_where_clauses(filters=rel_filters, model=rel_model)
            for clause in clauses:
                # TODO: Use carefully e.g with_loader_criteria() applies conditions to that secondary query only.
                options.append(with_loader_criteria(rel_model, clause, include_aliases=True))

        return options

    async def create(self, obj_in: BaseModel | dict[str, Any]) -> ModelType:
        """
        Create object

        Args:
            obj_in: object to create

        Returns:
            Created object
        """
        logger.debug(f"Creating {self.model_name}")

        data = obj_in.model_dump(mode="json") if isinstance(obj_in, BaseModel) else obj_in
        statement = insert(self.model).values(**data).returning(self.model)
        return await self.execute(statement=statement, action=lambda result: result.scalar_one())

    async def bulk_create(self, objs_in: list[BaseModel | dict[str, Any]]) -> list[ModelType]:
        """
        Create objects

        Args:
            objs_in: objects to create

        Returns:
            Created objects
        """

        logger.debug(f"Bulk creating {len(objs_in)} {self.model_name}")

        objects = objs_in
        if isinstance(objs_in[-1], BaseModel):
            objects = [obj.model_dump(mode="json") for obj in objs_in]  # type: ignore[union-attr]

        statement = insert(self.model).values(objects).returning(self.model)
        return await self.execute(statement=statement, action=lambda result: result.scalars().all())

    async def update(
        self, obj_in: BaseModel | dict[str, Any], *, return_object: bool = False, **filters: Any
    ) -> int | ModelType:
        """
        Update object

        Args:
            obj_in: object to update
            return_object: return updated object

        Kwargs:
            filters: filters

        Returns:
            Number of updated objects or object itself
        """
        logger.debug(f"Updating {self.model_name} with {filters=}")

        obj_in = obj_in.model_dump(mode="json") if isinstance(obj_in, BaseModel) else obj_in

        statement = update(self.model).where(*self.get_where_clauses(filters)).values(**obj_in)

        if return_object:
            statement = statement.returning(self.model)
            return await self.execute(statement=statement, action=lambda result: result.scalars().one())

        return await self.execute(statement=statement, action=lambda result: result.rowcount)

    async def delete(self, return_object: bool = False, **filters: Any) -> int | ModelType:
        """
        Delete object

        Args:
            return_object: return deleted object

        Kwargs:
            filters: filters

        Returns:
            Number of deleted objects or object itself
        """
        logger.debug(f"Deleting {self.model_name} with {filters=}")

        statement = delete(self.model).where(*self.get_where_clauses(filters))

        if return_object:
            statement = statement.returning(self.model)
            return await self.execute(statement=statement, action=lambda result: result.scalars().one())

        return await self.execute(statement=statement, action=lambda result: result.rowcount)

    async def get_count(self, **filters: Any) -> int:
        """
        Get count of objects

        Kwargs:
            filters: Filters

        Returns:
            Count of objects
        """

        statement = select(func.count(self.model.id)).where(*self.get_where_clauses(filters))

        return await self.execute(statement, action=lambda result: result.scalar())

    async def exist(self, mode: Literal["all", "any"] = "any", **filters: Any) -> bool:
        """
        Check if the values exist in the database

        Args:
            mode: The mode to check the existence. Defaults to "any".

        Returns:
            True if the values exist, False otherwise
        """

        result = await self.get_count(**filters)

        if mode == "any":
            return bool(result)

        values = []

        for key, value in filters.items():
            if key.endswith("__in") and isinstance(value, list):
                values = value
                break

        return result == len(values)

    async def sum(self, column: str, **filters: Any) -> Number:
        """
        Get sum of objects

        Args:
            column: column to sum
            filters: filters

        Returns:
            Sum of objects
        """

        statement = select(func.sum(getattr(self.model, column))).where(*self.get_where_clauses(filters))
        ret: Number = await self.execute(statement, action=lambda result: result.scalar()) or 0

        return ret


class ModelInheritanceCreateMixin(Generic[ModelType]):
    model: Type[ModelType]
    session: AsyncSession
    duplicate_error_class = ObjectExistsException

    async def create(self, obj_in: BaseModel | dict[str, Any], autocommit: bool = True) -> ModelType:
        """
        Create the instance via model because of polymorphic inheritance

        Args:
            obj_in: object to create
            autocommit: commit the transaction

        Returns:
            Object instance
        """
        model_name = self.model.__name__
        obj_in = obj_in.model_dump(mode="json") if isinstance(obj_in, BaseModel) else obj_in
        instance = self.model(**obj_in)

        try:
            self.session.add(instance)
            if autocommit:
                await self.session.commit()

        except IntegrityError as e:
            if "duplicate" in str(e):
                raise self.duplicate_error_class(class_name=model_name, obj=get_obj_from_integrity_error(e))
            raise e

        except OSError as e:
            raise DBConnectionException(detail=str(e))

        return instance

    async def bulk_create(self, objs_in: list[BaseModel | dict[str, Any]], autocommit: bool = True) -> list[ModelType]:
        """
        Bulk create instances via model for polymorphic inheritance

        Args:
            objs_in: list of objects to create
            autocommit: commit the transaction

        Returns:
            List of object instances
        """

        model_name = self.model.__name__

        logger.debug(f"Bulk creating {len(objs_in)} {model_name}")

        objects = objs_in
        if isinstance(objs_in[-1], BaseModel):
            objects = [obj.model_dump(mode="json") for obj in objs_in]  # type: ignore[union-attr]

        instances = [self.model(**obj) for obj in objects]  # type: ignore[arg-type]

        try:
            self.session.add_all(instances)
            if autocommit:
                await self.session.commit()

        except IntegrityError as e:
            if "duplicate" in str(e):
                raise self.duplicate_error_class(class_name=model_name, obj=get_obj_from_integrity_error(e))
            raise e

        except OSError as e:
            raise DBConnectionException(detail=str(e))

        return instances


class ModelInheritanceDeleteMixin(Generic[ModelType]):
    model: Type[ModelType]
    execute: Callable

    async def delete(self, return_object: bool = False, **filters: Any) -> int | ModelType:
        """
        Delete object with support for joined table inheritance.

        Args:
            return_object: return deleted object
            filters: filters

        Returns:
            Number of deleted objects or object itself
        """
        if hasattr(self.model, "__mapper_args__") and "polymorphic_identity" in self.model.__mapper_args__:
            child_statement = delete(self.model).where(self.model.id == filters.get("id"))  # type:ignore
            await self.execute(statement=child_statement)

        model = self.model.__bases__[0]
        statement = delete(model).where(model.id == filters.get("id"))  # type:ignore

        if return_object:
            statement = statement.returning(self.model)
            return await self.execute(statement=statement, action=lambda result: result.scalars().one())

        return await self.execute(statement=statement, action=lambda result: result.rowcount)


class PaginateRepositoryMixin(Generic[ModelType]):
    model: Type[ModelType]
    session: AsyncSession
    get_where_clauses: Callable
    get_join_load_options: Callable
    execute: Callable

    async def paged_list(
        self,
        *,
        join_load_list: list[Any] | None = None,
        page: int = 1,
        per_page: int = 10,
        order_by: str = "created_at",
        order_direction: OrderDirection = OrderDirection.DESC,
        join_filters: dict[str, Any] | None = None,
        **filters: Any,
    ) -> PaginatedOutput:
        statement = select(self.model)
        join_load_list = join_load_list or []

        statement = statement.options(*self.get_join_load_options(join_load_list, join_filters))
        statement = statement.where(*self.get_filters(filters))

        return await paginate(
            self, statement, page=page, per_page=per_page, order_by=order_by, order_direction=order_direction
        )

    def get_filters(self, filters: dict) -> list:
        """
        Get filters for statement

        Args:
            filters: where clauses
        """
        search: str | None = filters.pop("search", None)
        search_fields: list | None = filters.pop("search_fields", None)

        where_clauses = self.get_where_clauses(filters)

        if search and search_fields:
            where_clauses.append(or_(func.upper(field).like(f"%{search.upper()}%") for field in search_fields))

        return where_clauses
