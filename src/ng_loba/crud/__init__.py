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


__all__ = [
    'create_crud_table',
    'CrudTable',
    'DirectEditTable',
    'ExplicitEditTable',
    'Column',
    'TableConfig',
    'confirm_dialog',
    'page_init',
]
