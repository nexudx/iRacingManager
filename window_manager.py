#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Window management for the iRacing Manager.

This module is responsible for:
1. Finding windows belonging to specific processes
2. Minimizing windows with retries and specialized handling
3. Providing window manipulation utilities
"""

import time
import logging
from typing import List

from process_utils import WINDOWS_IMPORTS_AVAILABLE

# Set up logger
logger = logging.getLogger("WindowManager")

# Windows-specific imports (already checked in process_utils)
if WINDOWS_IMPORTS_AVAILABLE:
    import win32gui
    import win32con
    import win32process
    import psutil


class WindowManager:
    """
    Handles finding and manipulating windows for external processes.
    
    Provides methods to find windows by process ID, minimize windows, 
    and handle specialized window manipulation tasks.
    """
    
    def __init__(self):
        """Initialize the WindowManager."""
        pass
        
    def find_process_windows(self, pid: int) -> List[int]:
        """
        Finds all visible windows belonging to a specific process ID.
        
        Args:
            pid (int): Process ID to find windows for
            
        Returns:
            List[int]: List of window handles belonging to the process
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            return []

        windows = []
        try:
            def callback(hwnd, hwnds):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    try:
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == pid:
                            hwnds.append(hwnd)
                    except Exception:  # Ignore errors like permission denied
                        pass
                return True
            win32gui.EnumWindows(callback, windows)
        except Exception as e:
            logger.error(f"Error enumerating windows for PID {pid}: {e}")
        return windows

    def minimize_window(self, pid: int, program_name: str, max_attempts: int = 3, retry_delay: float = 0.5) -> bool:
        """
        Minimizes the window(s) of a process with multiple attempts.
        
        This method uses the Windows API to:
        1. Find all visible windows of the specified process
        2. Log each found window title
        3. Minimize the windows
        4. Check for successful minimization
        5. Make multiple attempts if needed

        Args:
            pid (int): Process ID whose windows should be minimized
            program_name (str): Name of the program for meaningful logging
            max_attempts (int): Maximum number of minimization attempts
            retry_delay (float): Wait time between attempts in seconds

        Returns:
            bool: True if at least one window was successfully minimized, otherwise False
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            logger.warning(f"Could not minimize window for '{program_name}': Windows modules not available.")
            return False

        success = False
        
        for attempt in range(1, max_attempts + 1):
            windows_found_this_attempt = False
            try:
                windows = self.find_process_windows(pid)
                if windows:
                    windows_found_this_attempt = True

                if not windows_found_this_attempt:
                    # Log warning only on the last attempt if no windows were ever found
                    if attempt == max_attempts and not success:  # 'success' tracks if windows were found in previous attempts
                        logger.warning(f"No visible windows found for '{program_name}' (PID: {pid}) after {max_attempts} attempts.")
                    else:
                        logger.debug(f"No visible windows found for '{program_name}' (Attempt {attempt}/{max_attempts}). Waiting and trying again.")
                        time.sleep(retry_delay)
                    continue

                # Minimize all found windows
                for hwnd in windows:
                    window_title = win32gui.GetWindowText(hwnd)
                    logger.info(f"Minimizing window: '{window_title}' for '{program_name}' (Attempt {attempt}/{max_attempts})")
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                
                # Check if minimization was successful
                time.sleep(0.5)  # Wait to give Windows time to respond
                all_minimized = True
                for hwnd in windows:
                    placement = win32gui.GetWindowPlacement(hwnd)
                    # SW_SHOWMINIMIZED (2) means the window is minimized
                    if placement[1] != win32con.SW_SHOWMINIMIZED:
                        all_minimized = False
                        break
                
                if all_minimized:
                    success = True
                    break
                elif attempt < max_attempts:
                    logger.debug(f"Not all windows for '{program_name}' were minimized. Trying again in {retry_delay} seconds.")
                    time.sleep(retry_delay)

            except Exception as e:
                logger.error(f"Error minimizing window for '{program_name}' (Attempt {attempt}/{max_attempts}): {e}")
        
        return success

    def minimize_all_windows_of_process(self, pid: int, program_name: str, is_oculus: bool = False, oculus_window_titles=None) -> bool:
        """
        Minimizes all visible windows of a specific process.
        
        Particularly useful for:
        - Programs that open multiple parallel windows
        - Programs that open new windows later
        
        Args:
            pid (int): Process ID of the program to monitor
            program_name (str): Name of the program for differentiated logging
            is_oculus (bool): Whether this is an Oculus process (for specialized handling)
            oculus_window_titles (list): List of possible Oculus window titles (required if is_oculus=True)

        Returns:
            bool: True if at least one window was found and minimized, otherwise False
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            return False
            
        try:
            windows = self.find_process_windows(pid)
            
            if not windows:
                return False
                
            # Minimize all found windows
            for hwnd in windows:
                window_title = win32gui.GetWindowText(hwnd)
                
                # Check if it's an Oculus main window
                is_oculus_main = is_oculus and oculus_window_titles and \
                                any(oculus_title in window_title for oculus_title in oculus_window_titles)

                if is_oculus_main:
                    logger.info(f"Oculus main window found: '{window_title}'. Minimizing it.")
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                else:
                    logger.info(f"Additional window found and minimizing: '{window_title}' for '{program_name}'")
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                
            return True
            
        except Exception as e:
            logger.error(f"Error minimizing all windows for '{program_name}': {e}")
            return False