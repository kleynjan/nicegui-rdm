"""Unit tests for i18n module.

Pure Python tests — no NiceGUI User fixture needed.
"""
import pytest

from ng_rdm.components.i18n import _, set_language, set_translations, none_as_text

pytestmark = pytest.mark.components


@pytest.fixture(autouse=True)
def reset_i18n():
    """Reset language and translations after each test."""
    import ng_rdm.components.i18n as i18n_mod
    original_language = i18n_mod._language
    original_translations = {k: dict(v) for k, v in i18n_mod._translations.items()}
    yield
    i18n_mod._language = original_language
    i18n_mod._translations = original_translations


# ── Default English ──

def test_default_english():
    """Default language returns key unchanged."""
    assert _('Save') == 'Save'
    assert _('Cancel') == 'Cancel'


def test_unknown_key_returns_key():
    """Unknown key returns the key itself."""
    assert _('nonexistent_key_xyz') == 'nonexistent_key_xyz'


# ── Dutch ──

def test_set_dutch():
    """set_language('nl_nl') switches to Dutch."""
    set_language('nl_nl')
    assert _('Save') == 'Opslaan'


def test_dutch_translations_spot_check():
    """Spot-check several Dutch translations."""
    set_language('nl_nl')
    assert _('Cancel') == 'Annuleren'
    assert _('Delete') == 'Verwijderen'
    assert _('Edit') == 'Bewerken'
    assert _('Add new') == 'Nieuw toevoegen'


def test_dutch_unknown_key_returns_key():
    """Unknown key in Dutch still returns key itself."""
    set_language('nl_nl')
    assert _('nonexistent_key_xyz') == 'nonexistent_key_xyz'


# ── Custom translations ──

def test_custom_translations():
    """set_translations adds/overrides translations."""
    set_translations({'en_gb': {'Save': 'Store it'}})
    # en_gb is still the default which returns key unchanged,
    # but custom translations for other languages work
    set_translations({'nl_nl': {'Custom Key': 'Aangepaste Sleutel'}})
    set_language('nl_nl')
    assert _('Custom Key') == 'Aangepaste Sleutel'


# ── Invalid language ──

def test_invalid_language_stays_english():
    """Unknown language code logs warning and stays on English."""
    set_language('xx_xx')  # Should warn and not switch
    assert _('Save') == 'Save'


# ── none_as_text ──

def test_none_as_text_english():
    """Empty value returns '(none)' in English."""
    assert none_as_text('') == '(none)'
    assert none_as_text('hello') == 'hello'


def test_none_as_text_dutch():
    """Empty value returns '(geen)' in Dutch."""
    set_language('nl_nl')
    assert none_as_text('') == '(geen)'
