from nicegui import ui
from ng_loba import DictStore, Validator, FieldSpec
from ng_loba import CrudTable, Column, TableConfig, init_page
from ng_loba import StoreRefreshable

# Define field validation
name_validator = Validator(
    message="Name must not be empty",
    validator=lambda v, _: bool(v.strip())
)

# Create store with validation
store = DictStore({
    'name': FieldSpec(validators=[name_validator])
})


# # Use CRUD operations
# await store.create_item({'name': 'Test'})
# items = await store.read_items()

# CrudTable Example

# Define table columns
config = TableConfig(
    columns=[
        Column(name='name', label='Name', ui_type=ui.input),
        Column(name='email', label='Email', ui_type=ui.input),
    ],
    focus_column='name'
)

# Create table
table = CrudTable(
    state={'editor': {}},
    store=store,
    config=config
)

class UserList(StoreRefreshable):
    async def _rebuild(self):
        items = await self.store.read_items()
        with ui.column():
            for item in items:
                ui.label(item['name'])

user_list = UserList(state={}, store=store)

# Build table in UI
@ui.page('/')
async def main():
    init_page(ui)
    await store.create_item({'name': 'Test', 'email': 'test@testy.com'})
    await store.create_item({'name': 'Test2', 'email': 'test2@testy.com'})

    await table.build()     # type: ignore

    # Create and build component
    await user_list.build()  # type: ignore

ui.run(show=False)
