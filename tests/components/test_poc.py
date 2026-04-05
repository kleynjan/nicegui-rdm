"""
Proof-of-concept tests: validate NiceGUI User fixture works with html elements.

RDM components use nicegui.html elements (html.span, html.button, html.table, etc.)
rather than ui elements (ui.button, ui.label, etc.).

KEY FINDING: ElementFilter (used by user.should_see/find) does NOT support
HTMLElement._text content matching. It only checks TextElement.text,
ContentElement.content, and element.props — none of which HTMLElement uses.

WORKAROUNDS validated here:
1. Direct element tree traversal via client.layout.descendants()
2. .mark() for element identification (stored in _markers, which ElementFilter CAN check)
3. Custom helper functions for text content assertions
"""
import pytest

from nicegui import html, ui
from nicegui.testing import User

from ng_rdm.store import DictStore

from .conftest import (
    get_html_texts, html_should_see, html_should_see_async,
    html_should_not_see, find_html_elements_with_text,
)

pytestmark = pytest.mark.components


# ── 1. Basic html element visibility via custom helpers ──

async def test_html_text_via_helper(user: User):
    """Custom helper finds text inside html.span and html.div."""
    @ui.page('/')
    def page():
        html.span('Hello from span')
        html.div('Hello from div')

    await user.open('/')
    html_should_see(user, 'Hello from span')
    html_should_see(user, 'Hello from div')


async def test_html_not_see(user: User):
    """Custom helper confirms absent text is not found."""
    @ui.page('/')
    def page():
        html.span('Present')

    await user.open('/')
    html_should_see(user, 'Present')
    html_should_not_see(user, 'Absent text')


# ── 2. Mark-based finding (ElementFilter supports _markers) ──

async def test_find_by_mark(user: User):
    """Elements found by .mark() — ElementFilter checks _markers."""
    @ui.page('/')
    def page():
        result = html.div('')
        result.mark('result-output')

        def handle_click(_=None):
            result._text = 'marker clicked!'
            result.update()

        btn = html.button('Action').on('click', handle_click)
        btn.mark('action-btn')

    await user.open('/')
    user.find(marker='action-btn').click()
    # Verify via helper
    html_should_see(user, 'marker clicked!')


async def test_find_by_mark_with_inner_span(user: User):
    """Mark on parent button, click fires handler (RDM pattern)."""
    @ui.page('/')
    def page():
        result = html.div('waiting')
        result.mark('result')

        def handle_click(_=None):
            result._text = 'button clicked!'
            result.update()

        with html.button().on('click', handle_click) as btn:
            btn.mark('edit-btn')
            html.span('Edit')

    await user.open('/')
    user.find(marker='edit-btn').click()
    html_should_see(user, 'button clicked!')


# ── 3. Direct element tree access ──

async def test_element_tree_traversal(user: User):
    """Directly traverse element tree to inspect HTMLElement properties."""
    @ui.page('/')
    def page():
        html.span('Alice').mark('name-cell')
        html.span('30').mark('age-cell')

    await user.open('/')
    texts = get_html_texts(user)
    assert 'Alice' in texts
    assert '30' in texts


async def test_find_elements_with_text(user: User):
    """find_html_elements_with_text returns matching elements."""
    @ui.page('/')
    def page():
        html.span('Alice')
        html.span('Bob')
        html.span('Alice Jr')

    await user.open('/')
    alices = find_html_elements_with_text(user, 'Alice')
    assert len(alices) == 2  # 'Alice' and 'Alice Jr'


# ── 4. html.table rendering ──

async def test_html_table_content(user: User):
    """Content inside html.table structure is visible via helper."""
    @ui.page('/')
    def page():
        with html.table():
            with html.thead():
                with html.tr():
                    html.th('Name')
                    html.th('Age')
            with html.tbody():
                with html.tr():
                    html.td('Alice')
                    html.td('30')
                with html.tr():
                    html.td('Bob')
                    html.td('25')

    await user.open('/')
    html_should_see(user, 'Name')
    html_should_see(user, 'Alice')
    html_should_see(user, 'Bob')
    html_should_see(user, '30')


