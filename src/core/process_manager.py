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

import subprocess
import time
import logging
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

# Import our refactored modules with updated paths
from src.utils.process_utils import WINDOWS_IMPORTS_AVAILABLE, check_windows_requirements
from src.utils.window_manager import WindowManager
from src.vr.oculus_handler import OculusHandler, OCULUS_CLIENT_NAME

# Set up logger - Configuration should be done in the main entry point
logger = logging.getLogger("ProcessManager")

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
        self._terminated_programs: set[str] = set()
        self._window_manager = WindowManager()
        self._oculus_handler = OculusHandler()
        self._check_requirements()

    def _check_requirements(self) -> None:
        """
        Checks if all required modules are available.
        """
        if not check_windows_requirements():
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
            if name == OCULUS_CLIENT_NAME:
                logger.info(f"Special handling for {OCULUS_CLIENT_NAME} (PID: {proc.pid}). Starting monitor thread.")
                # Give Oculus a moment to potentially create its initial process structures
                time.sleep(1.0)
                self._oculus_handler.start_oculus_monitor_thread(name, proc.pid)
            else:
                # Standard wait for other programs to potentially create windows
                time.sleep(0.5)

            # Minimize the window if it's not the main program
            was_minimized = True
            if not is_main:
                # Check if the program is marked as systray_only
                if program_config.get("systray_only", False):
                    logger.info(f"Program '{name}' starts directly in the system tray, skipping minimization.")
                else:
                    was_minimized = self._window_manager.minimize_window(proc.pid, name)
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
                if WINDOWS_IMPORTS_AVAILABLE:
                    import psutil
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

            # Call the window manager's minimize function
            if self._window_manager.minimize_window(pid, name, max_attempts=8, retry_delay=1.5):
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
                        import psutil
                        process = psutil.Process(pid)
                        process.terminate()  # Send SIGTERM
                        
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
        
        # Stop any running Oculus monitor threads
        self._oculus_handler.stop_all_monitors()
        
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

    def reset(self) -> None:
        """
        Resets the ProcessManager, clearing all lists.
        """
        self.processes.clear()
        self.non_minimized_windows.clear()
        self._terminated_programs.clear()
        self._oculus_handler.stop_all_monitors()