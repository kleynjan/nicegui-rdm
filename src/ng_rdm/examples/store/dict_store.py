"""
DictStore Example - In-memory CRUD with validation and observers.

This example demonstrates:
- Creating a DictStore with field validation
- CRUD operations (Create, Read, Update, Delete)
- Observer pattern for reactive updates
- Field normalization

Run from project root:
    python -m ng_rdm.examples.store.dict_store
"""

import asyncio
from ng_rdm.models import FieldSpec, Validator
from ng_rdm.store import DictStore


# Define validators
name_validator = Validator(
    message="Name must not be empty",
    validator=lambda v, _: bool(v and v.strip())
)

email_validator = Validator(
    message="Must be valid email format",
    validator=lambda v, _: '@' in v if v else True
)

# Normalizer: trim whitespace
def trim_normalizer(v): return v.strip() if isinstance(v, str) else v


async def main():
    print("=== DictStore Example ===\n")

    # Create store with field specs
    store = DictStore(field_specs={
        'name': FieldSpec(validators=[name_validator], normalizer=trim_normalizer),
        'email': FieldSpec(validators=[email_validator], normalizer=trim_normalizer),
    })

    # Add observer to track changes
    def on_change(event):
        print(f"  [Observer] {event.verb}: {event.item}")

    store.add_observer(on_change)
    print(f"Observer registered (count: {store.observer_count})\n")

    # CREATE
    print("--- CREATE ---")
    item1 = await store.create_item({'name': '  Alice Smith  ', 'email': 'alice@example.com', 'age': 28})
    assert item1
    print(f"Created: {item1}")

    item2 = await store.create_item({'name': 'Bob Jones', 'email': 'bob@example.com', 'age': 35})
    assert item2
    print(f"Created: {item2}")

    # Try creating with invalid data
    print("\nTrying to create with empty name...")
    bad_item = await store.create_item({'name': '   ', 'email': 'bad@example.com'})
    print(f"Result: {bad_item}")  # Should be None

    print("\nTrying to create with invalid email...")
    bad_item = await store.create_item({'name': 'Bad User', 'email': 'not-an-email'})
    print(f"Result: {bad_item}")  # Should be None

    # READ
    print("\n--- READ ---")
    all_items = await store.read_items()
    print(f"All items: {all_items}")

    filtered = await store.read_items(filter_by={'name': 'Alice Smith'})
    print(f"Filtered by name='Alice Smith': {filtered}")

    by_id = await store.read_item_by_id(0)
    print(f"By ID 0: {by_id}")

    # UPDATE
    print("\n--- UPDATE ---")
    updated = await store.update_item(0, {'age': 29})
    print(f"Updated age: {updated}")

    # Try invalid update
    print("\nTrying to update with empty name...")
    bad_update = await store.update_item(0, {'name': ''})
    print(f"Result: {bad_update}")  # Should be None

    # DELETE
    print("\n--- DELETE ---")
    await store.delete_item(item2)
    print("Deleted item2")

    remaining = await store.read_items()
    print(f"Remaining items: {remaining}")

    # SORTING
    print("\n--- SORTING ---")
    await store.create_item({'name': 'Carol White', 'email': 'carol@example.com', 'age': 42})
    await store.create_item({'name': 'Dave Brown', 'email': 'dave@example.com', 'age': 25})

    store.set_sort_key(lambda item: item.get('age', 0))
    sorted_items = await store.read_items()
    names_ages = [f"{i['name']}({i['age']})" for i in sorted_items]
    print(f"Sorted by age (asc): {names_ages}")

    store.set_sort_key(lambda item: item.get('name', ''))
    sorted_items = await store.read_items()
    names = [i['name'] for i in sorted_items]
    print(f"Sorted by name: {names}")

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
