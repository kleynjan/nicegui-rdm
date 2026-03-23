"""
Page initialization utilities for ng_rdm.
"""


def init_page() -> None:
    """
    Initialize the page with styles and settings from all ng_rdm modules.
    """

    # Call module-specific initialization functions
    from ng_rdm import components
    components.rdm_init()

    # Add more module initializations here as needed
