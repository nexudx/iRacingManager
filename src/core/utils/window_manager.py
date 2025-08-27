#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Window management: find and minimize process windows."""

import time
import logging
from typing import List

from src.core.utils.process_utils import WINDOWS_IMPORTS_AVAILABLE

# Logger
logger = logging.getLogger("WindowManager")

# OS-specific imports (checked in process_utils)
if WINDOWS_IMPORTS_AVAILABLE:
    import win32gui
    import win32con
    import win32process
 

 
class WindowManager:
    """Finds and manipulates external process windows."""
    
    def __init__(self):
        """Initialize the WindowManager."""
        pass
        
    def find_process_windows(self, pid: int) -> List[int]:
        """Finds visible windows for a PID. Returns list of handles."""
        if not WINDOWS_IMPORTS_AVAILABLE:
            return []

        windows = []
        try:
            def callback(hwnd, hwnds): # EnumWindows callback
                # Checks visibility, title, and PID match.
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                    try:
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == pid: hwnds.append(hwnd)
                    except Exception: pass # Ignore errors (perms, closed window)
                return True # Continue
            win32gui.EnumWindows(callback, windows)
        except Exception as e:
            logger.error(f"Error enumerating windows for PID {pid}: {e}")
        return windows

    def minimize_window(self, pid: int, program_name: str, max_attempts: int = 3, retry_delay: float = 0.5) -> bool:
        """Minimizes process window(s) with retries. Returns True on success."""
        if not WINDOWS_IMPORTS_AVAILABLE:
            logger.warning(f"Could not minimize window for '{program_name}': Windows modules not available.")
            return False

        success = False
        
        for attempt in range(1, max_attempts + 1):
            windows_found_this_attempt = False
            try:
                windows = self.find_process_windows(pid)
                logger.debug(f"Attempt {attempt}/{max_attempts} for PID {pid} ('{program_name}'): Found windows: {windows}")
                if windows:
                    windows_found_this_attempt = True
                    logger.debug(f"Attempt {attempt}: windows_found_this_attempt = True. Proceeding to minimize.")
                else:
                    logger.debug(f"Attempt {attempt}: No windows found for PID {pid} ('{program_name}').")


                if not windows_found_this_attempt:
                    # This inner 'if' is redundant if the outer one is already true.
                    # if not windows_found_this_attempt:
                    logger.debug(f"Attempt {attempt}: windows_found_this_attempt is False. Checking retry conditions.")
                    # No windows found this attempt:
                    # Warn on last attempt if no prior success, else debug & retry.
                    if attempt == max_attempts and not success:
                        logger.warning(f"No windows for '{program_name}' (PID: {pid}) after {max_attempts} tries (outer check).")
                    else:
                        logger.debug(f"No windows for '{program_name}' (Attempt {attempt}/{max_attempts}). Retrying (outer check).")
                        time.sleep(retry_delay)
                    continue # Skip to next attempt
    
                # This block should only execute if windows_found_this_attempt is True
                logger.debug(f"Attempt {attempt}: Entering loop to minimize windows: {windows}")
                for hwnd_index, hwnd in enumerate(windows): # Minimize found windows
                    title = win32gui.GetWindowText(hwnd)
                    logger.info(f"Attempt {attempt}/{max_attempts}: Minimizing window {hwnd_index+1}/{len(windows)} (HWND: {hwnd}, Title: '{title}') for '{program_name}'")
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        logger.debug(f"Called ShowWindow(SW_MINIMIZE) for HWND: {hwnd}")
                    except Exception as e_minimize:
                        logger.error(f"Error calling ShowWindow(SW_MINIMIZE) for HWND {hwnd}: {e_minimize}")
                        continue # Try next window if one fails
                    
                time.sleep(0.5)  # Allow state update.
                all_minimized = True # Check success
                logger.debug(f"Attempt {attempt}: Checking if all windows are minimized.")
                for hwnd_index, hwnd in enumerate(windows):
                    try:
                        placement = win32gui.GetWindowPlacement(hwnd)
                        logger.debug(f"Window {hwnd_index+1}/{len(windows)} (HWND: {hwnd}) placement: {placement}")
                        # placement[1] == SW_SHOWMINIMIZED (2)
                        if placement[1] != win32con.SW_SHOWMINIMIZED:
                            logger.warning(f"Window (HWND: {hwnd}, Title: '{win32gui.GetWindowText(hwnd)}') not minimized. Placement state: {placement[1]}")
                            all_minimized = False; break
                    except Exception as e_placement:
                        logger.error(f"Error getting placement for HWND {hwnd}: {e_placement}")
                        all_minimized = False; break # Assume not minimized if error
                    
                if all_minimized:
                    logger.info(f"Attempt {attempt}: All windows for '{program_name}' successfully minimized.")
                    success = True; break
                elif attempt < max_attempts:
                    logger.debug(f"Attempt {attempt}: Not all windows for '{program_name}' minimized. Retrying.")
                    time.sleep(retry_delay)
                else: # Last attempt and not all_minimized
                    logger.warning(f"Failed to minimize all windows for '{program_name}' after {max_attempts} attempts.")
            except Exception as e:
                logger.error(f"Error minimizing window for '{program_name}' (Attempt {attempt}/{max_attempts}): {e}")
        
        return success