# ── 5. DictStore in page context ──

async def test_dictstore_in_page(user: User):
    """DictStore works within a NiceGUI page — async CRUD in page context."""
    store = DictStore()

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice'})
        await store.create_item({'name': 'Bob'})
        items = await store.read_items()
        for item in items:
            html.span(item['name'])

    await user.open('/')
    html_should_see(user, 'Alice')
    html_should_see(user, 'Bob')


# ── 6. @ui.refreshable works ──

async def test_refreshable_with_mark(user: User):
    """@ui.refreshable + mark-based click + async helper assertion."""
    counter = {'value': 0}

    @ui.page('/')
    def page():
        @ui.refreshable
        def counter_display():
            html.span(f'Count: {counter["value"]}')

        counter_display()

        def increment(_=None):
            counter['value'] += 1
            counter_display.refresh()

        html.button().on('click', increment).mark('inc-btn')

    await user.open('/')
    html_should_see(user, 'Count: 0')
    user.find(marker='inc-btn').click()
    await html_should_see_async(user, 'Count: 1')


# ── 7. Visibility binding ──

async def test_bind_visibility_with_helpers(user: User):
    """Verify bind_visibility_from works, tested via custom helpers."""
    @ui.page('/')
    def page():
        state = {'visible': False}
        panel = html.div('Hidden Panel')
        panel.bind_visibility_from(state, 'visible')

        def toggle(_=None):
            state['visible'] = not state['visible']

        html.button().on('click', toggle).mark('toggle-btn')
        html.span('Always Visible')

    await user.open('/')
    html_should_see(user, 'Always Visible')
    html_should_not_see(user, 'Hidden Panel')
    user.find(marker='toggle-btn').click()
    html_should_see(user, 'Hidden Panel')


# ── 8. ui elements still work normally ──

async def test_ui_elements_still_work(user: User):
    """Standard ui.* elements work with should_see/find as expected."""
    @ui.page('/')
    def page():
        state = {'name': ''}
        ui.label('Form Title')
        ui.input('Name').bind_value(state, 'name')

    await user.open('/')
    await user.should_see('Form Title')
    user.find(kind=ui.input).type('Test Name')


# ── 9. Mixed ui + html elements ──

async def test_mixed_ui_and_html(user: User):
    """ui.label visible via should_see, html.span via custom helper."""
    @ui.page('/')
    def page():
        ui.label('UI Label')
        html.span('HTML Span')
        ui.input('Name')

    await user.open('/')
    await user.should_see('UI Label')
    html_should_see(user, 'HTML Span')
    await user.should_see(kind=ui.input)


# ── 10. RDM-like table pattern ──

async def test_rdm_table_pattern(user: User):
    """Full RDM table pattern with marks for button interaction."""
    store = DictStore()
    edit_log: list[str] = []

    @ui.page('/')
    async def page():
        await store.create_item({'name': 'Alice', 'email': 'alice@test.com'})
        await store.create_item({'name': 'Bob', 'email': 'bob@test.com'})
        items = await store.read_items()

        with html.div().classes('rdm-table-card'):
            with html.table().classes('rdm-table'):
                with html.thead():
                    with html.tr():
                        html.th('Name')
                        html.th('Email')
                        html.th('')
                with html.tbody():
                    for i, row in enumerate(items):
                        name = row['name']
                        with html.tr():
                            html.td(name)
                            html.td(row['email'])
                            with html.td():
                                html.button().on(
                                    'click', lambda _, n=name: edit_log.append(n)
                                ).mark(f'edit-row-{i}')

    await user.open('/')
    html_should_see(user, 'Name')
    html_should_see(user, 'Alice')
    html_should_see(user, 'bob@test.com')

    # Click edit button for first row (Alice)
    user.find(marker='edit-row-0').click()
    assert edit_log == ['Alice']

    # Click edit button for second row (Bob)
    user.find(marker='edit-row-1').click()
    assert edit_log == ['Alice', 'Bob']
