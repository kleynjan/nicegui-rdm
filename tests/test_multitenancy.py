"""
Tests for MultitenantTortoiseStore: tenant scoping and isolation.
"""
import pytest
from ng_rdm.store import MultitenantTortoiseStore, TenancyError
from ng_rdm.store.multitenancy import set_valid_tenants, valid_tenants
from tests.conftest import TenantItem


@pytest.fixture(autouse=True)
def setup_tenants():
    """Register test tenants before each test"""
    # Clear and set fresh
    valid_tenants.clear()
    set_valid_tenants(["alpha", "beta"])
    yield
    valid_tenants.clear()


async def test_create_with_tenant():
    """Created item automatically gets tenant field"""
    store = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    item = await store.create_item({"name": "Item A"})

    assert item is not None
    assert item["tenant"] == "alpha"


async def test_tenant_isolation():
    """Each tenant only sees its own items"""
    store_alpha = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    store_beta = MultitenantTortoiseStore(TenantItem, tenant="beta")

    await store_alpha.create_item({"name": "Alpha Item"})
    await store_beta.create_item({"name": "Beta Item"})

    alpha_items = await store_alpha.read_items()
    beta_items = await store_beta.read_items()

    assert len(alpha_items) == 1
    assert alpha_items[0]["name"] == "Alpha Item"
    assert len(beta_items) == 1
    assert beta_items[0]["name"] == "Beta Item"


async def test_invalid_tenant_raises():
    """Creating store with invalid tenant raises TenancyError"""
    with pytest.raises(TenancyError, match="Invalid tenant"):
        MultitenantTortoiseStore(TenantItem, tenant="nonexistent")


async def test_cross_tenant_update_raises():
    """Updating with a different tenant raises TenancyError"""
    store = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    item = await store.create_item({"name": "Item A"})

    assert item
    with pytest.raises(TenancyError, match="cross-tenant"):
        await store.update_item(item["id"], {"tenant": "beta", "name": "Hacked"})


async def test_update_within_tenant():
    """Update within same tenant succeeds"""
    store = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    item = await store.create_item({"name": "Original"})

    assert item
    updated = await store.update_item(item["id"], {"name": "Updated"})
    assert updated is not None
    assert updated["name"] == "Updated"
    assert updated["tenant"] == "alpha"


async def test_delete_scoped_to_tenant():
    """Delete only removes within tenant scope"""
    store_alpha = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    store_beta = MultitenantTortoiseStore(TenantItem, tenant="beta")

    alpha_item = await store_alpha.create_item({"name": "Alpha"})
    await store_beta.create_item({"name": "Beta"})

    assert alpha_item
    # Delete alpha item
    await store_alpha.delete_item(alpha_item)

    assert len(await store_alpha.read_items()) == 0
    assert len(await store_beta.read_items()) == 1  # beta untouched


async def test_store_without_tenant():
    """Store without tenant sees all items (no scoping)"""
    scoped = MultitenantTortoiseStore(TenantItem, tenant="alpha")
    await scoped.create_item({"name": "Alpha Item"})

    unscoped = MultitenantTortoiseStore(TenantItem, tenant=None)
    # Manually create in beta
    await TenantItem.create(tenant="beta", name="Beta Item")

    all_items = await unscoped.read_items()
    assert len(all_items) == 2


async def test_set_valid_tenants_deduplicates():
    """set_valid_tenants deduplicates entries"""
    import ng_rdm.store.multitenancy as mt
    mt.valid_tenants.clear()
    set_valid_tenants(["a", "b", "a"])
    assert len(mt.valid_tenants) == 2
    assert set(mt.valid_tenants) == {"a", "b"}
