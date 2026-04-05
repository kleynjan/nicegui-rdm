"""Tests for ActionButtonTable, ListTable, SelectionTable."""
import asyncio

import pytest
from nicegui import ui
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import (
    ActionButtonTable, ListTable, SelectionTable,
    Column, TableConfig, RowAction,
)

from .conftest import html_should_see, html_should_not_see, html_should_see_async

pytestmark = pytest.mark.components


# ═══════════════════════════════════════════════
# ActionButtonTable
# ═══════════════════════════════════════════════

async def test_abt_renders_headers(user: User):
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice', 'email': 'a@test.com'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='name', label='Name'),
                Column(name='email', label='Email'),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Name')
    html_should_see(user, 'Email')


async def test_abt_renders_row_data(user: User):
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice', 'email': 'alice@test.com'})
        await store.create_item({'name': 'Bob', 'email': 'bob@test.com'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='name', label='Name'),
                Column(name='email', label='Email'),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Alice')
    html_should_see(user, 'bob@test.com')


async def test_abt_shows_edit_icon_button(user: User):
    """Default action_style='icon' shows edit icon button with mark."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_edit=lambda row: None,
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    # Edit button should be findable by mark
    user.find(marker='rdm-edit-0')


async def test_abt_shows_delete_icon_button(user: User):
    """Default shows delete icon button with mark."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_delete=lambda row: None,
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-delete-0')


async def test_abt_calls_on_edit(user: User):
    """Clicking edit calls on_edit callback with row data."""
    store = DictStore()
    edit_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_edit=lambda row: edit_log.append(row['name']),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-edit-0').click()
    await asyncio.sleep(0.1)
    assert edit_log == ['Alice']
    user.find(marker='rdm-edit-1').click()
    await asyncio.sleep(0.1)
    assert edit_log == ['Alice', 'Bob']


async def test_abt_calls_on_delete(user: User):
    """Clicking delete fires delete handler."""
    store = DictStore()
    delete_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_delete=lambda row: delete_log.append(row['name']),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-delete-0').click()
    await asyncio.sleep(0.1)
    assert delete_log == ['Alice']


async def test_abt_empty_message(user: User):
    """Shows empty_message when store is empty."""
    store = DictStore()

    @ui.page('/')
    async def page():
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                empty_message='Nothing here',
            ),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Nothing here')


async def test_abt_add_button(user: User):
    """Toolbar shows add button, clicking fires on_add."""
    store = DictStore()
    add_log = []

    @ui.page('/')
    async def page():
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                add_button='Add Person',
            ),
            on_add=lambda: add_log.append('added'),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    await user.should_see('Add Person')
    user.find('Add Person').click()
    assert add_log == ['added']


async def test_abt_hide_add_button(user: User):
    """show_add_button=False hides the add button."""
    store = DictStore()

    @ui.page('/')
    async def page():
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_add_button=False,
            ),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_not_see(user, 'Add new')


async def test_abt_custom_actions(user: User):
    """RowAction buttons render and fire callbacks."""
    store = DictStore()
    action_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ActionButtonTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                custom_actions=[
                    RowAction(label='Send', variant='primary', callback=lambda row: action_log.append(row['name'])),
                ],
                show_edit_button=False,
                show_delete_button=False,
            ),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-action-0-0').click()
    await asyncio.sleep(0.1)
    assert action_log == ['Alice']


# ═══════════════════════════════════════════════
# ListTable
# ═══════════════════════════════════════════════

async def test_lt_renders_headers(user: User):
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Name')


async def test_lt_renders_rows(user: User):
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Alice')
    html_should_see(user, 'Bob')


async def test_lt_row_click(user: User):
    """Clicking row fires on_click with row key."""
    store = DictStore()
    click_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_click=lambda key: click_log.append(key),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-row-0').click()
    assert click_log == [0]
    user.find(marker='rdm-row-1').click()
    assert click_log == [0, 1]


async def test_lt_empty_message(user: User):
    store = DictStore()

    @ui.page('/')
    async def page():
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                empty_message='No items found',
            ),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'No items found')


async def test_lt_formatter(user: User):
    """Column formatter function applied to display."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'alice'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='name', label='Name', formatter=str.upper),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'ALICE')


async def test_lt_badge_column(user: User):
    """Column with badge ui_type renders badge-styled."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice', 'status': 'Active'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='name', label='Name'),
                Column(name='status', label='Status', ui_type=ui.badge),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    await user.should_see('Active')


# ═══════════════════════════════════════════════
# SelectionTable
# ═══════════════════════════════════════════════

async def test_st_renders_with_checkboxes(user: User):
    """Each row has a checkbox."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-checkbox-0')
    user.find(marker='rdm-checkbox-1')


async def test_st_select_row(user: User):
    """Clicking checkbox fires on_selection_change with selected ids."""
    store = DictStore()
    selection_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_selection_change=lambda ids: selection_log.append(ids),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-checkbox-0').click()
    assert any(0 in ids for ids in selection_log)


async def test_st_deselect_row(user: User):
    """Clicking again removes from selection."""
    store = DictStore()
    selection_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_selection_change=lambda ids: selection_log.append(ids),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-checkbox-0').click()  # Select
    user.find(marker='rdm-checkbox-0').click()  # Deselect
    # Last callback should have empty set
    assert selection_log[-1] == set()


async def test_st_on_selection_change(user: User):
    """Callback fires with updated selection set."""
    store = DictStore()
    selection_log = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            on_selection_change=lambda ids: selection_log.append(ids),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-checkbox-0').click()
    user.find(marker='rdm-checkbox-1').click()
    assert any({0, 1} == ids for ids in selection_log)
