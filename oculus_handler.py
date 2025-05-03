#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Oculus-specific handling for the iRacing Manager.

This module is responsible for specialized handling of Oculus Client processes,
including monitoring threads, window detection, and minimization strategies.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, Callable

from process_utils import WINDOWS_IMPORTS_AVAILABLE
from window_manager import WindowManager

# Set up logger
logger = logging.getLogger("OculusHandler")

# Windows-specific imports (already checked in process_utils)
if WINDOWS_IMPORTS_AVAILABLE:
    import win32gui
    import win32con
    import psutil

# --- Constants ---
OCULUS_CLIENT_NAME = "Oculus Client"
OCULUS_WINDOW_TITLES = [
    "Oculus", "Meta Quest", "Meta Link", "Meta Quest Link",
    "Oculus App", "Meta App", "Meta Quest App"
]
# --- End Constants ---


class OculusHandler:
    """
    Handles specialized Oculus Client operations.
    
    Provides methods for monitoring and minimizing Oculus windows,
    which have special behavior compared to regular applications.
    """
    
    # Constants for Oculus monitoring thread
    OCULUS_MONITOR_INITIAL_DELAYS = [2, 4, 6]  # Seconds
    OCULUS_MONITOR_POLL_INTERVAL = 2.0  # Seconds
    OCULUS_MONITOR_MAX_ATTEMPTS = 30  # Max attempts after initial delays
    
    def __init__(self):
        """Initialize the OculusHandler."""
        self.window_manager = WindowManager()
        # Dictionary to store active window monitoring threads and their control flags
        self._window_monitor_threads: Dict[str, Dict[str, Any]] = {}
        self._monitor_thread_lock = threading.Lock()  # Lock for accessing the threads dict
    
    def start_oculus_monitor_thread(self, program_name: str, pid: int) -> None:
        """
        Starts a background thread to monitor and minimize Oculus Client windows.

        Handles the complex startup sequence of Oculus by periodically checking
        for its windows and attempting minimization.

        Args:
            program_name (str): Should be OCULUS_CLIENT_NAME.
            pid (int): Process ID of the Oculus Client.
        """
        with self._monitor_thread_lock:
            # Stop and join existing thread for this program if running
            if program_name in self._window_monitor_threads:
                existing_thread_data = self._window_monitor_threads[program_name]
                if existing_thread_data.get("running"):
                    logger.info(f"Stopping existing monitor thread for '{program_name}'...")
                    existing_thread_data["stop_event"].set()  # Signal thread to stop
                    thread_to_join = existing_thread_data.get("thread")
                    if thread_to_join and thread_to_join.is_alive():
                        thread_to_join.join(timeout=self.OCULUS_MONITOR_POLL_INTERVAL + 1)  # Wait slightly longer than poll interval
                        if thread_to_join.is_alive():
                            logger.warning(f"Existing monitor thread for '{program_name}' did not stop gracefully.")
                # Remove old entry regardless of whether it stopped gracefully
                del self._window_monitor_threads[program_name]

            # Create new control event and data for the thread
            stop_event = threading.Event()
            thread_data = {
                "thread": None,
                "stop_event": stop_event,
                "running": True  # Indicates the thread *should* be running
            }
            self._window_monitor_threads[program_name] = thread_data  # Store immediately

        def monitor_thread_func():
            """Target function for the Oculus monitoring thread."""
            logger.info(f"Starting Oculus monitor thread for PID {pid}...")
            minimized_successfully = False
            attempt_counter = 0

            try:
                # --- Initial checks with increasing delays ---
                for delay in self.OCULUS_MONITOR_INITIAL_DELAYS:
                    if stop_event.is_set(): break  # Check for stop signal
                    logger.debug(f"Oculus monitor (PID {pid}): Waiting {delay}s...")
                    stop_event.wait(delay)  # Wait for delay or stop signal
                    if stop_event.is_set(): break

                    logger.debug(f"Oculus monitor (PID {pid}): Attempting minimization after {delay}s delay.")
                    if self._minimize_oculus_windows(pid):
                        logger.info(f"Oculus windows (PID {pid}) minimized during initial delay phase ({delay}s).")
                        minimized_successfully = True
                        break  # Exit loop if successful

                # --- Continuous polling phase ---
                while not stop_event.is_set() and not minimized_successfully and attempt_counter < self.OCULUS_MONITOR_MAX_ATTEMPTS:
                    # Check if the main process still exists (optional but good practice)
                    try:
                        if not psutil.pid_exists(pid):
                            logger.info(f"Oculus process (PID {pid}) no longer exists. Stopping monitor.")
                            break
                    except Exception as e:
                        logger.warning(f"Error checking Oculus PID {pid} existence: {e}. Continuing monitor.")

                    logger.debug(f"Oculus monitor (PID {pid}): Polling attempt {attempt_counter + 1}/{self.OCULUS_MONITOR_MAX_ATTEMPTS}.")
                    if self._minimize_oculus_windows(pid):
                        logger.info(f"Oculus windows (PID {pid}) minimized during polling phase (Attempt {attempt_counter + 1}).")
                        minimized_successfully = True
                        break  # Exit loop if successful

                    attempt_counter += 1
                    stop_event.wait(self.OCULUS_MONITOR_POLL_INTERVAL)  # Wait for interval or stop signal

            except Exception as e:
                logger.error(f"Error in Oculus monitor thread for PID {pid}: {e}", exc_info=True)
            finally:
                # --- Cleanup ---
                with self._monitor_thread_lock:
                    # Check if this thread's data is still the current one before modifying 'running'
                    current_data = self._window_monitor_threads.get(program_name)
                    if current_data and current_data["stop_event"] == stop_event:
                        current_data["running"] = False  # Mark as no longer running
                    else:
                        logger.warning(f"Oculus monitor thread (PID {pid}) finished, but its data was already replaced or removed.")

                if not minimized_successfully and attempt_counter >= self.OCULUS_MONITOR_MAX_ATTEMPTS:
                    logger.warning(f"Oculus monitor (PID {pid}): Failed to minimize windows after {self.OCULUS_MONITOR_MAX_ATTEMPTS} polling attempts.")
                elif not minimized_successfully and not stop_event.is_set():
                    # Only log if not stopped externally and not successful
                    logger.warning(f"Oculus monitor (PID {pid}): Exited loop unexpectedly before success or max attempts.")

                logger.info(f"Oculus monitor thread for PID {pid} finished.")

        # --- Start the thread ---
        try:
            thread = threading.Thread(target=monitor_thread_func, daemon=True)
            thread.start()
            # Store the thread object itself in the dictionary
            with self._monitor_thread_lock:
                # Ensure the entry still exists and hasn't been replaced
                if program_name in self._window_monitor_threads and self._window_monitor_threads[program_name]["stop_event"] == stop_event:
                    self._window_monitor_threads[program_name]["thread"] = thread
                else:
                    logger.warning(f"Could not store thread object for '{program_name}': Entry was modified or removed.")
                    # If the entry was removed, the thread we just started might become orphaned.
                    # Signal it to stop just in case.
                    stop_event.set()

        except Exception as e:
            logger.error(f"Failed to start Oculus monitor thread for PID {pid}: {e}")
            # Clean up the entry if thread failed to start
            with self._monitor_thread_lock:
                if program_name in self._window_monitor_threads and self._window_monitor_threads[program_name]["stop_event"] == stop_event:
                    del self._window_monitor_threads[program_name]

    def _minimize_oculus_windows(self, pid: int) -> bool:
        """
        Specialized function for finding and minimizing Oculus windows.
        
        This function differs from normal window minimization through:
        1. Use of a list of known Oculus window titles for precise detection
        2. Special handling for main window vs. side windows
        3. Alternative minimization method (PostMessage) for stubborn windows
        4. Detailed logging of found windows and minimization measures
        
        Args:
            pid (int): Process ID of the Oculus Client
            
        Returns:
            bool: True if Oculus main window was found and minimized, otherwise False
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            return False
            
        try:
            all_process_windows = self.window_manager.find_process_windows(pid)
            if not all_process_windows:
                return False  # No windows found for this PID

            oculus_main_window = None
            other_windows = []
            minimized_any = False  # Track if we successfully minimized at least one window

            # Separate main window from others based on title
            for hwnd in all_process_windows:
                title = win32gui.GetWindowText(hwnd)
                # Use constant for checking titles
                is_main = any(oculus_title in title for oculus_title in OCULUS_WINDOW_TITLES)
                if is_main:
                    # Prioritize the first main window found if multiple match
                    if oculus_main_window is None:
                        oculus_main_window = hwnd
                else:
                    other_windows.append(hwnd)

            # If a main window was found, minimize it first
            if oculus_main_window:
                hwnd = oculus_main_window
                window_title = win32gui.GetWindowText(hwnd)
                logger.info(f"Oculus main window found: '{window_title}'. Minimizing...")
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    time.sleep(0.1)  # Give it a moment

                    # Check if minimization was successful
                    placement = win32gui.GetWindowPlacement(hwnd)
                    if placement[1] != win32con.SW_SHOWMINIMIZED:
                        # Alternative method for difficult windows
                        logger.info("First minimization method failed for main window, trying alternative...")
                        win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MINIMIZE, 0)
                        time.sleep(0.1)  # Give it another moment
                        # Re-check placement after alternative method
                        placement = win32gui.GetWindowPlacement(hwnd)
                        if placement[1] == win32con.SW_SHOWMINIMIZED:
                            minimized_any = True
                        else:
                            logger.warning(f"Alternative minimization method also failed for '{window_title}'.")
                    else:
                        minimized_any = True
                except Exception as e:
                    logger.error(f"Error minimizing the Oculus main window '{window_title}': {e}")

            # Minimize other windows as well
            if other_windows:
                logger.info(f"Found {len(other_windows)} other Oculus window(s) to minimize.")
                for hwnd in other_windows:
                    window_title = win32gui.GetWindowText(hwnd)
                    logger.info(f"Minimizing Oculus side window: '{window_title}'...")
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        minimized_any = True  # Count success even if main window failed
                    except Exception as e:
                        logger.error(f"Error minimizing Oculus side window '{window_title}': {e}")

            return minimized_any  # Return True if any window (main or side) was successfully minimized

        except Exception as e:
            logger.error(f"Error during Oculus window search/minimization for PID {pid}: {e}")
            return False
            
    def stop_all_monitors(self) -> None:
        """
        Stops all running Oculus monitor threads.
        """
        with self._monitor_thread_lock:
            if not self._window_monitor_threads:
                return
                
            for program_name, thread_data in list(self._window_monitor_threads.items()):
                if thread_data.get("running"):
                    logger.info(f"Stopping monitor thread for '{program_name}'...")
                    thread_data["stop_event"].set()
                    thread = thread_data.get("thread")
                    if thread and thread.is_alive():
                        try:
                            thread.join(timeout=1.0)
                        except Exception as e:
                            logger.error(f"Error joining thread for '{program_name}': {e}")
            
            # Clear the dictionary after stopping all threads
            self._window_monitor_threads.clear()