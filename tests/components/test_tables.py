"""Tests for ActionButtonTable, ListTable, SelectionTable."""
import asyncio
from typing import cast

import pytest
from nicegui import ui
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import (
    ActionButtonTable, ListTable, SelectionTable,
    Column, TableConfig, RowAction,
)
from ng_rdm.components.i18n import _

from .conftest import html_should_see, html_should_not_see, html_should_see_async, get_html_texts

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
    """Edit icon button renders with action mark."""
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
    # Edit button at index 0 (first in _all_actions), row id 0
    user.find(marker='rdm-action-0-0')


async def test_abt_shows_delete_icon_button(user: User):
    """Delete icon button renders with action mark."""
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
    # Delete button at index 1 (after edit in _all_actions), row id 0
    user.find(marker='rdm-action-1-0')


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
    # Edit at index 0, row ids 0 and 1
    user.find(marker='rdm-action-0-0').click()
    await asyncio.sleep(0.1)
    assert edit_log == ['Alice']
    user.find(marker='rdm-action-0-1').click()
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
    # Delete at index 1 (after edit), row id 0
    user.find(marker='rdm-action-1-0').click()
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
        await table.render()

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
            on_add=lambda: None,
            auto_observe=False,
        )
        await table.render()

    await user.open('/')
    html_should_not_see(user, 'Add new')


# ═══════════════════════════════════════════════
# Toolbar (rendered by render(), outside the refreshable)
# ═══════════════════════════════════════════════

async def test_toolbar_renders_and_survives_empty_data(user: User):
    """render_toolbar content appears — also when the filter matches zero rows."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            filter_by={'name': 'Nobody'},
            render_toolbar=lambda: ui.label('TOOLBAR'),
            auto_observe=False,
        )
        await table.render()

    await user.open('/')
    await user.should_see('TOOLBAR')
    html_should_see(user, 'Name')          # headers survive the empty result too


async def test_toolbar_accepts_async_render_toolbar(user: User):
    """render_toolbar may be a coroutine function — it can await read_counts()."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )

        async def toolbar():
            ui.label(f"total {await store.read_counts()}")

        table.render_toolbar = toolbar
        await table.render()

    await user.open('/')
    await user.should_see('total 1')


async def test_add_button_needs_a_handler(user: User):
    """Default config renders no Add button; on_add renders one — also on SelectionTable."""
    store = DictStore()
    config = TableConfig(columns=[Column(name='name', label='Name')])

    @ui.page('/')
    async def page():
        plain = ListTable(data_source=store, config=config, auto_observe=False)
        await plain.render()
        wired = SelectionTable(
            data_source=store, config=config, on_add=lambda: None, auto_observe=False,
        )
        await wired.render()

    await user.open('/')
    assert len(user.find('Add new').elements) == 1  # only the on_add-wired table has one


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
                    RowAction(label='Send', color='primary', callback=lambda row: action_log.append(row['name'])),
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


# ═══════════════════════════════════════════════
# Header-click sorting
# ═══════════════════════════════════════════════

def _visible_order(user: User, values: set[str]) -> list[str]:
    """Return the given values in the order they appear in the rendered HTML."""
    return [t for t in get_html_texts(user) if t in values]


NAMES = {'Alice', 'Bob', 'Carol'}


async def _seed_names(store: DictStore):
    for name in ['Carol', 'Alice', 'Bob']:  # deliberately unsorted
        await store.create_item({'name': name})


async def test_sort_ascending_on_header_click(user: User):
    """Clicking a sortable header orders rows ascending by that field."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name', sortable=True)]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    assert _visible_order(user, NAMES) == ['Carol', 'Alice', 'Bob']  # insertion order
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Alice', 'Bob', 'Carol']


async def test_sort_toggles_descending(user: User):
    """A second click on the same header flips to descending."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name', sortable=True)]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Alice', 'Bob', 'Carol']
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Carol', 'Bob', 'Alice']


async def test_non_sortable_header_has_no_sort_handle(user: User):
    """Columns that don't opt in render a plain header with no sort marker."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),  # sortable defaults False
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    html_should_see(user, 'Name')
    with pytest.raises(AssertionError):
        user.find(marker='rdm-sort-name')


async def test_sort_key_overrides_field(user: User):
    """sort_key controls the ordering field independent of the displayed column name."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'label': 'Zeta', 'rank': 1})
        await store.create_item({'label': 'Alpha', 'rank': 2})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='label', label='Label', sortable=True, sort_key='rank'),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-sort-label').click()
    await asyncio.sleep(0.1)
    # Ordered by rank asc → Zeta (1) before Alpha (2), not alphabetical
    assert _visible_order(user, {'Alpha', 'Zeta'}) == ['Zeta', 'Alpha']


