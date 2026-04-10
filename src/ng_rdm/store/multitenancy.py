# adds multitenancy to ng_rdm TortoiseStore

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from tortoise.expressions import Q

from ..models import QModel
from ..utils.logging import logger
from .base import Store
from .orm import TortoiseStore

if TYPE_CHECKING:
    from ..debug.event_log import EventLog

# set this to a list of tenant identifiers in your app
valid_tenants: list[str] = []

T = TypeVar('T', bound=QModel)


def set_valid_tenants(tenants: list[str]):
    global valid_tenants
    valid_tenants.extend(tenants)
    valid_tenants = list(set(valid_tenants))


class TenancyError(Exception):
    """Raised when tenant validation fails"""
    pass


class MultitenantTortoiseStore(TortoiseStore, Generic[T]):
    """Extends TortoiseStore with tenant scoping"""

    def __init__(self, model: type[T], tenant: str | None = None) -> None:
        super().__init__(model)
        self.tenant = tenant
        if tenant:
            self._validate_tenant(tenant)
        else:
            logger.debug(f"Creating store for {model.__name__} without tenant scope")

    def _validate_tenant(self, tenant: str) -> None:
        """Validate tenant exists"""
        if tenant not in valid_tenants:
            raise TenancyError(f'Invalid tenant: {tenant}')

    def _build_query(self, filter_by: dict | None, q: Q | None) -> Q:
        """Build query from filter_by dict and optional Q object, adding tenant scope"""
        result = super()._build_query(filter_by, q)
        # Add tenant scope if configured
        if self.tenant:
            result &= Q(tenant=self.tenant)
        return result

    async def _create_item(self, item: dict) -> dict:
        """Create item in database with tenant scope"""
        if self.tenant:
            item = {**item, "tenant": self.tenant}
        return await super()._create_item(item)

    async def _update_item(self, id: int, partial_item: dict) -> dict | None:
        """Update item in database with tenant scope validation"""
        if self.tenant:
            if item_tenant := partial_item.get('tenant'):
                if item_tenant != self.tenant:
                    raise TenancyError(f'Attempt at cross-tenant update: {item_tenant}')
            partial_item["tenant"] = self.tenant
        return await super()._update_item(id, partial_item)

    async def _delete_item(self, id: int) -> None:
        """Delete item from database with tenant scope"""
        query = Q(id=id)
        if self.tenant:
            query &= Q(tenant=self.tenant)
        await self.model.filter(query).delete()

class MultitenantStoreRegistry:
    """Registry for tenant-scoped singleton store instances."""

    def __init__(self):
        self._stores: dict[str, dict[str, Store]] = {}
        self._event_log: EventLog | None = None

    def set_event_log(self, event_log: EventLog) -> None:
        """Enable debug event logging for all stores."""
        self._event_log = event_log
        for tenant, name, store in self.get_all_stores():
            store.set_event_log(event_log, name, tenant)

    def register_store(self, tenant: str, name: str, store: Store) -> None:
        """Register a store instance for a tenant."""
        self._stores.setdefault(tenant, {})[name] = store
        if self._event_log:
            store.set_event_log(self._event_log, name, tenant)
        logger.debug(f"Registered {name} store for tenant {tenant}")

    def get_store(self, tenant: str, name: str) -> Store:
        """Get the singleton store instance for a tenant.

        Raises:
            KeyError: If no store exists for this tenant/name combination
        """
        try:
            return self._stores[tenant][name]
        except KeyError:
            raise KeyError(f"No store '{name}' found for tenant '{tenant}'")

    def get_all_stores(self) -> list[tuple[str, str, Store]]:
        """Get all registered stores as (tenant, name, store) tuples."""
        return [(t, n, s) for t, stores in self._stores.items() for n, s in stores.items()]


# Global multitenant registry instance
mt_store_registry = MultitenantStoreRegistry()
