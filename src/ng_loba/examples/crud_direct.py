"""
Example of DirectEditTable - inline editing with auto-save on blur.
"""

from nicegui import ui
from ng_loba.store import DictStore
from ng_loba.models import Validator, FieldSpec
from ng_loba.crud import create_crud_table, Column, TableConfig


@ui.page('/')
async def main():
    # Define field validation
    name_validator = Validator(
        message="Name must not be empty",
        validator=lambda v, _: bool(v.strip())
    )

    email_validator = Validator(
        message="Must be valid email",
        validator=lambda v, _: '@' in v if v else True
    )

    # Create store with validation
    store = DictStore({
        'name': FieldSpec(validators=[name_validator]),
        'email': FieldSpec(validators=[email_validator])
    })

    # Define table configuration for direct edit mode
    config = TableConfig(
        columns=[
            Column(name='name', label='Name', ui_type=ui.input),
            Column(name='email', label='Email', ui_type=ui.input),
            Column(name='age', label='Age', ui_type=ui.number, default_value=0),
        ],
        mode='direct',  # Direct edit mode
        add_button='Add User',
    )

    # Create table using factory
    table = create_crud_table(
        state={},
        data_source=store,
        config=config
    )

    ui.add_head_html("""
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    """)

    # Load styles
    import os
    styles_path = os.path.join(os.path.dirname(__file__), 'crud.scss')
    with open(styles_path) as f:
        ui.add_scss(f.read())

    # Add some sample data
    await store.create_item({'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 28})
    await store.create_item({'name': 'Bob Jones', 'email': 'bob@example.com', 'age': 35})
    await store.create_item({'name': 'Carol White', 'email': 'carol@example.com', 'age': 42})

    with ui.card().classes('w-full'):
        ui.label('Direct Edit Mode Demo').classes('text-h5')
        ui.label('All rows are editable. Changes save automatically on blur.').classes('text-caption')
        await table.build()   # type: ignore


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(show=False)
