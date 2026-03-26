"""
MultitenantTortoiseStore Example - Tenant-scoped CRUD operations.

This example demonstrates:
- Setting up valid tenants
- Tenant-scoped store operations
- Cross-tenant isolation
- TenancyError protection

Run from project root:
    python -m ng_rdm.examples.store.multitenancy

Creates: mt_demo.sqlite3
"""

import asyncio
from pathlib import Path
from tortoise import Tortoise, fields
from ng_rdm.store.multitenancy import set_valid_tenants
from ng_rdm.store import MultitenantTortoiseStore, TenancyError
from ng_rdm.models import QModel, FieldSpec, Validator


# Define model with tenant field
class Task(QModel):
    """Task belonging to a tenant."""
    id = fields.IntField(pk=True)
    tenant = fields.CharField(max_length=50)
    title = fields.CharField(max_length=200)
    status = fields.CharField(max_length=20, default="pending")
    priority = fields.IntField(default=1)

    field_specs = {
        'title': FieldSpec(validators=[
            Validator(message="Title is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(QModel.Meta):
        table = "task"


# Database setup
DB_PATH = Path(__file__).parent / "mt_demo.sqlite3"
DB_URL = f"sqlite://{DB_PATH}"


async def init_db():
    """Initialize database and create tables."""
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": [__name__]}
    )
    await Tortoise.generate_schemas()


async def seed_data():
    """Seed demo data for two tenants."""
    if await Task.all().count() > 0:
        print("Database already seeded, skipping.")
        return

    print("Seeding demo data...")

    # Tenant A tasks
    await Task.create(tenant="tenant_a", title="Review budget", status="done", priority=2)
    await Task.create(tenant="tenant_a", title="Update website", status="pending", priority=1)
    await Task.create(tenant="tenant_a", title="Call client", status="in_progress", priority=3)

    # Tenant B tasks
    await Task.create(tenant="tenant_b", title="Ship order #123", status="pending", priority=2)
    await Task.create(tenant="tenant_b", title="Restock inventory", status="pending", priority=1)
    await Task.create(tenant="tenant_b", title="Pay invoice", status="done", priority=3)

    print("  Created 3 tasks for tenant_a and 3 for tenant_b")


async def main():
    print("=== MultitenantTortoiseStore Example ===\n")

    # Initialize database
    print(f"Database: {DB_PATH}")
    await init_db()
    await seed_data()

    # Register valid tenants
    set_valid_tenants(["tenant_a", "tenant_b"])
    print("Registered tenants: tenant_a, tenant_b\n")

    # Create tenant-scoped stores
    store_a = MultitenantTortoiseStore(Task, tenant="tenant_a")
    store_b = MultitenantTortoiseStore(Task, tenant="tenant_b")

    # ISOLATION: Each store only sees its own tenant's data
    print("--- TENANT ISOLATION ---")
    tasks_a = await store_a.read_items()
    tasks_b = await store_b.read_items()
    print(f"Tenant A sees {len(tasks_a)} tasks: {[t['title'] for t in tasks_a]}")
    print(f"Tenant B sees {len(tasks_b)} tasks: {[t['title'] for t in tasks_b]}")

    # CREATE: New items automatically get tenant assigned
    print("\n--- CREATE (auto-tenant) ---")
    new_task = await store_a.create_item({'title': 'New A task', 'status': 'pending'})
    if new_task:
        print(f"Created in tenant_a: {new_task}")
        print(f"  tenant field auto-set: '{new_task.get('tenant')}'")

    # UPDATE: Can only update own tenant's items
    print("\n--- UPDATE (tenant-scoped) ---")
    if new_task:
        updated = await store_a.update_item(new_task['id'], {'status': 'in_progress'})
        print(f"Updated: {updated}")

    # CROSS-TENANT PROTECTION
    print("\n--- CROSS-TENANT PROTECTION ---")

    # Try creating with wrong tenant
    print("Trying to create with explicit wrong tenant...")
    try:
        # The store will override with its own tenant, so this is safe
        bad_task = await store_a.create_item({'title': 'Evil task', 'tenant': 'tenant_b'})
        if bad_task:
            print(f"  Created (tenant was overridden): tenant={bad_task.get('tenant')}")
    except TenancyError as e:
        print(f"  TenancyError: {e}")

    # Try invalid tenant
    print("\nTrying to create store with invalid tenant...")
    try:
        MultitenantTortoiseStore(Task, tenant="invalid_tenant")
        print("  Created store (shouldn't happen)")
    except TenancyError as e:
        print(f"  TenancyError: {e}")

    # DELETE: Can only delete own tenant's items
    print("\n--- DELETE (tenant-scoped) ---")
    if new_task:
        await store_a.delete_item(new_task)
        print(f"Deleted task {new_task['id']} from tenant_a")

    # Verify isolation maintained
    print("\n--- FINAL STATE ---")
    tasks_a = await store_a.read_items()
    tasks_b = await store_b.read_items()
    print(f"Tenant A: {len(tasks_a)} tasks")
    print(f"Tenant B: {len(tasks_b)} tasks")

    # Cleanup
    await Tortoise.close_connections()
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
