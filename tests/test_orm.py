"""
Tests for TortoiseStore: ORM CRUD, hydration/dehydration, join fields.
"""
from ng_rdm.models import FieldSpec
from datetime import date, datetime

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
    found = await store.read_item_by_id(created["id"])

    assert found is not None
    assert found["name"] == "Jane Austen"


async def test_update_item():
    """Update an existing item"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Jane Austen"})

    updated = await store.update_item(created["id"], {"name": "J. Austen"})
    assert updated is not None
    assert updated["name"] == "J. Austen"


async def test_delete_item():
    """Delete an item"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Jane Austen"})

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
    """QModel auto-generates required validators for non-nullable CharFields"""
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

    book_store = TortoiseStore(Book)
    book = await book_store.create_item({
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

    book_store = TortoiseStore(Book)
    book = await book_store.create_item({
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
    author = await store.create_item({"name": "Test"})
    # email is null=True, so DB has None

    items = await store.read_items()
    assert items[0]["email"] == ""


async def test_datetime_hydration():
    """DatetimeField is hydrated to local timezone string"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Test Author"})

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
    """QModel.get_all_join_fields returns all possible join fields"""
    join_fields = Book.get_all_join_fields()
    assert "author__name" in join_fields
    assert "author__email" in join_fields


async def test_get_join_field_types():
    """QModel.get_join_field_types returns types for join fields"""
    types = Book.get_join_field_types()
    assert "author__name" in types
    assert types["author__name"] == "CharField"


# --- Derived fields with ORM ---

async def test_derived_fields_with_join():
    """Derived fields can use join field data"""
    author_store = TortoiseStore(Author)
    author = await author_store.create_item({"name": "Jane Austen"})

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


# --- Observer with ORM ---

async def test_observer_on_orm_create():
    """Observer fires on TortoiseStore create"""
    store = TortoiseStore(Author)
    events = []
    store.add_observer(lambda e: events.append(e))

    await store.create_item({"name": "Test"})
    assert len(events) == 1
    assert events[0].verb == "create"


async def test_observer_on_orm_update():
    """Observer fires on TortoiseStore update"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Test"})

    events = []
    store.add_observer(lambda e: events.append(e))
    await store.update_item(created["id"], {"name": "Updated"})

    assert len(events) == 1
    assert events[0].verb == "update"


async def test_observer_on_orm_delete():
    """Observer fires on TortoiseStore delete"""
    store = TortoiseStore(Author)
    created = await store.create_item({"name": "Test"})

    events = []
    store.add_observer(lambda e: events.append(e))
    await store.delete_item(created)

    assert len(events) == 1
    assert events[0].verb == "delete"


# --- QModel.values() ---

async def test_qmodel_values():
    """QModel instance values() returns dict"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values()
    assert d["name"] == "Jane Austen"
    assert d["email"] == "jane@books.com"


async def test_qmodel_values_with_selection():
    """QModel values() with field selection"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values("name")
    assert "name" in d
    assert "email" not in d


async def test_qmodel_values_with_rename():
    """QModel values() with field renaming"""
    author = await Author.create(name="Jane Austen", email="jane@books.com")
    d = author.values(author_name="name")
    assert d["author_name"] == "Jane Austen"


# import needed for type reference in test_auto_required_validators
