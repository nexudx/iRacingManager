#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock Windows Implementation for iRacing Manager Tests.

This module provides mock implementations of Windows-related functionality:
- win32gui functions for window management
- WindowManager with minimization tracking
- Mock window handles and states

This allows testing the window management features without actual Windows API calls.
"""

import logging
from typing import Dict, List, Any, Optional, Set

# Set up logger
logger = logging.getLogger("MockWindows")

# --- Mock Windows Constants ---
SW_MINIMIZE = 6
SW_SHOWMINIMIZED = 2
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020
# --- End Constants ---

class MockWindowManager:
    """
    Static manager class for tracking mock windows and their states.
    
    This class maintains:
    - Window handles (hwnd) and their association with process IDs
    - Window titles and states (minimized or not)
    - Methods to find and manipulate window state
    """
    
    _next_hwnd = 100000  # Start window handles at 100000
    _windows = {}        # Dict mapping hwnds to window info
    _pid_to_hwnds = {}   # Dict mapping PIDs to sets of window handles
    
    @classmethod
    def reset(cls):
        """Reset all tracked windows."""
        cls._windows = {}
        cls._pid_to_hwnds = {}
        cls._next_hwnd = 100000
        logger.debug("MockWindowManager reset")
    
    @classmethod
    def create_window(cls, pid: int, title: str = "Mock Window"):
        """Create a new mock window for a process."""
        hwnd = cls._next_hwnd
        cls._next_hwnd += 1
        
        # Store window information
        cls._windows[hwnd] = {
            'pid': pid,
            'title': title,
            'minimized': False
        }
        
        # Add to PID mapping
        if pid not in cls._pid_to_hwnds:
            cls._pid_to_hwnds[pid] = set()
        cls._pid_to_hwnds[pid].add(hwnd)
        
        logger.debug(f"Created mock window: hwnd={hwnd}, pid={pid}, title='{title}'")
        return hwnd
    
    @classmethod
    def find_process_windows(cls, pid: int) -> List[int]:
        """Find all windows belonging to a specific process."""
        return list(cls._pid_to_hwnds.get(pid, set()))
    
    @classmethod
    def get_window_text(cls, hwnd: int) -> str:
        """Get the title of a window."""
        if hwnd in cls._windows:
            return cls._windows[hwnd]['title']
        return ""
    
    @classmethod
    def show_window(cls, hwnd: int, cmd: int) -> bool:
        """Simulate ShowWindow function to change window state."""
        if hwnd not in cls._windows:
            return False
        
        # Only handle minimization commands
        if cmd == SW_MINIMIZE:
            cls._windows[hwnd]['minimized'] = True
            logger.debug(f"Window {hwnd} minimized")
            return True
        
        return True
    
    @classmethod
    def post_message(cls, hwnd: int, msg: int, wparam: int, lparam: int) -> bool:
        """Simulate PostMessage function for sending window messages."""
        if hwnd not in cls._windows:
            return False
        
        # Handle window minimize command
        if msg == WM_SYSCOMMAND and wparam == SC_MINIMIZE:
            cls._windows[hwnd]['minimized'] = True
            logger.debug(f"Window {hwnd} minimized via WM_SYSCOMMAND")
            return True
        
        return True
    
    @classmethod
    def get_window_placement(cls, hwnd: int) -> tuple:
        """Simulate GetWindowPlacement to check if a window is minimized."""
        if hwnd not in cls._windows:
            raise ValueError(f"Window handle {hwnd} not found")
        
        # Return tuple with minimized flag (index 1 holds the show state)
        # (flags, showCmd, min_pos, max_pos, normal_pos)
        show_cmd = SW_SHOWMINIMIZED if cls._windows[hwnd]['minimized'] else 1
        return (0, show_cmd, (0, 0), (0, 0), (0, 0, 0, 0))
    
    @classmethod
    def is_window_minimized(cls, hwnd: int) -> bool:
        """Check if a window is minimized."""
        if hwnd not in cls._windows:
            return False
        return cls._windows[hwnd]['minimized']


# --- Mock functions for win32gui ---

def mock_FindWindow(class_name, window_name):
    """Mock for win32gui.FindWindow."""
    # Just return None for now - we'll use more specific methods
    return None

def mock_GetWindowText(hwnd):
    """Mock for win32gui.GetWindowText."""
    return MockWindowManager.get_window_text(hwnd)

def mock_ShowWindow(hwnd, cmd):
    """Mock for win32gui.ShowWindow."""
    return MockWindowManager.show_window(hwnd, cmd)

def mock_PostMessage(hwnd, msg, wparam, lparam):
    """Mock for win32gui.PostMessage."""
    return MockWindowManager.post_message(hwnd, msg, wparam, lparam)

def mock_GetWindowPlacement(hwnd):
    """Mock for win32gui.GetWindowPlacement."""
    return MockWindowManager.get_window_placement(hwnd)

def setup_win32_mocks():
    """Set up all win32gui mocks for testing."""
    # Reset the window manager
    MockWindowManager.reset()
    
    # Patch win32gui functions
    import win32gui
    import win32con
    
    # Store original functions for restoration later
    original_functions = {
        'FindWindow': getattr(win32gui, 'FindWindow', None),
        'GetWindowText': getattr(win32gui, 'GetWindowText', None),
        'ShowWindow': getattr(win32gui, 'ShowWindow', None),
        'PostMessage': getattr(win32gui, 'PostMessage', None),
        'GetWindowPlacement': getattr(win32gui, 'GetWindowPlacement', None)
    }
    
    # Replace with mock implementations
    if hasattr(win32gui, 'FindWindow'):
        win32gui.FindWindow = mock_FindWindow
    if hasattr(win32gui, 'GetWindowText'):
        win32gui.GetWindowText = mock_GetWindowText
    if hasattr(win32gui, 'ShowWindow'):
        win32gui.ShowWindow = mock_ShowWindow
    if hasattr(win32gui, 'PostMessage'):
        win32gui.PostMessage = mock_PostMessage
    if hasattr(win32gui, 'GetWindowPlacement'):
        win32gui.GetWindowPlacement = mock_GetWindowPlacement
    
    return original_functions

def restore_win32_originals(original_functions):
    """Restore original win32gui functions after testing."""
    import win32gui
    
    # Restore all patched functions
    for func_name, original_func in original_functions.items():
        if original_func is not None and hasattr(win32gui, func_name):
            setattr(win32gui, func_name, original_func)