async def test_sort_key_resolves_lazily_via_query_map(user: User):
    """A derived column sorts through query_map — resolved against the store at click
    time, not when the Column (which predates the store) was constructed."""
    store = DictStore()
    column = Column(name='full_name', label='Name', sortable=True)   # no sort_key

    @ui.page('/')
    async def page():
        store.set_derived_fields(
            {'full_name': lambda i: f"{i['first']} {i['last']}"},
            query_map={'full_name': ['last', 'first']},
        )
        await store.create_item({'first': 'Alice', 'last': 'Young'})
        await store.create_item({'first': 'Bob', 'last': 'Adams'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[column]),
            auto_observe=False,
        )
        await table.build()

    assert column.sort_key is None          # nothing was resolved at construction time
    await user.open('/')
    user.find(marker='rdm-sort-full_name').click()
    await asyncio.sleep(0.1)
    # ordered by `last` → Bob Adams before Alice Young
    assert _visible_order(user, {'Alice Young', 'Bob Adams'}) == ['Bob Adams', 'Alice Young']


async def test_sort_desc_first_opens_descending(user: User):
    """sort_desc_first flips the initial click to descending; toggling is unchanged."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[
                Column(name='name', label='Name', sortable=True, sort_desc_first=True),
            ]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Carol', 'Bob', 'Alice']
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Alice', 'Bob', 'Carol']


async def test_sort_is_per_subscriber(user: User):
    """Two tables on one store sort independently (sort state is per-instance)."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        cfg = TableConfig(columns=[Column(name='name', label='Name', sortable=True)])
        asc = ListTable(data_source=store, config=cfg, order_by=['name'], auto_observe=False)
        desc = ListTable(data_source=store, config=cfg, order_by=['-name'], auto_observe=False)
        await asc.build()
        await desc.build()

    await user.open('/')
    # First table ascending, second descending, concatenated in DOM order
    assert _visible_order(user, NAMES) == ['Alice', 'Bob', 'Carol', 'Carol', 'Bob', 'Alice']


# ═══════════════════════════════════════════════
# q predicate pass-through
# ═══════════════════════════════════════════════

async def test_q_filters_rows_at_construction(user: User):
    """A q passed to the constructor reaches read_items — no subclass needed."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            q=lambda item: item['name'].startswith('A'),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    assert _visible_order(user, NAMES) == ['Alice']


async def test_q_reassignment_swaps_result_set(user: User):
    """Assigning table.q then refreshing is the supported way to drive a search box."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )
        await table.build()

        async def search():
            table.q = lambda item: item['name'] == 'Bob'
            await table.build.refresh()

        ui.button('search', on_click=search)

    await user.open('/')
    assert _visible_order(user, NAMES) == ['Carol', 'Alice', 'Bob']  # unfiltered
    user.find('search').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Bob']


async def test_q_composes_with_filter_by_and_window(user: User):
    """q is ANDed with filter_by and applied before limit/order_by."""
    store = DictStore()

    @ui.page('/')
    async def page():
        for name, kind in [('Carol', 'x'), ('Alice', 'x'), ('Bob', 'y'), ('Alicia', 'x')]:
            await store.create_item({'name': name, 'kind': kind})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            filter_by={'kind': 'x'},
            q=lambda item: 'ali' in item['name'].lower(),
            order_by=['name'],
            limit=1,
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    # kind=x AND name~ali → Alice, Alicia; ordered by name, capped at 1
    assert _visible_order(user, {'Alice', 'Alicia', 'Bob', 'Carol'}) == ['Alice']


async def test_no_q_is_unchanged(user: User):
    """Omitting q keeps the existing call shape (q=None) — nothing regresses."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            auto_observe=False,
        )
        await table.build()

    await user.open('/')
    assert _visible_order(user, NAMES) == ['Carol', 'Alice', 'Bob']


# ═══════════════════════════════════════════════
# Pager, search, requery
# ═══════════════════════════════════════════════

async def test_pager_pages_and_publishes_state(user: User):
    """page_first/page_last/total track the window; next disables on the last page."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')], show_pager=True),
            order_by=['name'],
            limit=2,
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    assert (table.state['page_first'], table.state['page_last'], table.state['total']) == (1, 2, 3)
    assert table.state['has_prev'] is False and table.state['has_next'] is True
    await user.should_see('1–2 of 3')

    await table._page(1)
    assert (table.state['page_first'], table.state['page_last'], table.state['total']) == (3, 3, 3)
    assert table.state['has_prev'] is True and table.state['has_next'] is False

    await table._page(-1)
    assert table.state['page_first'] == 1


