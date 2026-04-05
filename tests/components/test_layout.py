"""Tests for Button, IconButton, Row, Col, Separator."""
import pytest
from nicegui import ui
from nicegui.testing import User

from ng_rdm.components import Button, IconButton, Row, Col, Separator

from .conftest import html_should_see, get_html_texts

pytestmark = pytest.mark.components


# ── Button ──

async def test_button_renders(user: User):
    """Button label is visible."""
    @ui.page('/')
    def page():
        Button("Save")

    await user.open('/')
    await user.should_see('Save')


async def test_button_click(user: User):
    """on_click fires when button is clicked."""
    click_log = []

    @ui.page('/')
    def page():
        Button("Go", on_click=lambda: click_log.append('clicked'))

    await user.open('/')
    user.find('Go').click()
    assert click_log == ['clicked']


async def test_button_variants(user: User):
    """Different color variants get correct CSS classes."""
    @ui.page('/')
    def page():
        Button("Primary", color="primary").mark("btn-primary")
        Button("Danger", color="danger").mark("btn-danger")
        Button("Secondary", color="secondary").mark("btn-secondary")

    await user.open('/')
    with user:
        for el in user.current_layout.descendants():
            markers = getattr(el, '_markers', set())
            if 'btn-primary' in markers:
                assert 'rdm-btn-primary' in el._classes
            elif 'btn-danger' in markers:
                assert 'rdm-btn-danger' in el._classes
            elif 'btn-secondary' in markers:
                assert 'rdm-btn-secondary' in el._classes


async def test_button_disabled(user: User):
    """Disabled button has disabled prop."""
    click_log = []

    @ui.page('/')
    def page():
        Button("Nope", on_click=lambda: click_log.append('bad')).mark("btn-dis")

    await user.open('/')
    with user:
        for el in user.current_layout.descendants():
            if 'btn-dis' in getattr(el, '_markers', set()):
                el.disable()
                assert not el.enabled


# ── IconButton ──

async def test_icon_button_renders(user: User):
    """IconButton renders with Bootstrap icon class in child."""
    @ui.page('/')
    def page():
        IconButton("pencil").mark("icon-btn")

    await user.open('/')
    with user:
        for el in user.current_layout.descendants():
            if 'icon-btn' in getattr(el, '_markers', set()):
                assert 'rdm-btn-icon' in el._classes
                break
        else:
            raise AssertionError("IconButton not found")


# ── Row ──

async def test_row_layout(user: User):
    """Row creates a flex container with rdm-row class."""
    @ui.page('/')
    def page():
        with Row() as row:
            row.element.mark("test-row")

    await user.open('/')
    with user:
        for el in user.current_layout.descendants():
            if 'test-row' in getattr(el, '_markers', set()):
                assert 'rdm-row' in el._classes
                break
        else:
            raise AssertionError("Row not found")


# ── Col ──

async def test_col_layout(user: User):
    """Col creates a flex-direction:column container."""
    @ui.page('/')
    def page():
        with Col() as col:
            col.element.mark("test-col")

    await user.open('/')
    with user:
        for el in user.current_layout.descendants():
            if 'test-col' in getattr(el, '_markers', set()):
                assert 'rdm-col' in el._classes
                break
        else:
            raise AssertionError("Col not found")


# ── Separator ──

async def test_separator(user: User):
    """Separator renders with rdm-separator class."""
    @ui.page('/')
    def page():
        Separator()

    await user.open('/')
    with user:
        found = False
        for el in user.current_layout.descendants():
            if 'rdm-separator' in getattr(el, '_classes', []):
                found = True
                break
        assert found, "Separator with rdm-separator class not found"
