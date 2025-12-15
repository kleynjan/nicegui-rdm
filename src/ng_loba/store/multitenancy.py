# stores/tortoise.py
# adds multitenancy to ng_loba TortoiseStore

from typing import Generic, TypeVar

from tortoise.expressions import Q

from ..models import QModel
from ..utils.logging import logger
from .orm import TortoiseStore

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


class StoreRegistry:
    """Registry for tenant-scoped singleton store instances"""

    def __init__(self):
        self._stores = {}

    def register_store(self, tenant: str, name: str, store: MultitenantTortoiseStore) -> None:
        """Register a store instance for a tenant.

        Args:
            tenant: The tenant identifier
            name: Unique name for this store type
            store: The store instance to register
        """
        if tenant not in self._stores:
            self._stores[tenant] = {}
        self._stores[tenant][name] = store
        logger.info(f"Registered {name} store for tenant {tenant}")

    def get_store(self, tenant: str, name: str) -> MultitenantTortoiseStore:
        """Get the singleton store instance for a tenant.

        Args:
            tenant: The tenant identifier
            name: The store type name

        Returns:
            The singleton store instance for this tenant

        Raises:
            KeyError: If no store exists for this tenant/name combination
        """
        try:
            return self._stores[tenant][name]
        except KeyError:
            raise TenancyError(f"No store '{name}' found for tenant '{tenant}'")

# Global registry instance
store_registry = StoreRegistry()
