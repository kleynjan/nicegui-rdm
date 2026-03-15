"""
Hierarchical Org/Employee demo with ViewStack, SelectTable, and DetailCard.

This example demonstrates:
- SQLite database with Tortoise ORM
- Hierarchical data: Organizations contain Employees
- ViewStack for list → detail → edit navigation
- TortoiseStore for ORM-backed CRUD operations
- Join fields for FK relationships

Run from project root:
    python -m ng_loba.examples.org_demo

or directly in examples directory:
    python org_demo.py
"""

from pathlib import Path

from nicegui import app, ui
from tortoise import fields

from ng_loba.models import QModel, FieldSpec, Validator
from ng_loba.store import TortoiseStore
from ng_loba.store.orm import init_db, close_db
from ng_loba.crud import Column, TableConfig, ViewStack, page_init


# ── Models ──

class Org(QModel):
    """Organization model."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ])
    }

    class Meta:
        table = "org"


class Emp(QModel):
    """Employee model with FK to Organization."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, null=True)
    role = fields.CharField(max_length=50, null=True)
    org: fields.ForeignKeyRelation[Org] = fields.ForeignKeyField(
        "models.Org", related_name="employees", source_field="org_id"
    )

    field_specs = {
        'name': FieldSpec(validators=[
            Validator(message="Name is required", validator=lambda v, _: bool(v and v.strip()))
        ]),
        'email': FieldSpec(validators=[
            Validator(message="Invalid email", validator=lambda v, _: '@' in v if v else True)
        ])
    }

    class Meta:
        table = "emp"


# ── Database Setup ──

DB_PATH = Path(__file__).parent / "org_demo.sqlite3"
DB_URL = f"sqlite://{DB_PATH}"


async def seed_data():
    """Seed fictional data if database is empty."""
    if await Org.all().count() > 0:
        return

    # Create organizations
    acme = await Org.create(name="Acme Corp", description="Global manufacturing and innovation")
    techstart = await Org.create(name="TechStart Inc", description="Cutting-edge software startup")
    green = await Org.create(name="Green Energy Ltd", description="Renewable energy solutions")

    # Create employees
    await Emp.create(name="Alice Smith", email="alice@acme.com", role="CEO", org=acme)
    await Emp.create(name="Bob Jones", email="bob@acme.com", role="Engineer", org=acme)
    await Emp.create(name="Carol White", email="carol@techstart.io", role="CTO", org=techstart)
    await Emp.create(name="Dave Brown", email="dave@techstart.io", role="Developer", org=techstart)
    await Emp.create(name="Eve Davis", email="eve@techstart.io", role="Developer", org=techstart)
    await Emp.create(name="Frank Miller", email="frank@greenenergy.com", role="CEO", org=green)
    await Emp.create(name="Grace Lee", email="grace@greenenergy.com", role="Engineer", org=green)


# ── Initialize Database ──

# Register Tortoise with NiceGUI's app (before ui.run)
init_db(app, DB_URL, modules={"models": [__name__]}, generate_schemas=True)
app.on_shutdown(close_db)

# Create stores (Tortoise will be initialized by the time pages load)
org_store = TortoiseStore(Org)
emp_store = TortoiseStore(Emp)


@app.on_startup
async def seed():
    """Seed data on first startup."""
    await seed_data()


# ── UI Configuration ──

org_select_config = TableConfig(
    columns=[
        Column(name='name', label='Organization', width_percent=40),
        Column(name='description', label='Description', width_percent=50),
    ],
    add_button='New Organization',
)

org_detail_config = TableConfig(
    columns=[
        Column(name='name', label='Name'),
        Column(name='description', label='Description', ui_type=ui.textarea),
    ],
)

emp_table_config = TableConfig(
    columns=[
        Column(name='name', label='Name', width_percent=30),
        Column(name='email', label='Email', width_percent=30),
        Column(name='role', label='Role', width_percent=30),
    ],
    empty_message="No employees in this organization",
)


# ── Detail Renderer ──

async def render_org_detail(item: dict):
    """Render organization detail view with employee list."""
    ui.label(item.get('name', '')).classes('text-h5')
    ui.label(item.get('description', '') or 'No description').classes('text-body1 text-grey')

    ui.separator().classes('q-my-md')
    ui.label('Employees').classes('text-h6')

    # Get employees for this org
    org_id = item.get('id')
    if org_id and emp_store:
        employees = await emp_store.read_items(filter_by={'org_id': org_id})
        if employees:
            with ui.element('div').classes('employee-list'):
                for emp in employees:
                    with ui.row().classes('employee-row items-center gap-4'):
                        ui.label(emp.get('name', '')).classes('text-weight-medium')
                        ui.label(emp.get('role', '')).classes('text-grey')
                        ui.label(emp.get('email', '')).classes('text-caption text-grey-6')
        else:
            ui.label('No employees yet').classes('text-grey')


# ── Page ──

@ui.page('/')
async def main():
    """Main page with org ViewStack."""
    page_init()

    ui.label('Organization & Employee Demo').classes('text-h4')
    ui.label('ViewStack navigation: list → detail → edit').classes('text-subtitle1')

    ui.separator()

    # ViewStack for organizations
    stack = ViewStack(
        data_source=org_store,
        select_config=org_select_config,
        detail_config=org_detail_config,
        render_detail=render_org_detail,
        breadcrumb_root="Organizations",
        item_label=lambda item: item.get("name", ""),
        show_add=True,
        show_edit=True,
        show_delete=True,
    )

    with ui.card().classes('w-full'):
        await stack.build()     # type: ignore


ui.run(title="Org Demo")
