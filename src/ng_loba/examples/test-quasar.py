import sass
from nicegui import ui

scss = """
@layer quasar_importants {
    $my-bg-color: red;
    .crudy-column-button {
        background-color: $my-bg-color !important;
    }
}
"""

# this works - add_css does not support scss
css = sass.compile(string=scss)
ui.add_css(css)

# # this does not work
# ui.add_scss(scss)

ui.add_head_html("""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
""")

# ui.button(icon="delete").classes("crudy-column-button")
ui.button("test").classes("crudy-column-button")

ui.run()
