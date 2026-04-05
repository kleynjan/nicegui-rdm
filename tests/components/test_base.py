"""Unit tests for base component dataclasses and form helpers.

These are pure Python tests — no NiceGUI User fixture needed.
"""
import pytest
from nicegui import ui

from ng_rdm.components.base import Column, TableConfig, FormConfig, RdmComponent

pytestmark = pytest.mark.components


# ── Column ──

def test_column_defaults_text():
    """Text column keeps empty string default."""
    col = Column(name='name', label='Name')
    assert col.default_value == ""


def test_column_defaults_number():
    """Number column gets None default instead of empty string."""
    col = Column(name='age', label='Age', ui_type=ui.number)
    assert col.default_value is None


def test_column_defaults_select():
    """Select column gets None default instead of empty string."""
    col = Column(name='role', label='Role', ui_type=ui.select)
    assert col.default_value is None


def test_column_width_style():
    """Column with width_percent gets computed flex style."""
    col = Column(name='name', label='Name', width_percent=30)
    assert col.width_style == "flex: 0 0 30%"


def test_column_no_width_style():
    """Column without width_percent has empty width_style."""
    col = Column(name='name', label='Name')
    assert col.width_style == ""


# ── TableConfig ──

def test_table_config_join_fields():
    """Columns with __ in name are extracted as join_fields."""
    config = TableConfig(columns=[
        Column(name='name', label='Name'),
        Column(name='role__name', label='Role'),
        Column(name='dept__title', label='Dept'),
    ])
    assert sorted(config.join_fields) == ['dept__title', 'role__name']


def test_table_config_no_join_fields():
    """Columns without __ yield empty join_fields."""
    config = TableConfig(columns=[
        Column(name='name', label='Name'),
        Column(name='email', label='Email'),
    ])
    assert config.join_fields == []


# ── FormConfig ──

def test_form_config_focus_column_default():
    """Default focus_column is first column name."""
    config = FormConfig(columns=[
        Column(name='name', label='Name'),
        Column(name='email', label='Email'),
    ])
    assert config.focus_column == 'name'


def test_form_config_focus_column_explicit():
    """Explicit focus_column is preserved."""
    config = FormConfig(
        columns=[Column(name='name', label='Name'), Column(name='email', label='Email')],
        focus_column='email',
    )
    assert config.focus_column == 'email'


# ── _init_form_state ──

def test_init_form_state_empty():
    """Without item, state uses column defaults."""
    columns = [
        Column(name='name', label='Name'),
        Column(name='count', label='Count', ui_type=ui.number),
    ]
    state = RdmComponent._init_form_state(columns, None)
    assert state == {'name': '', 'count': None}


def test_init_form_state_with_item():
    """With item, state uses item values."""
    columns = [
        Column(name='name', label='Name'),
        Column(name='email', label='Email'),
    ]
    item = {'name': 'Alice', 'email': 'alice@test.com'}
    state = RdmComponent._init_form_state(columns, item)
    assert state == {'name': 'Alice', 'email': 'alice@test.com'}


def test_init_form_state_number_preserves_none():
    """Number column preserves None from item (doesn't coerce to empty string)."""
    columns = [Column(name='count', label='Count', ui_type=ui.number)]
    item = {'count': None}
    state = RdmComponent._init_form_state(columns, item)
    assert state['count'] is None


# ── _build_item_data ──

def test_build_item_data():
    """Builds trimmed item data from state."""
    columns = [
        Column(name='name', label='Name'),
        Column(name='email', label='Email'),
    ]
    state = {'name': '  Alice  ', 'email': 'alice@test.com'}
    data = RdmComponent._build_item_data(columns, state)
    assert data == {'name': 'Alice', 'email': 'alice@test.com'}


def test_build_item_data_whitespace_to_none():
    """Whitespace-only strings become None."""
    columns = [Column(name='name', label='Name')]
    state = {'name': '   '}
    data = RdmComponent._build_item_data(columns, state)
    assert data['name'] is None


def test_build_item_data_empty_to_none():
    """Empty strings become None."""
    columns = [Column(name='name', label='Name')]
    state = {'name': ''}
    data = RdmComponent._build_item_data(columns, state)
    assert data['name'] is None
