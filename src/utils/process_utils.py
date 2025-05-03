#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common utilities for process management in iRacing Manager.

This module provides utility functions and shared constants used across
the process management components of the system.
"""

import logging
import os
import sys

# Set up logger
logger = logging.getLogger("ProcessUtils")

# Windows-specific imports
try:
    import win32gui
    import win32con
    import win32process
    import psutil
    WINDOWS_IMPORTS_AVAILABLE = True
except ImportError:
    WINDOWS_IMPORTS_AVAILABLE = False
    # Warning logged in _check_requirements


def check_windows_requirements() -> bool:
    """
    Checks if Windows-specific requirements are met.
    
    Returns:
        bool: True if all requirements are met, False otherwise
    """
    if not WINDOWS_IMPORTS_AVAILABLE:
        logger.warning("Windows-specific modules (win32gui, win32con, win32process, psutil) not available.")
        logger.warning("Please install these modules for full functionality:")
        logger.warning("pip install pywin32 psutil")
    
    # Check if we are running on Windows
    if sys.platform != "win32":
        logger.error("This program is designed only for Windows systems.")
        return False
    
    return True