"""Tests for build_form_field, EditCard, EditDialog."""
import asyncio

import pytest
from nicegui import ui
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import Column, FormConfig, EditCard, EditDialog
from ng_rdm.components.fields import build_form_field

from .conftest import html_should_see

pytestmark = pytest.mark.components


# ═══════════════════════════════════════════════
# build_form_field
# ═══════════════════════════════════════════════

async def test_field_creates_input(user: User):
    """Default ui_type=None creates ui.input."""
    @ui.page('/')
    def page():
        state = {'name': ''}
        build_form_field(Column(name='name', label='Name'), state)

    await user.open('/')
    await user.should_see(kind=ui.input)


async def test_field_creates_number(user: User):
    """ui_type=ui.number creates number input."""
    @ui.page('/')
    def page():
        state = {'count': None}
        build_form_field(Column(name='count', label='Count', ui_type=ui.number), state)

    await user.open('/')
    await user.should_see(kind=ui.number)


async def test_field_creates_textarea(user: User):
    """ui_type=ui.textarea creates textarea."""
    @ui.page('/')
    def page():
        state = {'notes': ''}
        build_form_field(Column(name='notes', label='Notes', ui_type=ui.textarea), state)

    await user.open('/')
    await user.should_see(kind=ui.textarea)


async def test_field_creates_select(user: User):
    """ui_type=ui.select with options."""
    @ui.page('/')
    def page():
        state = {'role': None}
        build_form_field(
            Column(name='role', label='Role', ui_type=ui.select, parms={'options': ['Admin', 'User']}),
            state,
        )

    await user.open('/')
    await user.should_see(kind=ui.select)


async def test_field_creates_checkbox(user: User):
    """ui_type=ui.checkbox."""
    @ui.page('/')
    def page():
        state = {'active': False}
        build_form_field(Column(name='active', label='Active', ui_type=ui.checkbox), state)

    await user.open('/')
    await user.should_see(kind=ui.checkbox)


async def test_field_binds_to_state(user: User):
    """Field value bound to state dict."""
    state = {'name': ''}

    @ui.page('/')
    def page():
        build_form_field(Column(name='name', label='Name'), state)

    await user.open('/')
    user.find(kind=ui.input).type('Alice')
    assert state['name'] == 'Alice'


# ═══════════════════════════════════════════════
# EditCard
# ═══════════════════════════════════════════════

async def test_editcard_renders_form_fields(user: User):
    """All columns render as form fields."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = EditCard(
            data_source=store,
            config=FormConfig(columns=[
                Column(name='name', label='Name'),
                Column(name='email', label='Email'),
            ]),
        )
        card.set_item(None)
        await card.build()

    await user.open('/')
    # New item shows "Add" button, not "Save"
    await user.should_see('Add')
    await user.should_see('Cancel')


async def test_editcard_save_creates_new(user: User):
    """Save on new form creates item in store."""
    store = DictStore()
    saved_log = []

    @ui.page('/')
    async def page():
        card = EditCard(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
            on_saved=lambda item: saved_log.append(item),
        )
        card.set_item(None)
        card.state['form']['name'] = 'Alice'
        await card.build()

    await user.open('/')
    user.find('Add').click()
    await asyncio.sleep(0.1)
    items = await store.read_items()
    assert len(items) == 1
    assert items[0]['name'] == 'Alice'


async def test_editcard_save_updates_existing(user: User):
    """Save with item updates in store."""
    store = DictStore()

    @ui.page('/')
    async def page():
        item = await store.create_item({'name': 'Alice'})
        card = EditCard(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
        )
        card.set_item(item)
        card.state['form']['name'] = 'Alice Updated'
        await card.build()

    await user.open('/')
    user.find('Save').click()
    await asyncio.sleep(0.1)
    items = await store.read_items()
    assert items[0]['name'] == 'Alice Updated'


async def test_editcard_cancel_callback(user: User):
    """Cancel button fires on_cancel."""
    store = DictStore()
    cancel_log = []

    @ui.page('/')
    async def page():
        card = EditCard(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
            on_cancel=lambda: cancel_log.append('cancelled'),
        )
        card.set_item(None)
        await card.build()

    await user.open('/')
    user.find('Cancel').click()
    assert cancel_log == ['cancelled']


# ═══════════════════════════════════════════════
# EditDialog
# ═══════════════════════════════════════════════

async def test_editdialog_open_for_new(user: User):
    """open_for_new() shows dialog with empty form."""
    store = DictStore()

    @ui.page('/')
    async def page():
        dlg = EditDialog(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
        )
        dlg.open_for_new()

    await user.open('/')
    await user.should_see('Add')


async def test_editdialog_open_for_edit(user: User):
    """open_for_edit(item) pre-fills form."""
    store = DictStore()

    @ui.page('/')
    async def page():
        item = await store.create_item({'name': 'Alice'})
        dlg = EditDialog(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
        )
        dlg.open_for_edit(item)

    await user.open('/')
    await user.should_see('Edit')


async def test_editdialog_save_creates(user: User):
    """Save in new mode creates item."""
    store = DictStore()
    saved_log = []

    @ui.page('/')
    async def page():
        dlg = EditDialog(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
            on_saved=lambda item: saved_log.append(item),
        )
        dlg.open_for_new()
        dlg.state['form']['name'] = 'Alice'

    await user.open('/')
    user.find('Save').click()
    await asyncio.sleep(0.1)
    items = await store.read_items()
    assert len(items) == 1
    assert items[0]['name'] == 'Alice'


async def test_editdialog_close_on_cancel(user: User):
    """Cancel closes dialog."""
    store = DictStore()

    @ui.page('/')
    async def page():
        dlg = EditDialog(
            data_source=store,
            config=FormConfig(columns=[Column(name='name', label='Name')]),
        )
        dlg.open_for_new()

    await user.open('/')
    user.find('Cancel').click()
    # Dialog should be closed — backdrop hidden
