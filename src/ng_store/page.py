"""
Page initialization utilities for ng_loba.
"""

from typing import Any

def init_page() -> None:
    """
    Initialize the page with styles and settings from all ng_loba modules.
    """

    # Call module-specific initialization functions
    from ng_loba import crud
    crud.page_init()

    # Add more module initializations here as needed
    # For example:
    # from ng_loba.another_module import init_page_module
    # init_page_module(ui)
