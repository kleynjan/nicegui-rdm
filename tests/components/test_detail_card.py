"""Tests for DetailCard rendering and actions."""
import pytest
from nicegui import html, ui
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import DetailCard

from .conftest import html_should_see

pytestmark = pytest.mark.components


async def _render_summary(item: dict):
    html.span(f'Name: {item["name"]}')
    html.span(f'Email: {item["email"]}')


async def test_dc_renders_summary(user: User):
    """Summary section renders item data."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'alice@test.com'})
        await card.build()

    await user.open('/')
    html_should_see(user, 'Name: Alice')
    html_should_see(user, 'Email: alice@test.com')


async def test_dc_edit_button(user: User):
    """Edit button visible when on_edit provided."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
            on_edit=lambda item: None,
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'a@test.com'})
        await card.build()

    await user.open('/')
    await user.should_see('Edit')


async def test_dc_delete_button(user: User):
    """Delete button visible when on_deleted provided."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
            on_deleted=lambda: None,
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'a@test.com'})
        await card.build()

    await user.open('/')
    await user.should_see('Delete')


async def test_dc_hide_edit(user: User):
    """show_edit=False hides edit button."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
            on_edit=lambda item: None,
            show_edit=False,
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'a@test.com'})
        await card.build()

    await user.open('/')
    await user.should_not_see('Edit')


async def test_dc_hide_delete(user: User):
    """show_delete=False hides delete button."""
    store = DictStore()

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
            on_deleted=lambda: None,
            show_delete=False,
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'a@test.com'})
        await card.build()

    await user.open('/')
    await user.should_not_see('Delete')


async def test_dc_edit_callback(user: User):
    """Edit button fires on_edit with item."""
    store = DictStore()
    edit_log = []

    @ui.page('/')
    async def page():
        card = DetailCard(
            data_source=store,
            render_summary=_render_summary,
            on_edit=lambda item: edit_log.append(item['name']),
        )
        card.set_item({'id': 1, 'name': 'Alice', 'email': 'a@test.com'})
        await card.build()

    await user.open('/')
    user.find('Edit').click()
    assert edit_log == ['Alice']
