"""
Logging configuration for the package.
"""

import logging

# Configure logger
logger = logging.getLogger('ng_loba')

def setup_logging(level=logging.INFO):
    """Set up logging configuration"""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.setLevel(level)
    
    # Prevent duplicate logging
    logger.propagate = False
    
    return logger
