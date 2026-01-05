"""
Example of ExplicitEditTable - row selection with dedicated edit mode.
"""

from nicegui import ui
from ng_loba.store import DictStore
from ng_loba.models import Validator, FieldSpec
from ng_loba.crud import create_crud_table, Column, TableConfig, get_crud_css


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

    # Define table configuration for explicit edit mode
    config = TableConfig(
        columns=[
            Column(name='name', label='Name', ui_type=ui.input, width_percent=40),
            Column(name='email', label='Email', ui_type=ui.input, width_percent=40),
            Column(name='age', label='Age', ui_type=ui.number, default_value=0, width_percent=18),
        ],
        mode='explicit',  # Explicit edit mode (default)
        focus_column='name',
        add_button='Add User',
        delete_confirmation=True,
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

    ui.add_css(get_crud_css())

    # Add some sample data
    await store.create_item({'name': 'Alice Smith', 'email': 'alice@example.com', 'age': 28})
    await store.create_item({'name': 'Bob Jones', 'email': 'bob@example.com', 'age': 35})
    await store.create_item({'name': 'Carol White', 'email': 'carol@example.com', 'age': 42})

    ui.label('Explicit Edit Mode Demo').classes('text-h5')
    ui.label('Click to select, double-click or click edit button to edit. Use arrow keys to navigate.').classes('text-caption')

    with ui.card().classes('card w-full'):
        await table.build()     # type: ignore


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(show=False)