async def test_pager_buttons_page_on_click(user: User):
    """The pager buttons carry stable markers, so paging is clickable from a test."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')], show_pager=True),
            order_by=['name'],
            limit=2,
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    assert _visible_order(user, NAMES) == ['Alice', 'Bob']

    user.find(marker='rdm-pager-next').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Carol']
    assert tables[0].state['page_first'] == 3
    await user.should_see('3–3 of 3')

    user.find(marker='rdm-pager-prev').click()
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Alice', 'Bob']
    assert tables[0].state['page_first'] == 1


async def test_custom_pager_label_is_not_asked_about_the_empty_case(user: User):
    """total == 0 falls back to the built-in empty label, which prefers empty_message —
    a custom pager_label never has to remember the branch."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                empty_message='No persons found.',
                show_pager=True,
                pager_label=lambda f, l, t: f'{f}–{l} of {t} persons',
            ),
            limit=2,
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    assert table.state['page_label'] == 'No persons found.'

    await store.create_item({'name': 'Alice'})
    await table.build.refresh()
    assert table.state['page_label'] == '1–1 of 1 persons'  # non-empty still uses the custom label


async def test_sort_click_returns_to_first_page(user: User):
    """A header click resets offset — the bound pager follows for free."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name', sortable=True)], show_pager=True),
            order_by=['name'],
            limit=2,
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    await tables[0]._page(1)
    assert tables[0].state['page_first'] == 3
    user.find(marker='rdm-sort-name').click()
    await asyncio.sleep(0.1)
    assert tables[0].state['offset'] == 0
    assert tables[0].state['page_first'] == 1


async def test_pager_clamps_offset_when_rows_disappear(user: User):
    """A window past the end steps back to the last page instead of showing nothing."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')], show_pager=True),
            order_by=['name'],
            limit=2,
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    await table._page(1)                      # offset 2, one row
    await store.delete_item({'id': 1})        # only 2 rows left → page 2 is empty
    await table.build.refresh()
    assert table.state['offset'] == 0
    assert table.state['total'] == 2 and table.state['shown'] == 2


async def test_no_count_query_when_nothing_shows_a_total(user: User):
    """Without a pager (or pager_label) a read never adds a COUNT."""
    store = DictStore()
    calls = []
    real_read_counts = store.read_counts

    async def spy(*args, **kwargs):
        calls.append(kwargs)
        return await real_read_counts(*args, **kwargs)

    store.read_counts = spy  # type: ignore[method-assign]

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            limit=2,                       # a full first page: total is NOT free
            auto_observe=False,
        )
        await table.render()

    await user.open('/')
    assert calls == []


async def test_search_narrows_and_composes_with_q(user: User):
    """The search predicate comes from the store and ANDs with a preset q."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        for name, kind in [('Alice', 'x'), ('Alicia', 'y'), ('Bob', 'x')]:
            await store.create_item({'name': name, 'kind': kind})
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_search=True, search_fields=['name'],
            ),
            q=lambda item: item['kind'] == 'x',
            order_by=['name'],
            auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    names = {'Alice', 'Alicia', 'Bob'}
    assert _visible_order(user, names) == ['Alice', 'Bob']   # q only

    await tables[0]._on_search('ali')
    await asyncio.sleep(0.1)
    assert _visible_order(user, names) == ['Alice']          # q AND search, not q clobbered

    await tables[0]._on_search('')
    await asyncio.sleep(0.1)
    assert _visible_order(user, names) == ['Alice', 'Bob']


async def test_search_input_is_wired_and_keeps_its_value(user: User):
    """Typing in the rendered input filters — and the input survives the refresh it
    triggers, because the toolbar sits outside the refreshable."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_search=True, search_fields=['name'],
            ),
            order_by=['name'], auto_observe=False,
        )
        await table.render()

    def search_box() -> ui.input:
        with user:
            return cast(ui.input, list(user.find(marker='rdm-search').elements)[0])

    await user.open('/')
    search_box().value = 'bo'                 # fires the same handler as a keystroke
    await asyncio.sleep(0.1)
    assert _visible_order(user, NAMES) == ['Bob']
    assert search_box().value == 'bo'         # not re-rendered, so not reset


async def test_search_resets_to_first_page(user: User):
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_search=True, search_fields=['name'], show_pager=True,
            ),
            order_by=['name'], limit=2, auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    await tables[0]._page(1)
    assert tables[0].state['offset'] == 2
    await tables[0]._on_search('a')
    assert tables[0].state['offset'] == 0


