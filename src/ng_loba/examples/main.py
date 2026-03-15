"""
Comprehensive CRUD demo showing all three table modes side-by-side.

This example demonstrates:
- Modal mode: Table view with modal dialog for editing
- Direct mode: Inline editing with auto-save on blur
- Explicit mode: Row selection with dedicated edit mode

All three tables share the same data store, so changes in one table
are immediately reflected in the others.

Run from project root:
    python -m ng_loba.examples.main
"""

from nicegui import ui
from ng_loba.store import DictStore
from ng_loba.models import Validator, FieldSpec
from ng_loba.crud import create_crud_table, Column, TableConfig, page_init


# Field validators
name_validator = Validator(
    message="Name must not be empty",
    validator=lambda v, _: bool(v.strip())
)

email_validator = Validator(
    message="Must be valid email",
    validator=lambda v, _: '@' in v if v else True
)


@ui.page('/')
async def main():
    """Main page showing all three CRUD modes."""
    page_init()

    ui.label('CRUD Table Modes Comparison').classes('text-h4')
    ui.label('Compare the three different editing modes available in ng_loba.crud').classes('text-subtitle1')
    ui.label('All tables share the same data - changes in one are reflected in all others').classes('text-caption')

    # Create a single shared store with validation
    shared_store = DictStore({
        'name': FieldSpec(validators=[name_validator]),
        'email': FieldSpec(validators=[email_validator])
    })

    # Add sample data
    await shared_store.create_item({'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 28})
    await shared_store.create_item({'name': 'Bob Jones', 'email': 'bob@example.com', 'age': 35})
    await shared_store.create_item({'name': 'Carol White', 'email': 'carol@example.com', 'age': 42})

    ui.separator()

    # ==================== MODAL MODE ====================
    ui.label('Modal Mode').classes('text-h5')
    ui.label('Read-only table view with modal dialog for add/edit operations').classes('text-caption')

    config_modal = TableConfig(
        table_columns=[
            Column(name='name', label='Name', width_percent=35),
            Column(name='email', label='Email', width_percent=35),
            Column(name='age', label='Age', width_percent=20),
        ],
        dialog_columns=[
            Column(name='name', label='Name', placeholder='Enter full name'),
            Column(name='email', label='Email', placeholder='user@example.com'),
            Column(name='age', label='Age', ui_type=ui.number, default_value=0),
        ],
        mode='modal',
        add_button='New User...',
        dialog_title_add='Add New User',
        dialog_title_edit='Edit User',
    )

    table_modal = create_crud_table(
        state={},
        data_source=shared_store,
        config=config_modal
    )

    with ui.card().classes('w-full'):
        await table_modal.build()  # type: ignore
        with ui.row().classes('q-mt-md'):
            table_modal.render_add_button()  # type: ignore

    ui.separator()

    # ==================== DIRECT MODE ====================
    ui.label('Direct Mode').classes('text-h5')
    ui.label('All rows are editable. Changes save automatically on blur.').classes('text-caption')

    config_direct = TableConfig(
        columns=[
            Column(name='name', label='Name', ui_type=ui.input, width_percent=35),
            Column(name='email', label='Email', ui_type=ui.input, width_percent=35),
            Column(name='age', label='Age', ui_type=ui.number, default_value=0, width_percent=20),
        ],
        mode='direct',
        add_button='Add User',
    )

    table_direct = create_crud_table(
        state={},
        data_source=shared_store,
        config=config_direct
    )

    with ui.card().classes('w-full'):
        await table_direct.build()  # type: ignore

    ui.separator()

    # ==================== EXPLICIT MODE ====================
    ui.label('Explicit Mode').classes('text-h5')
    ui.label('Click to select, double-click or use edit button to edit. Arrow keys for navigation.').classes('text-caption')

    config_explicit = TableConfig(
        columns=[
            Column(name='name', label='Name', ui_type=ui.input, width_percent=35),
            Column(name='email', label='Email', ui_type=ui.input, width_percent=35),
            Column(name='age', label='Age', ui_type=ui.number, default_value=0, width_percent=20),
        ],
        mode='explicit',
        focus_column='name',
        add_button='Add User',
        delete_confirmation=True,
    )

    table_explicit = create_crud_table(
        state={},
        data_source=shared_store,
        config=config_explicit
    )

    with ui.card().classes('w-full'):
        await table_explicit.build()  # type: ignore

ui.run()
