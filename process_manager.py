#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Process manager for the iRacing Manager.

This module is responsible for:
1. Starting external programs (including output redirection)
2. Minimizing program windows (with special handling for different program types)
3. Monitoring and minimizing windows that appear later
4. Clean termination of all started programs

The main class ProcessManager provides an abstract interface for process management,
independent from the rest of the iRacing Manager system.
"""

import threading
import subprocess
import time
import logging
import os
import signal
import sys
from typing import Dict, List, Any, Optional, Tuple

# Windows-specific imports
try:
    import win32gui
    import win32con
    import win32process
    import psutil
    WINDOWS_IMPORTS_AVAILABLE = True
except ImportError:
    WINDOWS_IMPORTS_AVAILABLE = False
    # Warning logged later in _check_requirements if needed

# Set up logger - Configuration should be done in the main entry point
logger = logging.getLogger("ProcessManager")

# --- Constants ---
OCULUS_CLIENT_NAME = "Oculus Client"
OCULUS_WINDOW_TITLES = [
    "Oculus", "Meta Quest", "Meta Link", "Meta Quest Link",
    "Oculus App", "Meta App", "Meta Quest App"
]
# --- End Constants ---


class ProcessManager:
    """
    Main class for managing processes for the iRacing Manager.

    Provides methods to start, minimize (including retries and special handling),
    and terminate external programs based on configuration.
    Requires Windows-specific libraries (pywin32, psutil) for full functionality.
    """

    def __init__(self):
        """
        Initializes the ProcessManager.
        """
        self.processes: Dict[str, Dict[str, Any]] = {}
        self.non_minimized_windows: Dict[str, Dict[str, Any]] = {}
        self._terminated_programs: set[str] = set() # Use instance variable
        self._check_requirements()

    def _check_requirements(self) -> None:
        """
        Checks if all required modules are available.
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            logger.warning("Windows-specific modules (win32gui, win32con, win32process, psutil) not available.")
            logger.warning("Please install these modules for full functionality:")
            logger.warning("pip install pywin32 psutil")
        
        # Check if we are running on Windows
        if sys.platform != "win32":
            logger.error("This program is designed only for Windows systems.")
            sys.exit(1)

    def start_program(self, program_config: Dict[str, Any]) -> Tuple[bool, Optional[subprocess.Popen]]:
        """
        Starts a program based on the configuration and minimizes it if necessary.

        This method:
        1. Extracts path and parameters from the configuration
        2. Checks if the executable file exists
        3. Starts the process with redirected output
        4. Performs special handling for Oculus Client (monitoring thread)
        5. Minimizes the program window if required
        6. Stores process information for later use

        Args:
            program_config (Dict[str, Any]): The program configuration from config.json
                                            with parameters like "name", "path", "arguments", etc.

        Returns:
            Tuple[bool, Optional[subprocess.Popen]]:
                - True and process object on success
                - False and None on error
        """
        name = program_config["name"]
        path = program_config["path"]
        arguments = program_config.get("arguments", "").strip()
        is_main = program_config.get("is_main", False)

        # Check if the executable file exists
        if not os.path.exists(path):
            logger.error(f"Could not start '{name}'. Path does not exist: {path}")
            return False, None

        try:
            cmd = [path]
            if arguments:
                cmd += arguments.split()
            
            logger.info(f"Starting program: {name}")
            
            # Redirect the output for all programs to avoid disruptive console messages.
            # TODO: Consider making output redirection configurable (e.g., via config.json)
            # Use subprocess.DEVNULL for cleaner output redirection (Python 3.3+)
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW # Attempt to prevent console window flashing
            )

            # Special handling for Oculus Client - start monitoring thread
            # Note: This complex monitoring will be refactored later.
            if name == OCULUS_CLIENT_NAME:
                logger.info(f"Special handling for {OCULUS_CLIENT_NAME} (PID: {proc.pid}). Starting monitor thread.")
                # Give Oculus a moment to potentially create its initial process structures
                time.sleep(1.0) # Increased slightly
                self._start_oculus_monitor_thread(name, proc.pid)
            else:
                # Standard wait for other programs to potentially create windows
                time.sleep(0.5) # Keep short wait for non-Oculus

            # Minimize the window if it's not the main program
            was_minimized = True
            if not is_main:
                # Check if the program is marked as systray_only
                if program_config.get("systray_only", False):
                    logger.info(f"Program '{name}' starts directly in the system tray, skipping minimization.")
                else:
                    was_minimized = self._minimize_window(proc.pid, name)
                    if not was_minimized:
                        # Note that the window should be minimized later
                        self.non_minimized_windows[name] = {"pid": proc.pid, "has_splash_screen": program_config.get("has_splash_screen", False)}
            
            # Store process information
            self.processes[name] = {
                "process": proc,
                "pid": proc.pid,
                "config": program_config,
                "was_minimized": was_minimized
            }
            
            logger.info(f"Program '{name}' successfully started (PID: {proc.pid})")
            return True, proc
            
        except Exception as e:
            logger.error(f"Error starting '{name}': {e}")
            return False, None

    def _find_process_windows(self, pid: int) -> List[int]:
        """Finds all visible windows belonging to a specific process ID."""
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
                    except Exception: # Ignore errors like permission denied
                        pass
                return True
            win32gui.EnumWindows(callback, windows)
        except Exception as e:
            logger.error(f"Error enumerating windows for PID {pid}: {e}")
        return windows

    def _minimize_window(self, pid: int, program_name: str, max_attempts: int = 3, retry_delay: float = 0.5) -> bool:
        """
        Minimizes the window(s) of a process with multiple attempts.
        
        This method uses the Windows API to:
        1. Find all visible windows of the specified process
        2. Log each found window title
        3. Minimize the windows
        4. Check for successful minimization
        5. Make multiple attempts if needed

        The method uses EnumWindows to iterate through all open windows
        and checks which ones belong to the specified process.

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
                windows = self._find_process_windows(pid)
                if windows:
                    windows_found_this_attempt = True

                if not windows_found_this_attempt:
                    # Log warning only on the last attempt if no windows were ever found
                    if attempt == max_attempts and not success: # 'success' tracks if windows were found in previous attempts
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
                # No delay needed anymore
        
        return success

    def retry_minimize_all(self) -> None:
        """
        Attempts to minimize programs whose windows were not found or minimized initially.

        Iterates through the list of programs marked as not minimized and calls
        `_minimize_window` again for each.
        """
        if not self.non_minimized_windows:
            logger.debug("No programs pending retry minimization.")
            return

        logger.info(f"Retrying minimization for {len(self.non_minimized_windows)} program(s)...")

        successfully_minimized_this_round = []

        # Iterate over a copy of the items, as we might modify the dict
        for name, info in list(self.non_minimized_windows.items()):
            pid = info.get("pid")
            if pid is None:
                 logger.warning(f"Skipping retry for '{name}': PID missing.")
                 # Remove from retry list if PID is missing
                 if name in self.non_minimized_windows:
                     del self.non_minimized_windows[name]
                 continue

            # Check if the process still exists before retrying
            try:
                 if not psutil.pid_exists(pid):
                      logger.info(f"Skipping retry for '{name}' (PID: {pid}): Process no longer exists.")
                      # Remove from retry list if process is gone
                      if name in self.non_minimized_windows:
                          del self.non_minimized_windows[name]
                      continue
            except Exception as e:
                 logger.warning(f"Error checking PID existence for '{name}' (PID: {pid}): {e}. Skipping retry.")
                 if name in self.non_minimized_windows:
                     del self.non_minimized_windows[name]
                 continue


            logger.info(f"Retrying minimization for '{name}' (PID: {pid})...")

            # Call the main minimize function again with appropriate attempts/delay
            # Note: Oculus specific logic (_minimize_oculus_windows) is NOT called here anymore.
            # The standard _minimize_window will handle it. If Oculus needs more specialized
            # retry logic, it should be handled within its dedicated monitoring/minimization functions.
            if self._minimize_window(pid, name, max_attempts=8, retry_delay=1.5): # More attempts/delay for retry
                successfully_minimized_this_round.append(name)
                if name in self.processes:
                    self.processes[name]["was_minimized"] = True
            else:
                # Log failure for this specific program during retry
                logger.warning(f"Retry minimization failed for '{name}' (PID: {pid}).")


        # Remove successfully minimized programs from the retry list
        for name in successfully_minimized_this_round:
            if name in self.non_minimized_windows:
                del self.non_minimized_windows[name]

        # Log final status
        if self.non_minimized_windows:
            remaining_names = list(self.non_minimized_windows.keys())
            logger.warning(f"{len(self.non_minimized_windows)} program(s) remain unminimized after retry: {remaining_names}")
        else:
            logger.info("Retry minimization round completed. All pending programs minimized or removed.")


    # _terminated_programs moved to __init__ as self._terminated_programs

    def terminate_program(self, program_name: str) -> bool:
        """
        Terminates a program by its name with clean error handling.

        This method ensures reliable termination through:
        1. Checking if the program has already been terminated (prevents double attempts)
        2. Using psutil for gentle termination with terminate()
        3. Falling back to more aggressive kill() method if terminate() doesn't work
        4. Clean removal of all references from internal lists
        5. Logging of the termination process

        Args:
            program_name (str): Name of the program to terminate (as defined in config.json)

        Returns:
            bool: True if the program was successfully terminated or was already terminated,
                  False if errors occurred during termination.
        """
        # Check if the program has already been terminated
        if program_name in self._terminated_programs:
            logger.debug(f"Program '{program_name}' already marked as terminated.")
            return True

        if program_name not in self.processes:
            logger.warning(f"Cannot terminate '{program_name}': Not found in the active process list.")
            return False

        # Mark program as "being terminated" immediately to prevent race conditions
        self._terminated_programs.add(program_name)

        process_info = self.processes.get(program_name) # Use get for safety, though checked above
        if not process_info: # Should not happen due to check above, but defensive
             logger.error(f"Internal error: Process info for '{program_name}' disappeared unexpectedly.")
             return False

        proc = process_info["process"]
        pid = process_info["pid"]

        try:
            logger.info(f"Terminating program: {program_name} (PID: {pid})")
            
            # Try to terminate the process gently first
            if proc.poll() is None:  # Process is still running
                if WINDOWS_IMPORTS_AVAILABLE:
                    try:
                        process = psutil.Process(pid)
                        process.terminate()  # Send SIGTERM
                        
                        # We rely on terminating without waiting
                        
                        # If the process is still running, force termination
                        if proc.poll() is None:
                            process.kill()  # Send SIGKILL
                    except psutil.NoSuchProcess:
                        # Process already no longer exists
                        pass
                else:
                    # Fallback if psutil is not available - non-blocking
                    logger.warning("psutil not available, using basic terminate/kill.")
                    try:
                        proc.terminate() # Send SIGTERM
                        # Don't wait here, let cleanup proceed. If it doesn't exit,
                        # subsequent checks or system cleanup will handle it.
                        # Consider adding kill() immediately after if terminate is unreliable.
                        # proc.kill() # Optional: Force kill immediately after terminate
                    except OSError as e:
                        # Ignore errors if process already exited
                        logger.debug(f"OS error during fallback termination for '{program_name}': {e}")
                        pass

            # Remove the program from the active list *after* attempting termination
            if program_name in self.processes:
                del self.processes[program_name]
            
            # If the program is in the non-minimized list, remove it from there too
            if program_name in self.non_minimized_windows:
                del self.non_minimized_windows[program_name]
                
            return True
            
        except Exception as e:
            logger.error(f"Error terminating '{program_name}': {e}")
            
            # Even in case of error, remove from the list to avoid repeated termination attempts
            if program_name in self.processes:
                del self.processes[program_name]
            if program_name in self.non_minimized_windows:
                del self.non_minimized_windows[program_name]
                
            return False

    def terminate_all_programs(self) -> None:
        """
        Terminates all started programs cleanly and in the correct order.
        
        This method:
        1. Checks if any programs have been started at all to avoid unnecessary actions
        2. Creates a copy of the program list, since elements are removed during iteration
        3. Terminates each program individually with error handling
        4. Logs the progress and completion of the termination process
        5. Resets all internal state lists
        
        The method is idempotent and can be called multiple times without causing problems.
        """
        if not self.processes:
            # If no programs are left in the list, do nothing
            return
        
        logger.info("Terminating all started programs...")
        
        # Copy the key list since we'll be removing elements during iteration
        program_names = list(self.processes.keys())
        
        for name in program_names:
            # Check if the program is still in the list (could have been removed by another thread)
            if name in self.processes and name not in self._terminated_programs:
                self.terminate_program(name)
        
        # After termination, ensure all lists are actually empty
        self.processes = {}
        self.non_minimized_windows = {}
        
        logger.info("All programs have been terminated.")

    def is_program_running(self, program_name: str) -> bool:
        """
        Checks if a program is still running.

        Args:
            program_name (str): Name of the program to check

        Returns:
            bool: True if the program is still running, otherwise False
        """
        if program_name not in self.processes:
            return False
        
        proc = self.processes[program_name]["process"]
        return proc.poll() is None

    def get_running_programs(self) -> List[str]:
        """
        Returns a list of all running programs.

        Returns:
            List[str]: List of names of all running programs
        """
        running_programs = []
        for name in list(self.processes.keys()):
            if self.is_program_running(name):
                running_programs.append(name)
            else:
                # Remove no longer running programs from the list
                del self.processes[name]
                # Also remove from the non-minimized list if present
                if name in self.non_minimized_windows:
                    del self.non_minimized_windows[name]
                
        return running_programs
        
    # Dictionary to store active window monitoring threads and their control flags
    _window_monitor_threads: Dict[str, Dict[str, Any]] = {}
    _monitor_thread_lock = threading.Lock() # Lock for accessing the threads dict

    # Constants for Oculus monitoring thread
    OCULUS_MONITOR_INITIAL_DELAYS = [2, 4, 6] # Seconds
    OCULUS_MONITOR_POLL_INTERVAL = 2.0 # Seconds
    OCULUS_MONITOR_MAX_ATTEMPTS = 30 # Max attempts after initial delays

    def _start_oculus_monitor_thread(self, program_name: str, pid: int) -> None:
        """
        Starts a background thread to monitor and minimize Oculus Client windows.

        Handles the complex startup sequence of Oculus by periodically checking
        for its windows and attempting minimization.

        Args:
            program_name (str): Should be OCULUS_CLIENT_NAME.
            pid (int): Process ID of the Oculus Client.
        """
        import threading # Keep import local to this method if only used here

        with self._monitor_thread_lock:
            # Stop and join existing thread for this program if running
            if program_name in self._window_monitor_threads:
                existing_thread_data = self._window_monitor_threads[program_name]
                if existing_thread_data.get("running"):
                    logger.info(f"Stopping existing monitor thread for '{program_name}'...")
                    existing_thread_data["stop_event"].set() # Signal thread to stop
                    thread_to_join = existing_thread_data.get("thread")
                    if thread_to_join and thread_to_join.is_alive():
                         thread_to_join.join(timeout=self.OCULUS_MONITOR_POLL_INTERVAL + 1) # Wait slightly longer than poll interval
                         if thread_to_join.is_alive():
                              logger.warning(f"Existing monitor thread for '{program_name}' did not stop gracefully.")
                # Remove old entry regardless of whether it stopped gracefully
                del self._window_monitor_threads[program_name]


            # Create new control event and data for the thread
            stop_event = threading.Event()
            thread_data = {
                "thread": None,
                "stop_event": stop_event,
                "running": True # Indicates the thread *should* be running
            }
            self._window_monitor_threads[program_name] = thread_data # Store immediately

        def monitor_thread_func():
            """Target function for the Oculus monitoring thread."""
            logger.info(f"Starting Oculus monitor thread for PID {pid}...")
            minimized_successfully = False
            attempt_counter = 0

            try:
                # --- Initial checks with increasing delays ---
                for delay in self.OCULUS_MONITOR_INITIAL_DELAYS:
                    if stop_event.is_set(): break # Check for stop signal
                    logger.debug(f"Oculus monitor (PID {pid}): Waiting {delay}s...")
                    stop_event.wait(delay) # Wait for delay or stop signal
                    if stop_event.is_set(): break

                    logger.debug(f"Oculus monitor (PID {pid}): Attempting minimization after {delay}s delay.")
                    if self._minimize_oculus_windows(pid):
                        logger.info(f"Oculus windows (PID {pid}) minimized during initial delay phase ({delay}s).")
                        minimized_successfully = True
                        break # Exit loop if successful

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
                        break # Exit loop if successful

                    attempt_counter += 1
                    stop_event.wait(self.OCULUS_MONITOR_POLL_INTERVAL) # Wait for interval or stop signal

            except Exception as e:
                 logger.error(f"Error in Oculus monitor thread for PID {pid}: {e}", exc_info=True)
            finally:
                 # --- Cleanup ---
                 with self._monitor_thread_lock:
                      # Check if this thread's data is still the current one before modifying 'running'
                      current_data = self._window_monitor_threads.get(program_name)
                      if current_data and current_data["stop_event"] == stop_event:
                           current_data["running"] = False # Mark as no longer running
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
        
        The function searches all Windows windows for those that belong to the Oculus process
        and have a known window title.
        
        Args:
            pid (int): Process ID of the Oculus Client
            
        Returns:
            bool: True if Oculus main window was found and minimized, otherwise False
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            return False
            
        try:
            # Use the constant defined at the top of the file
            # TODO: Consider making these configurable (e.g., via config.json)

            all_process_windows = self._find_process_windows(pid)
            if not all_process_windows:
                return False # No windows found for this PID

            oculus_main_window = None
            other_windows = []
            minimized_any = False # Track if we successfully minimized at least one window

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
                    time.sleep(0.1) # Give it a moment

                    # Check if minimization was successful
                    placement = win32gui.GetWindowPlacement(hwnd)
                    if placement[1] != win32con.SW_SHOWMINIMIZED:
                        # Alternative method for difficult windows
                        logger.info("First minimization method failed for main window, trying alternative...")
                        win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_MINIMIZE, 0)
                        time.sleep(0.1) # Give it another moment
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
                        minimized_any = True # Count success even if main window failed
                    except Exception as e:
                         logger.error(f"Error minimizing Oculus side window '{window_title}': {e}")

            return minimized_any # Return True if any window (main or side) was successfully minimized

        except Exception as e:
            logger.error(f"Error during Oculus window search/minimization for PID {pid}: {e}")
            return False
    
    def minimize_all_windows_of_process(self, pid: int, program_name: str) -> bool:
        """
        Minimizes all visible windows of a specific process.
        
        In contrast to the _minimize_window method:
        1. This method handles each window type individually
        2. Outputs more specific log messages
        3. Recognizes Oculus main window specifically and treats it differently
        
        Particularly useful for:
        - Programs that open multiple parallel windows
        - Programs that open new windows later
        - Oculus Client which opens its main window with a delay
        
        Args:
            pid (int): Process ID of the program to monitor
            program_name (str): Name of the program for differentiated logging

        Returns:
            bool: True if at least one window was found and minimized, otherwise False
        """
        if not WINDOWS_IMPORTS_AVAILABLE:
            return False
            
        try:
            windows = self._find_process_windows(pid)
            
            if not windows:
                return False
                
            # Minimize all found windows
            for hwnd in windows:
                window_title = win32gui.GetWindowText(hwnd)
                
                # Check if it's an Oculus main window using the constant name and titles
                is_oculus_main = program_name == OCULUS_CLIENT_NAME and \
                                 any(oculus_title in window_title for oculus_title in OCULUS_WINDOW_TITLES)

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


    def reset(self) -> None:
        """
        Resets the ProcessManager, clearing all lists.
        """
        self.processes.clear()
        self.non_minimized_windows.clear()
        self._terminated_programs.clear()