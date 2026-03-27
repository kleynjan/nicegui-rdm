"""
TortoiseStore Example - SQLite-backed CRUD with ORM models.

This example demonstrates:
- Defining QModel subclasses with field_specs
- TortoiseStore CRUD operations
- Join fields for FK relationships
- Hydration (datetime ↔ string conversion)

Run from project root:
    python -m ng_rdm.examples.tortoise_store

Creates: store_demo.sqlite3
"""

import asyncio
from pathlib import Path
from tortoise import Tortoise, fields
from tortoise.expressions import Q
from ng_rdm.store import TortoiseStore
from ng_rdm.models import QModel, FieldSpec, Validator


# Define models
class Category(QModel):
    """Product category."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta(QModel.Meta):
        table = "category"


class Product(QModel):
    """Product with FK to Category."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    created_at = fields.DatetimeField(auto_now_add=True)
    category: fields.ForeignKeyRelation[Category] = fields.ForeignKeyField(
        "models.Category", related_name="products", source_field="category_id"
    )

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
        'price': FieldSpec(validators=[
            Validator(message="Price must be positive", validator=lambda v, _: v > 0 if v else False)
        ])
    }

    class Meta(QModel.Meta):
        table = "product"


# Database setup
DB_PATH = Path(__file__).parent / "store_demo.sqlite3"
DB_URL = f"sqlite://{DB_PATH}"


async def init_db():
    """Initialize database and create tables."""
    await Tortoise.init(
        db_url=DB_URL,
        modules={"models": [__name__]}
    )
    await Tortoise.generate_schemas()


async def seed_data():
    """Seed demo data if database is empty."""
    if await Category.all().count() > 0:
        print("Database already seeded, skipping.")
        return

    print("Seeding demo data...")

    # Create categories
    electronics = await Category.create(name="Electronics", description="Gadgets and devices")
    clothing = await Category.create(name="Clothing", description="Apparel and accessories")
    await Category.create(name="Books", description="Reading materials")

    # Create products
    await Product.create(name="Laptop", price=999.99, category=electronics)
    await Product.create(name="Headphones", price=149.99, category=electronics)
    await Product.create(name="T-Shirt", price=29.99, category=clothing)

    print("  Created 3 categories and 3 products")


async def main():
    print("=== TortoiseStore Example ===\n")

    # Initialize database
    print(f"Database: {DB_PATH}")
    await init_db()
    await seed_data()

    # Create stores
    category_store = TortoiseStore(Category)
    product_store = TortoiseStore(Product)

    print(f"\nField specs auto-generated: {list(category_store.field_specs.keys())}")

    # READ - basic
    print("\n--- READ Categories ---")
    categories = await category_store.read_items()
    for cat in categories:
        print(f"  {cat['id']}: {cat['name']} - {cat['description']}")

    print("\n--- READ Products ---")
    products = await product_store.read_items()
    for prod in products:
        print(f"  {prod['id']}: {prod['name']} @ ${prod['price']} (created: {prod['created_at']})")

    # READ with JOIN FIELDS
    print("\n--- Products with Category (join_fields) ---")
    join_fields = ['category__name', 'category__description']
    products_with_cat = await product_store.read_items(join_fields=join_fields)
    for prod in products_with_cat:
        print(f"  {prod['name']} in '{prod['category__name']}'")

    # READ with FILTER
    print("\n--- Filter by price > 100 ---")
    expensive = await product_store._read_items(q=Q(price__gt=100))
    for prod in expensive:
        print(f"  {prod['name']} @ ${prod['price']}")

    # CREATE
    print("\n--- CREATE ---")
    new_cat = await category_store.create_item({'name': 'Sports', 'description': 'Athletic gear'})
    print(f"Created category: {new_cat}")

    # UPDATE
    print("\n--- UPDATE ---")
    if new_cat:
        updated = await category_store.update_item(new_cat['id'], {'description': 'Sports and fitness equipment'})
        print(f"Updated: {updated}")

    # DERIVED FIELDS
    print("\n--- Derived Fields ---")
    product_store.set_derived_fields(
        derived_fields={
            'display_name': lambda row: f"{row.get('name', '')} (${row.get('price', 0)})"
        }
    )
    products = await product_store.read_items()
    for prod in products:
        print(f"  {prod.get('display_name')}")

    # DELETE
    print("\n--- DELETE ---")
    if new_cat:
        await category_store.delete_item(new_cat)
        print(f"Deleted category {new_cat['id']}")

    remaining = await category_store.read_items()
    print(f"Remaining categories: {len(remaining)}")

    # Cleanup
    await Tortoise.close_connections()
    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
