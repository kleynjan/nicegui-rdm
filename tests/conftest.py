# pyright: reportUnusedImport=false
"""
Shared pytest fixtures for ng_rdm tests.
"""
from ng_rdm.models import RdmModel, MultitenantRdmModel
from tortoise import fields
from ng_rdm.models import FieldSpec, Validator
from ng_rdm.store import DictStore, StoreRegistry, MultitenantStoreRegistry
import pytest
from tortoise import Tortoise

pytest_plugins = ['nicegui.testing.user_plugin']


# --- Test models for ORM tests ---


class Author(RdmModel):
    """Test model: Author"""
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=200, null=True)

    field_specs = {
        "name": FieldSpec(validators=[
            Validator("Name must not be empty", lambda v, _: bool(v and str(v).strip())),
        ]),
    }

    class Meta(RdmModel.Meta):
        table = "author"


class Book(RdmModel):
    """Test model: Book with FK to Author"""
    title = fields.CharField(max_length=200)
    year = fields.IntField(null=True)
    published_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    author = fields.ForeignKeyField("models.Author", related_name="books")

    field_specs = {
        "title": FieldSpec(validators=[
            Validator("Title must not be empty", lambda v, _: bool(v and str(v).strip())),
        ]),
    }

    class Meta(RdmModel.Meta):
        table = "book"


class TenantItem(MultitenantRdmModel):
    """Test model with tenant field for multitenancy tests"""
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)

    class Meta(RdmModel.Meta):
        table = "tenant_item"


# --- Fixtures ---

@pytest.fixture(autouse=True)
async def reset_database():
    """Reset database before each test using in-memory SQLite"""
    await Tortoise.init(
        db_url='sqlite://:memory:',
        modules={"models": ["tests.conftest"]}
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
def dict_store():
    """A fresh DictStore instance"""
    return DictStore()


@pytest.fixture
def validated_store():
    """DictStore with field_specs for validation testing"""
    return DictStore(field_specs={
        "name": FieldSpec(validators=[
            Validator("Name is required", lambda v, _: bool(v and str(v).strip())),
        ]),
        "email": FieldSpec(
            validators=[
                Validator("Email must contain @", lambda v, _: "@" in str(v)),
            ],
            normalizer=lambda v: str(v).strip().lower(),
        ),
    })


@pytest.fixture
def registry():
    """A fresh StoreRegistry (flat)"""
    return StoreRegistry()


@pytest.fixture
def mt_registry():
    """A fresh MultitenantStoreRegistry"""
    return MultitenantStoreRegistry()
