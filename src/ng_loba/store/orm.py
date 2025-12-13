"""
ORM-specific store implementation using Tortoise ORM.
"""

from typing import Generic, Type, TypeVar

from tortoise.contrib.fastapi import register_tortoise
from tortoise.expressions import Q

from ..models import QModel
from ..utils.logging import logger
from ..utils.helpers import str_to_utc_datetime, utc_datetime_to_str

from .base import Store

T = TypeVar('T', bound=QModel)

def init_db(app, db_url: str, modules: dict[str, list[str]]):
    """Initialize Tortoise ORM with FastAPI"""
    register_tortoise(
        app,
        db_url=db_url,
        modules=modules,  # type:ignore # eg, {"models": ["models"]}
        generate_schemas=False,  # in production you should use version control migrations instead
    )


class TortoiseStore(Store, Generic[T]):
    """Tortoise ORM implementation of Store (without multitenancy)"""

    hydration_mapping = {
        "DatetimeField": {
            "hydrate": utc_datetime_to_str,
            "dehydrate": str_to_utc_datetime,
        },
    }

    def __init__(self, model: Type[T]) -> None:
        self.model = model
        super().__init__(getattr(model, 'field_specs', {}))  # set up validators & normalizers
        logger.debug(f"Creating store for {model.__name__}")

    # metamodel methods
    def _get_field_names(self, join_fields: list[str] = []) -> list[str]:
        """Get field names for model"""
        return self.model.get_field_names(join_fields=join_fields)

    def _get_field_types(self) -> list[dict[str, str]]:
        """Get field names -> types for model [{'tenant': 'CharField', 'name': 'DatetimeField'...}...]"""
        return self.model.get_field_types()

    # hydrate/dehydrate methods
    def _hydrate(self, item: dict) -> dict:
        """Convert DB types to API types"""
        result = item.copy()
        for f in self._get_field_types():
            for name, type_ in f.items():
                if type_ in self.hydration_mapping and name in result and result[name]:
                    result[name] = self.hydration_mapping[type_]["hydrate"](result[name])
        return result

    def _dehydrate(self, item: dict) -> dict:
        """Convert API types to DB types"""
        result = item.copy()
        for f in self._get_field_types():
            for name, type_ in f.items():
                if type_ in self.hydration_mapping and name in result and result[name]:
                    result[name] = self.hydration_mapping[type_]["dehydrate"](result[name])
        return result

    def _build_query(self, filter_by: dict | None, q: Q | None) -> Q:
        """Build query from filter_by dict and optional Q object"""
        result = q or Q()
        if filter_by:
            # Convert dict to Q objects for equality comparison
            filter_q = Q()
            for field, value in filter_by.items():
                filter_q &= Q(**{field: value})
            result &= filter_q
        return result

    async def _create_item(self, item: dict) -> dict:
        """Create item in database"""
        item = self._dehydrate(item)
        db_item = await self.model.create(**item)
        return self._hydrate(db_item.values())

    async def _read_items(self, filter_by: dict | None = None, q: Q | None = None, join_fields: list[str] = []) -> list[dict]:
        """Read items from database with optional filtering"""
        fields = self._get_field_names(join_fields=join_fields)
        query = self._build_query(filter_by, q)
        items = await self.model.filter(query).values(*fields)
        items = [self._hydrate(item) for item in items]
        return items

    async def _update_item(self, id: int, partial_item: dict) -> dict | None:
        """Update item in database"""
        partial_item = {k: v for k, v in partial_item.items() if k != 'id'}
        partial_item = self._dehydrate(partial_item)
        await self.model.filter(id=id).update(**partial_item)
        items = await self._read_items(filter_by={"id": id})
        return items[0] if items else None

    async def _delete_item(self, id: int) -> None:
        """Delete item from database"""
        query = Q(id=id)
        await self.model.filter(query).delete()

    async def read_item_by_id(self, id: int, join_fields: list[str] = []) -> dict | None:
        """Read single item by ID"""
        items = await self._read_items(filter_by={"id": id}, join_fields=join_fields)
        return items[0] if items else None