async def test_search_and_pager_render_in_their_own_slots(user: User):
    """Default config: search above the table, pager below (the 2.2 regression guard)."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_search=True, search_fields=['name'], show_pager=True,
            ),
            order_by=['name'], limit=2, auto_observe=False,
        )
        await table.render()

    await user.open('/')
    with user:
        classes = [c for el in user.current_layout.descendants()
                   for c in el.classes if c in ('rdm-search', 'rdm-table', 'rdm-pager')]
    assert classes == ['rdm-search', 'rdm-table', 'rdm-pager']


async def test_shared_slot_puts_search_and_pager_in_one_toolbar(user: User):
    """Assigning both to the same slot gives a single toolbar row: search, then pager."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(
                columns=[Column(name='name', label='Name')],
                show_search=True, search_fields=['name'],
                show_pager=True, pager_position='top',
            ),
            order_by=['name'], limit=2, auto_observe=False,
        )
        await table.render()

    await user.open('/')
    with user:
        toolbars = [el for el in user.current_layout.descendants()
                    if 'rdm-table-toolbar' in el.classes]
        classes = [c for el in user.current_layout.descendants()
                   for c in el.classes if c in ('rdm-search', 'rdm-table', 'rdm-pager')]
    assert len(toolbars) == 1                                  # one row, not two
    assert classes == ['rdm-search', 'rdm-pager', 'rdm-table']  # both above the table


async def test_requery_sets_predicate_and_resets_page(user: User):
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            order_by=['name'], limit=2, auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    await tables[0]._page(1)
    await tables[0].requery(q=lambda item: item['name'] != 'Bob')
    await asyncio.sleep(0.1)
    assert tables[0].state['offset'] == 0
    assert _visible_order(user, NAMES) == ['Alice', 'Carol']


async def test_requery_moves_the_observer_subscription(user: User):
    """A new filter_by takes the topic subscription with it — an observed table must
    keep reacting to its *new* scope, not the one it was constructed with."""
    store = DictStore()
    store.set_topic_fields(['kind'])
    tables = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice', 'kind': 'x'})
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            filter_by={'kind': 'x'},
            auto_observe=True,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    await table.requery(filter_by={'kind': 'y'})
    assert table._observed_topics == {'kind': 'y'}

    await store.create_item({'name': 'Yvonne', 'kind': 'y'})   # in the new scope
    await asyncio.sleep(0.2)
    assert [i['name'] for i in table.data] == ['Yvonne']


async def test_requery_keeps_explicit_topics(user: User):
    """A table given explicit topics keeps them — requery only moves a subscription
    that was tracking filter_by."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            filter_by={'kind': 'x'},
            auto_observe=False,
        )
        table.observe(topics={'team': 'ops'})     # deliberately not filter_by
        tables.append(table)
        await table.render()

    await user.open('/')
    await tables[0].requery(filter_by={'kind': 'y'})
    assert tables[0]._observed_topics == {'team': 'ops'}


async def test_top_pager_binds_to_seeded_state(user: User):
    """A pager in the top slot renders before the first read — its keys must exist."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        table = ListTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')],
                               show_pager=True, pager_position='top'),
            limit=2, auto_observe=False,
        )
        tables.append(table)
        # state is seeded at construction, before any toolbar binding happens
        assert tables[0].state['page_label'] == ''
        assert tables[0].state['has_prev'] is False and tables[0].state['has_next'] is False
        await table.render()

    await user.open('/')
    assert tables[0].state['page_label'] == _('No data')   # first read has published by now


async def test_selection_flags_offscreen_rows(user: User):
    """Selecting on page 1 and paging away surfaces the invisible selection."""
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')], show_pager=True),
            order_by=['name'], limit=2, auto_observe=False,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    table.add_to_selection(1)                       # Alice — page 1 under name order
    await table.build.refresh()
    assert (table.state['selected_count'], table.state['selected_offscreen']) == (1, 0)
    await table._page(1)                            # page 2 is Carol; Alice is now invisible
    assert (table.state['selected_count'], table.state['selected_offscreen']) == (1, 1)
    assert 'off page' in table.state['page_label']


async def test_selection_can_be_page_scoped(user: User):
    store = DictStore()
    tables = []

    @ui.page('/')
    async def page():
        await _seed_names(store)
        table = SelectionTable(
            data_source=store,
            config=TableConfig(columns=[Column(name='name', label='Name')]),
            order_by=['name'], limit=2, auto_observe=False,
            clear_selection_on_page_change=True,
        )
        tables.append(table)
        await table.render()

    await user.open('/')
    table = tables[0]
    table.add_to_selection(0)
    await table.build.refresh()
    assert table.state['selected_count'] == 1
    await table._page(1)
    assert table.state['selected_ids'] == []
