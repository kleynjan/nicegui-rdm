"""
Tests for TortoiseStore: ORM CRUD, hydration/dehydration, join fields.
"""
from ng_rdm.models import FieldSpec
from datetime import date, datetime

import pytest
from tortoise.exceptions import FieldError
from tortoise.expressions import Q

from ng_rdm.store import TortoiseStore
from tests.conftest import Author, Book


# --- Basic CRUD ---

async def test_create_and_read():
    """Create an author and read it back"""
    store = TortoiseStore(Author)
    author = await store.create_item({"name": "Jane Austen"})

    assert author is not None
    assert author["name"] == "Jane Austen"
    assert "id" in author


async def test_read_items():
    """Read all items"""
    store = TortoiseStore(Author)
    await store.create_item({"name": "Jane Austen"})
    await store.create_item({"name": "Charles Dickens"})

    items = await store.read_items()
    assert len(items) == 2


async def test_read_items_filter():
    """Filter by field value"""
    store = TortoiseStore(Author)
    await store.create_item({"name": "Jane Austen", "email": "jane@example.com"})
    await store.create_item({"name": "Charles Dickens", "email": "charles@example.com"})

    items = await store.read_items(filter_by={"name": "Jane Austen"})
    assert len(items) == 1
    assert items[0]["name"] == "Jane Austen"


async def test_read_item_by_id():
    """Read single item by ID"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Jane Austen"})
    assert created
    found = await store.read_item_by_id(created["id"])

    assert found is not None
    assert found["name"] == "Jane Austen"


async def test_update_item():
    """Update an existing item"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Jane Austen"})
    assert created
    updated = await store.update_item(created["id"], {"name": "J. Austen"})
    assert updated is not None
    assert updated["name"] == "J. Austen"


async def test_delete_item():
    """Delete an item"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Jane Austen"})
    assert created

    await store.delete_item(created)
    items = await store.read_items()
    assert len(items) == 0


# --- Validation ---

async def test_validation_rejects_empty_name():
    """Author name validation rejects empty string"""
    store = TortoiseStore(Author)
    result = await store.create_item({"name": ""})
    assert result is None


async def test_auto_required_validators():
    """RdmModel auto-generates required validators for non-nullable CharFields"""
    specs = Author.get_all_field_specs()
    assert "name" in specs  # explicit
    # email is nullable, so should NOT have an auto-required validator
    assert "email" not in specs or any(
        v.message == "This field is required" for v in specs.get("email", FieldSpec([])).validators
    ) is False


async def test_auto_required_for_book_title():
    """Book.title should have auto or explicit required validator"""
    specs = Book.get_all_field_specs()
    assert "title" in specs


# --- Hydration/Dehydration ---

async def test_date_hydration():
    """Date fields are hydrated to string format on read"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Test Author"})
    assert author

    book_store = TortoiseStore(Book)
    await book_store.create_item({
        "title": "Test Book",
        "published_date": "2024-06-15",
        "author_id": author["id"],
    })

    items = await book_store.read_items()
    assert items[0]["published_date"] == "2024-06-15"


async def test_date_dehydration_empty_string():
    """Empty string dates are dehydrated to None for DB"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Test Author"})
    assert author

    book_store = TortoiseStore(Book)
    await book_store.create_item({
        "title": "Test Book",
        "published_date": "",
        "author_id": author["id"],
    })

    items = await book_store.read_items()
    # None dates hydrate to empty string
    assert items[0]["published_date"] == ""


async def test_null_char_field_hydrated_to_empty_string():
    """Null CharField values hydrate to empty string"""
    store = TortoiseStore(Author)
    await store.create_item({"name": "Test"})
    # email is null=True, so DB has None

    items = await store.read_items()
    assert items[0]["email"] == ""


async def test_datetime_hydration():
    """DatetimeField is hydrated to local timezone string"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Test Author"})
    assert author

    book_store = TortoiseStore(Book)
    await book_store.create_item({
        "title": "Test Book",
        "author_id": author["id"],
    })

    items = await book_store.read_items()
    # created_at is auto_now_add, should be a datetime string
    assert items[0]["created_at"]  # non-empty
    assert "/" in items[0]["created_at"]  # format: YYYY-MM-DD / HH:MM:SS


# --- Join fields ---

async def test_join_fields():
    """Read with join fields brings FK-related data"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Jane Austen", "email": "jane@books.com"})
    assert author

    book_store = TortoiseStore(Book)
    await book_store.create_item({
        "title": "Pride and Prejudice",
        "author_id": author["id"],
    })

    items = await book_store.read_items(join_fields=["author__name", "author__email"])
    assert len(items) == 1
    assert items[0]["author__name"] == "Jane Austen"
    assert items[0]["author__email"] == "jane@books.com"


async def test_get_all_join_fields():
    """RdmModel.get_all_join_fields returns all possible join fields"""
    join_fields = Book.get_all_join_fields()
    assert "author__name" in join_fields
    assert "author__email" in join_fields


async def test_get_join_field_types():
    """RdmModel.get_join_field_types returns types for join fields"""
    types = Book.get_join_field_types()
    assert "author__name" in types
    assert types["author__name"] == "CharField"


# --- Derived fields with ORM ---

async def test_derived_fields_with_join():
    """Derived fields can use join field data"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Jane Austen"})
    assert author

    book_store = TortoiseStore(Book)
    book_store.set_derived_fields(
        derived_fields={
            "author_display": lambda row: f"by {row.get('author__name', '?')}"
        },
        dependencies=["author__name"],
    )
    await book_store.create_item({"title": "Emma", "author_id": author["id"]})

    items = await book_store.read_items()
    assert items[0]["author_display"] == "by Jane Austen"


