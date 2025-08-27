#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Common utilities for iRacing Manager process management."""

import logging
import os
import sys

# Logger
logger = logging.getLogger("ProcessUtils")

# OS-specific imports
try:
    import win32gui
    import win32con
    import win32process
    import psutil
    WINDOWS_IMPORTS_AVAILABLE = True
except ImportError:
    WINDOWS_IMPORTS_AVAILABLE = False
    # Warning in check_windows_requirements()


def check_windows_requirements() -> bool:
    """Checks for Windows-specific modules (pywin32, psutil) and OS. Returns bool."""
    if not WINDOWS_IMPORTS_AVAILABLE:
        logger.warning("Windows-specific modules (win32gui, win32con, win32process, psutil) not available.")
        logger.warning("Please install these modules for full functionality:")
        logger.warning("pip install pywin32 psutil")
    
    if sys.platform != "win32": # Windows only
        logger.error("This program is Windows-only.")
        return False
    
    return True