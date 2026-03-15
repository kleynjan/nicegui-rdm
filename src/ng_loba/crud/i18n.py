"""
Minimal i18n for ng_loba/crud components.

Self-contained translations for generic CRUD UI strings.
Separate from app-level services/i18n.py to keep this package portable.
"""

_translations: dict[str, str] = {
    # Alphabetical
    '(none)': '(geen)',
    'Add': 'Toevoegen',
    'Add new': 'Nieuw toevoegen',
    'Are you sure?': 'Weet je het zeker?',
    'Cancel': 'Annuleren',
    'Delete': 'Verwijderen',
    'Delete item?': 'Item verwijderen?',
    'Delete this item?': 'Dit item verwijderen?',
    'Edit': 'Bewerken',
    'Item created': 'Item aangemaakt',
    'Item deleted': 'Item verwijderd',
    'Item updated': 'Item bijgewerkt',
    'New': 'Nieuw',
    'No': 'Nee',
    'Save': 'Opslaan',
    'This action cannot be undone': 'Deze actie kan niet ongedaan worden gemaakt',
    'This action cannot be undone.': 'Deze actie kan niet ongedaan worden gemaakt.',
    'Update failed': 'Bijwerken mislukt',
    'Yes': 'Ja',
}

_language: str = 'nl_nl'


def set_language(lang: str) -> None:
    """Set the current language for crud i18n."""
    global _language
    _language = lang


def set_translations(translations: dict[str, str]) -> None:
    """Override default translations."""
    global _translations
    _translations.update(translations)


def _(key: str) -> str:
    """Translate key using crud-specific translations."""
    if _language == 'en_gb':
        return key
    return _translations.get(key, key)


# Convenience formatters for Column.formatter

def none_as_text(value: str) -> str:
    """Format empty/None values as translated '(none)'."""
    return value if value else _('(none)')
