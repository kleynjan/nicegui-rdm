"""
CRUD components for data management.
"""
from nicegui import ui
from .table import (
    create_crud_table,
    CrudTable,
    DirectEditTable,
    ExplicitEditTable,
    Column,
    TableConfig,
    confirm_dialog,
)

def page_init():
    """
    Initialize page styles and settings for the CRUD module.
    """
    import os
    styles_path = os.path.join(os.path.dirname(__file__), 'crud.scss')
    with open(styles_path) as f:
        print("Loading CRUD styles from", styles_path)
        ui.add_scss(f.read())
    # ui.colors(primary="rgb(0,82,194)", secondary="#53B689", accent="#111B1E", positive="#53B689")

def get_crud_css():
    """
    Return the CSS styles for the CRUD module.
    """
    import os

    # read and return the local crud.css file as a string
    css_path = os.path.join(os.path.dirname(__file__), 'crud.css')
    with open(css_path) as f:
        return f.read()

    # return sass.compile(filename=os.path.join(os.path.dirname(__file__), 'crud.scss'))

__all__ = [
    'create_crud_table',
    'CrudTable',
    'DirectEditTable',
    'ExplicitEditTable',
    'Column',
    'TableConfig',
    'confirm_dialog',
    'page_init',
    'get_crud_css',
]
