"""Tests for Dialog open/close."""
import pytest
from nicegui import html, ui
from nicegui.testing import User

from ng_rdm.components import Dialog

from .conftest import html_should_see

pytestmark = pytest.mark.components


async def test_dialog_open_close(user: User):
    """Dialog opens and closes via state."""
    state = {}

    @ui.page('/')
    def page():
        with Dialog(state=state) as dlg:
            html.span('Dialog Content')
        dlg.open()

    await user.open('/')
    assert state['is_open'] is True
    html_should_see(user, 'Dialog Content')


async def test_dialog_visibility_binding(user: User):
    """Dialog is hidden when state is_open=False."""
    state = {}

    @ui.page('/')
    def page():
        with Dialog(state=state) as dlg:
            html.span('Hidden Content')
        # Don't open it

    await user.open('/')
    assert state['is_open'] is False


async def test_dialog_on_close_callback(user: User):
    """on_close fires when dialog closes."""
    state = {}
    close_log = []

    @ui.page('/')
    def page():
        with Dialog(state=state, on_close=lambda: close_log.append('closed')) as dlg:
            html.span('Content')
        dlg.open()
        dlg.close()

    await user.open('/')
    assert close_log == ['closed']
    assert state['is_open'] is False


async def test_dialog_actions_section(user: User):
    """Actions slot renders provided content."""
    state = {}

    @ui.page('/')
    def page():
        with Dialog(state=state, title='Test') as dlg:
            html.span('Body')
            with dlg.actions():
                html.span('Footer Action')
        dlg.open()

    await user.open('/')
    html_should_see(user, 'Footer Action')
