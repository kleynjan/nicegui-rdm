"""Tests for ViewStack and Tabs."""
import asyncio

import pytest
from nicegui import html, ui
from nicegui.testing import User

from ng_rdm.components import ViewStack, Tabs

from .conftest import html_should_see, html_should_not_see, html_should_see_async

pytestmark = pytest.mark.components


# ═══════════════════════════════════════════════
# ViewStack
# ═══════════════════════════════════════════════

async def _render_list(vs):
    html.span('LIST VIEW')


async def _render_detail(vs, item):
    html.span(f'DETAIL: {item["name"]}')


async def _render_edit(vs, item):
    label = f'EDIT: {item["name"]}' if item else 'EDIT: NEW'
    html.span(label)


async def test_vs_renders_list_by_default(user: User):
    """List view visible initially."""
    @ui.page('/')
    async def page():
        vs = ViewStack(
            render_list=_render_list,
            render_detail=_render_detail,
            render_edit=_render_edit,
        )
        await vs.build()

    await user.open('/')
    html_should_see(user, 'LIST VIEW')


async def test_vs_show_detail(user: User):
    """show_detail switches to detail view."""
    @ui.page('/')
    async def page():
        vs = ViewStack(
            render_list=_render_list,
            render_detail=_render_detail,
            render_edit=_render_edit,
        )
        await vs.build()
        vs.show_detail({'name': 'Alice', 'id': 1})

    await user.open('/')
    await html_should_see_async(user, 'DETAIL: Alice')


async def test_vs_show_edit(user: User):
    """show_edit_existing switches to edit view."""
    @ui.page('/')
    async def page():
        vs = ViewStack(
            render_list=_render_list,
            render_detail=_render_detail,
            render_edit=_render_edit,
        )
        await vs.build()
        vs.show_edit_existing({'name': 'Alice', 'id': 1})

    await user.open('/')
    await html_should_see_async(user, 'EDIT: Alice')


async def test_vs_go_back_edit_to_detail(user: User):
    """Back from edit -> detail."""
    state = {}

    @ui.page('/')
    async def page():
        vs = ViewStack(
            render_list=_render_list,
            render_detail=_render_detail,
            render_edit=_render_edit,
            state=state,
        )
        await vs.build()
        vs.show_detail({'name': 'Alice', 'id': 1})
        vs.show_edit_existing()

    await user.open('/')
    assert state['view'] == 'edit'
    user.find(marker='rdm-back').click()
    await asyncio.sleep(0.1)
    assert state['view'] == 'detail'


async def test_vs_go_back_detail_to_list(user: User):
    """Back from detail -> list."""
    state = {}

    @ui.page('/')
    async def page():
        vs = ViewStack(
            render_list=_render_list,
            render_detail=_render_detail,
            render_edit=_render_edit,
            state=state,
        )
        await vs.build()
        vs.show_detail({'name': 'Alice', 'id': 1})

    await user.open('/')
    assert state['view'] == 'detail'
    user.find(marker='rdm-back').click()
    await asyncio.sleep(0.1)
    assert state['view'] == 'list'


# ═══════════════════════════════════════════════
# Tabs
# ═══════════════════════════════════════════════

async def _render_tab1():
    html.span('Content 1')


async def _render_tab2():
    html.span('Content 2')


async def test_tabs_renders_labels(user: User):
    """All tab labels visible."""
    @ui.page('/')
    async def page():
        tabs = Tabs(tabs=[
            ("t1", "Tab One", _render_tab1),
            ("t2", "Tab Two", _render_tab2),
        ])
        await tabs.build()

    await user.open('/')
    html_should_see(user, 'Tab One')
    html_should_see(user, 'Tab Two')


async def test_tabs_first_active(user: User):
    """First tab selected by default."""
    state = {}

    @ui.page('/')
    async def page():
        tabs = Tabs(
            tabs=[
                ("t1", "Tab One", _render_tab1),
                ("t2", "Tab Two", _render_tab2),
            ],
            state=state,
        )
        await tabs.build()

    await user.open('/')
    assert state['active'] == 't1'


async def test_tabs_switch_tab(user: User):
    """Clicking tab updates active tab state."""
    state = {}

    @ui.page('/')
    async def page():
        tabs = Tabs(
            tabs=[
                ("t1", "Tab One", _render_tab1),
                ("t2", "Tab Two", _render_tab2),
            ],
            state=state,
        )
        await tabs.build()

    await user.open('/')
    assert state['active'] == 't1'
    user.find(marker='rdm-tab-t2').click()
    assert state['active'] == 't2'


async def test_tabs_content_visibility(user: User):
    """Tab panels have visibility bindings driven by active state."""
    state = {}

    @ui.page('/')
    async def page():
        tabs = Tabs(
            tabs=[
                ("t1", "Tab One", _render_tab1),
                ("t2", "Tab Two", _render_tab2),
            ],
            state=state,
        )
        await tabs.build()

    await user.open('/')
    # Both panels are rendered, visibility is bound to state['active']
    html_should_see(user, 'Content 1')
    html_should_see(user, 'Content 2')
    # Active state drives which panel is visible
    assert state['active'] == 't1'
    user.find(marker='rdm-tab-t2').click()
    assert state['active'] == 't2'
