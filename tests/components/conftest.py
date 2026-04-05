"""
Conftest for component tests.

NiceGUI testing plugin is registered in the top-level conftest.py.
Component tests use DictStore only (no ORM).
"""
import asyncio

import pytest
from nicegui.testing import User

from ng_rdm.store import DictStore
from ng_rdm.components import Column, TableConfig, FormConfig


# ── HTML element test helpers ──
# NiceGUI's ElementFilter does NOT check HTMLElement._text,
# so user.should_see() / user.find() won't work for html.* elements.
# These helpers traverse the element tree directly.

def get_html_texts(user: User) -> list[str]:
    """Get all _text values from HTMLElements in the current page."""
    texts = []
    with user:
        for el in user.current_layout.descendants():
            text = getattr(el, '_text', None)
            if text:
                texts.append(text)
    return texts


def html_should_see(user: User, text: str) -> None:
    """Assert that at least one HTMLElement contains the given text."""
    texts = get_html_texts(user)
    assert any(text in t for t in texts), \
        f"Expected to find '{text}' in HTML elements, found: {texts}"


async def html_should_see_async(user: User, text: str, retries: int = 5) -> None:
    """Assert with retries — use after clicks that trigger refreshable updates."""
    for _ in range(retries):
        texts = get_html_texts(user)
        if any(text in t for t in texts):
            return
        await asyncio.sleep(0.1)
    raise AssertionError(
        f"Expected to find '{text}' in HTML elements after {retries} retries, found: {texts}"
    )


def html_should_not_see(user: User, text: str) -> None:
    """Assert that no visible HTMLElement contains the given text."""
    with user:
        for el in user.current_layout.descendants():
            t = getattr(el, '_text', None)
            if t and text in t and el.visible:
                raise AssertionError(f"Did not expect to see '{text}' but found it in visible element")


def find_html_elements_with_text(user: User, text: str) -> list:
    """Find all HTMLElements whose _text contains the given string."""
    results = []
    with user:
        for el in user.current_layout.descendants():
            t = getattr(el, '_text', None)
            if t and text in t:
                results.append(el)
    return results


# ── Shared fixtures ──

@pytest.fixture
def sample_columns() -> list[Column]:
    """Standard columns for testing."""
    return [
        Column(name='name', label='Name'),
        Column(name='email', label='Email'),
    ]


@pytest.fixture
def sample_table_config(sample_columns) -> TableConfig:
    return TableConfig(columns=sample_columns)


@pytest.fixture
def sample_form_config(sample_columns) -> FormConfig:
    return FormConfig(columns=sample_columns)
