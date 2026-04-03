"""
Minimal i18n for ng_rdm components.

Self-contained translations for generic CRUD UI strings.
Separate from app-level services/i18n.py to keep this package portable.
"""
from ng_rdm.utils import logger

_translations: dict[str, dict[str, str]] = {
    'nl_nl': {
        # Alphabetical
        '(none)': '(geen)',
        'Add': 'Toevoegen',
        'Add new': 'Nieuw toevoegen',
        '← Back': '← Terug',
        'Cancel': 'Annuleren',
        'Create': 'Aanmaken',
        'Delete': 'Verwijderen',
        'Delete item?': 'Item verwijderen?',
        'Edit': 'Bewerken',
        'enter a valid date': 'voer een geldige datum in',
        'Item created': 'Item aangemaakt',
        'Item deleted': 'Item verwijderd',
        'Item updated': 'Item bijgewerkt',
        'Next →': 'Volgende →',
        'No data': 'Geen gegevens',
        'Save': 'Opslaan',
        'This action cannot be undone': 'Deze actie kan niet ongedaan worden gemaakt',
        'Update failed': 'Bijwerken mislukt',
        'This field is required': 'Dit veld is verplicht',
    },
}

_language: str = 'en_gb'

def set_language(lang: str) -> None:
    """Set the current language for crud i18n."""
    global _language
    if lang in _translations:
        _language = lang
    else:
        logger.warning(f"Language '{lang}' not found in translations. Falling back to English.")


def set_translations(translations: dict[str, dict[str, str]]) -> None:
    """Override default translations."""
    global _translations
    _translations.update(translations)


def _(key: str) -> str:
    """Translate key using crud-specific translations."""
    if _language != 'en_gb':
        if tl := _translations.get(_language):
            return tl.get(key, key)
        else:
            logger.warning(f"No translation found for '{key}' in language '{_language}'")
    return key

# Convenience formatters for Column.formatter

def none_as_text(value: str) -> str:
    """Format empty/None values as translated '(none)'."""
    return value if value else _('(none)')