async def test_derived_field_in_q_raises_value_error():
    """A derived name inside q= fails at query time; the error explains why"""
    store = TortoiseStore(Author)
    store.set_derived_fields({"display": lambda row: row["name"].upper()})

    with pytest.raises(ValueError, match="display"):
        await store.read_items(q=Q(display__icontains="x"))
    with pytest.raises(ValueError, match="display"):
        await store.read_counts(q=Q(display__icontains="x"))


async def test_bad_field_without_derived_fields_still_raises_field_error():
    """No derived fields configured → a typo'd name keeps its raw FieldError"""
    store = TortoiseStore(Author)

    with pytest.raises(FieldError):
        await store.read_items(q=Q(nosuchfield__icontains="x"))


# --- Observer with ORM ---

async def test_observer_on_orm_create():
    """Observer fires on TortoiseStore create"""
    store = TortoiseStore(Author, throttle_ms=0)
    events = []
    store.add_observer(lambda e: events.append(e))

    await store.create_item({"name": "Test"})
    assert len(events) == 1
    assert events[0].verb == "create"


async def test_observer_on_orm_update():
    """Observer fires on TortoiseStore update"""
    store = TortoiseStore(Author, throttle_ms=0)
    created = await store.create_item({"name": "Test"})
    assert created

    events = []
    store.add_observer(lambda e: events.append(e))
    await store.update_item(created["id"], {"name": "Updated"})

    assert len(events) == 1
    assert events[0].verb == "update"


async def test_observer_on_orm_delete():
    """Observer fires on TortoiseStore delete"""
    store = TortoiseStore(Author, throttle_ms=0)
    created = await store.create_item({"name": "Test"})
    assert created

    events = []
    store.add_observer(lambda e: events.append(e))
    await store.delete_item(created)

    assert len(events) == 1
    assert events[0].verb == "delete"


# --- RdmModel.values() ---

async def test_rdm_model_values():
    """RdmModel instance values() returns dict"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values()
    assert d["name"] == "Jane Austen"
    assert d["email"] == "jane@books.com"


async def test_rdm_model_values_with_selection():
    """RdmModel values() with field selection"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values("name")
    assert "name" in d
    assert "email" not in d


async def test_rdm_model_values_with_rename():
    """RdmModel values() with field renaming"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values(author_name="name")
    assert d["author_name"] == "Jane Austen"


# --- Bounded reads: limit / offset / order_by (DB-side) ---

async def test_read_items_order_by_ascending_and_descending():
    """order_by sorts DB-side, ascending and (via '-') descending"""
    store = TortoiseStore(Author)
    for name in ["Charlie", "Alice", "Bob"]:
        await store.create_item({"name": name})

    asc = await store.read_items(order_by=["name"])
    assert [a["name"] for a in asc] == ["Alice", "Bob", "Charlie"]

    desc = await store.read_items(order_by=["-name"])
    assert [a["name"] for a in desc] == ["Charlie", "Bob", "Alice"]


async def test_read_items_limit_offset_returns_correct_ordered_slice():
    """limit/offset page a stable, DB-ordered result"""
    store = TortoiseStore(Author)
    for name in ["a", "b", "c", "d", "e"]:
        await store.create_item({"name": name})

    page = await store.read_items(order_by=["name"], limit=2, offset=1)
    assert [a["name"] for a in page] == ["b", "c"]


async def test_read_items_limit_caps_after_ordering():
    """Ordering is applied before the cap, so limit returns the correct top rows"""
    store = TortoiseStore(Author)
    for name in ["z", "y", "x", "w"]:
        await store.create_item({"name": name})

    top = await store.read_items(order_by=["name"], limit=2)
    assert [a["name"] for a in top] == ["w", "x"]


# --- read_counts (DB-side) ---

async def test_read_counts_total_and_filtered():
    store = TortoiseStore(Author)
    await store.create_item({"name": "A", "email": "a@x.com"})
    await store.create_item({"name": "B", "email": "b@x.com"})

    assert await store.read_counts() == 2
    assert await store.read_counts(filter_by={"name": "A"}) == 1


async def test_read_counts_grouped():
    store = TortoiseStore(Author)
    await store.create_item({"name": "A", "email": "shared@x.com"})
    await store.create_item({"name": "B", "email": "shared@x.com"})
    await store.create_item({"name": "C", "email": "solo@x.com"})

    grouped = await store.read_counts(group_by="email")
    assert grouped == {"shared@x.com": 2, "solo@x.com": 1}


# import needed for type reference in test_auto_required_validators
