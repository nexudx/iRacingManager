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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

# Import our refactored modules with updated paths
from src.utils.process_utils import WINDOWS_IMPORTS_AVAILABLE, check_windows_requirements
from src.utils.window_manager import WindowManager


# Set up logger - Configuration should be done in the main entry point
logger = logging.getLogger("ProcessManager")

# Constants for persistent minimization
DEFAULT_MAX_MINIMIZE_ATTEMPTS = 6  # e.g., 6 attempts
DEFAULT_MINIMIZE_RETRY_DELAY = 1.0  # e.g., 1 second delay
DEFAULT_PROGRAM_START_TIMEOUT = 15 # e.g. 15 seconds for a program to start and its window to appear
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
        self._terminated_programs: set[str] = set()
        self._window_manager = WindowManager()
        self._check_requirements()
        self.main_program_proc: Optional[subprocess.Popen] = None
        self.main_program_name: Optional[str] = None
        # For managing parallel startup of helper apps
        self.helper_app_futures = []

    def _check_requirements(self) -> None:
        """
        Checks if all required modules are available.
        """
        if not check_windows_requirements():
            sys.exit(1)

    def _handle_program_startup_and_minimization(self, program_config: Dict[str, Any]) -> Tuple[bool, Optional[subprocess.Popen], str]:
        """
        Handles the startup of a single program and its minimization if it's a helper app.
        This method is intended to be run in a separate thread for helper applications.

        Returns:
            Tuple[bool, Optional[subprocess.Popen], str]: (success_status, process_object_or_None, program_name)
        """
        name = program_config["name"]
        path = program_config["path"]
        arguments = program_config.get("arguments", "").strip()
        is_main = program_config.get("is_main", False)

        if not os.path.exists(path):
            logger.error(f"Could not start '{name}'. Path does not exist: {path}")
            return False, None, name

        try:
            cmd = [path]
            if arguments:
                cmd += arguments.split()
            
            logger.info(f"Starting program: {name} (is_main: {is_main})")
            
            creation_flags = subprocess.CREATE_NO_WINDOW
            stdout_pipe = subprocess.DEVNULL
            stderr_pipe = subprocess.DEVNULL

            if is_main:
                logger.info(f"Launching main program '{name}' with visible window. Output will be redirected to DEVNULL.")
                creation_flags = 0 # Default flags, should show window
            
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=stdout_pipe,
                stderr=stderr_pipe,
                creationflags=creation_flags
            )

            if is_main:
                # Add a small delay to allow the main program to initialize or fail fast,
                # then check if it's still running.
                time.sleep(2.0)
                if proc.poll() is not None:
                    logger.error(f"Main program '{name}' (PID: {proc.pid}) terminated shortly after launch with exit code {proc.returncode}.")
                    return False, proc, name # Indicate failure

            # Store process information immediately
            # 'was_minimized' will be updated by the minimization logic for helper apps
            self.processes[name] = {
                "process": proc,
                "pid": proc.pid,
                "config": program_config,
                "was_minimized": True if is_main else False # Main apps are not minimized by this system
            }
            logger.info(f"Program '{name}' (PID: {proc.pid}) started successfully.")

            if not is_main:
                # For helper apps, attempt persistent minimization
                # Allow some time for the process to initialize and potentially create its window
                time.sleep(program_config.get("initial_delay_before_minimize_s", 2.0)) # Configurable initial delay
                
                starts_in_tray = program_config.get("starts_in_tray", False) # Get the flag
                minimized_successfully = self._minimize_program_persistently(
                    pid=proc.pid,
                    program_name=name,
                    starts_in_tray=starts_in_tray, # Pass the flag
                    max_attempts=program_config.get("max_minimize_attempts", DEFAULT_MAX_MINIMIZE_ATTEMPTS),
                    retry_delay=program_config.get("minimize_retry_delay_s", DEFAULT_MINIMIZE_RETRY_DELAY),
                    timeout_seconds=program_config.get("minimize_timeout_s", DEFAULT_PROGRAM_START_TIMEOUT)
                )
                if name in self.processes: # Check if process still exists (could have been terminated)
                    self.processes[name]["was_minimized"] = minimized_successfully
            else:
                # This is the main program
                self.main_program_proc = proc
                self.main_program_name = name
            
            return True, proc, name
        except Exception as e:
            logger.error(f"Error starting or handling '{name}': {e}")
            # Ensure it's removed from processes if it failed to start properly
            if name in self.processes:
                del self.processes[name]
            return False, None, name

    def _minimize_program_persistently(self, pid: int, program_name: str, starts_in_tray: bool, max_attempts: int, retry_delay: float, timeout_seconds: float) -> bool:
        """
        Persistently attempts to minimize a program's window(s), unless configured to start in tray.

        This method will:
        1. Check if the program is configured to start in the system tray. If so, skip minimization.
        2. Loop for a specified number of attempts or until a timeout is reached.
        3. In each iteration, try to find and minimize the program's windows.
        4. Use `self._window_manager.minimize_window` which has its own retry logic for finding/minimizing.
        5. Log attempts, successes, and failures.
        """
        if starts_in_tray:
            logger.info(f"'{program_name}' (PID: {pid}) is configured to start in tray, skipping active window minimization.")
            return True

        logger.info(f"Initiating persistent minimization for '{program_name}' (PID: {pid}). Max attempts: {max_attempts}, Retry delay: {retry_delay}s, Timeout: {timeout_seconds}s.")
        
        start_time = time.time()
        for attempt in range(1, max_attempts + 1):
            if time.time() - start_time > timeout_seconds:
                logger.warning(f"Minimization for '{program_name}' (PID: {pid}) timed out after {timeout_seconds}s.")
                return False

            # Check if the process still exists
            if not self._is_pid_running(pid):
                logger.info(f"Process '{program_name}' (PID: {pid}) is no longer running. Stopping minimization attempts.")
                return False # Or True if we consider a non-running process as "handled"

            logger.info(f"Attempt {attempt}/{max_attempts} to minimize '{program_name}' (PID: {pid}).")
            
            # We use minimize_window from WindowManager as it already contains logic
            # to find and attempt to minimize windows with its own internal retries.
            # The 'max_attempts' here refers to how many times we call this robust function.
            # We can configure the inner attempts of minimize_window to be small (e.g. 1-2)
            # if we want this outer loop to be the main retry controller.
            # For now, let's assume minimize_window is configured reasonably.
            if self._window_manager.minimize_window(pid, program_name, max_attempts=3, retry_delay=0.5): # Using short inner attempts
                logger.info(f"Successfully minimized '{program_name}' (PID: {pid}) on attempt {attempt}.")
                return True
            
            logger.debug(f"Minimization attempt {attempt} for '{program_name}' (PID: {pid}) did not confirm success. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)

        logger.warning(f"Failed to minimize '{program_name}' (PID: {pid}) after {max_attempts} attempts.")
        return False

    def _is_pid_running(self, pid: int) -> bool:
        """Checks if a process with the given PID is running."""
        if not WINDOWS_IMPORTS_AVAILABLE:
            # Fallback if psutil is not available (e.g., non-Windows or missing dependency)
            # Check our internal records.
            for p_info in self.processes.values():
                if p_info["pid"] == pid:
                    return p_info["process"].poll() is None
            return False # PID not found in our managed processes
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            logger.warning("psutil is not installed. Cannot accurately check if PID is running.")
            # Fallback: Check if we have a Popen object and if it hasn't terminated
            for p_name, p_info in self.processes.items():
                if p_info["pid"] == pid:
                    return p_info["process"].poll() is None
            return False # PID not found in our managed processes
        except Exception as e:
            logger.error(f"Error checking PID {pid} existence: {e}")
            return False # Assume not running on error

    def start_all_programs(self, program_configs: List[Dict[str, Any]], parallel_workers: int = 4) -> None:
        """
        Starts all configured programs. Main program is started first, then helper
        programs are started in parallel.
        """
        main_program_config = None
        helper_program_configs = []

        for config in program_configs:
            if config.get("is_main", False):
                if main_program_config:
                    logger.warning("Multiple main programs defined. Using the first one.")
                    helper_program_configs.append(config) # Treat subsequent "main" as helper
                else:
                    main_program_config = config
            else:
                helper_program_configs.append(config)

        # Start the main program first and wait for it
        if main_program_config:
            logger.info(f"Starting main program: {main_program_config['name']}")
            success, proc, name = self._handle_program_startup_and_minimization(main_program_config)
            if not success:
                logger.error(f"Main program '{name}' failed to start. Aborting helper app startup.")
                return # Or handle more gracefully depending on requirements
            self.main_program_proc = proc
            self.main_program_name = name
        else:
            logger.info("No main program defined. Starting only helper applications.")

        # Start helper programs in parallel
        if helper_program_configs:
            logger.info(f"Starting {len(helper_program_configs)} helper program(s) in parallel with {parallel_workers} workers...")
            # Clear previous futures if any
            self.helper_app_futures.clear()

            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                for config in helper_program_configs:
                    future = executor.submit(self._handle_program_startup_and_minimization, config)
                    self.helper_app_futures.append(future)
                
                # Optionally, wait for all helper apps to complete their startup and initial minimization attempt
                # This loop also helps in retrieving results or exceptions from threads
                for future in as_completed(self.helper_app_futures):
                    try:
                        success, proc_obj, prog_name = future.result()
                        if success:
                            logger.info(f"Helper program '{prog_name}' (PID: {proc_obj.pid if proc_obj else 'N/A'}) finished startup sequence.")
                        else:
                            logger.warning(f"Helper program '{prog_name}' failed or had issues during startup sequence.")
                    except Exception as exc:
                        logger.error(f"A helper program generated an exception during startup: {exc}")
        else:
            logger.info("No helper programs to start.")
        
        logger.info("All program startup sequences initiated.")

    def wait_for_main_program_exit(self, timeout: Optional[float] = None) -> None:
        """
        Waits for the main program to exit.
        """
        if self.main_program_proc:
            logger.info(f"Waiting for main program '{self.main_program_name}' (PID: {self.main_program_proc.pid}) to exit...")
            try:
                self.main_program_proc.wait(timeout=timeout)
                logger.info(f"Main program '{self.main_program_name}' has exited.")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout waiting for main program '{self.main_program_name}' to exit.")
            except Exception as e:
                logger.error(f"Error waiting for main program '{self.main_program_name}': {e}")
        else:
            logger.info("No main program was started or it already exited.")


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

            # Termination attempt finished (or process was already gone).
            # This part is the end of the 'try' block's normal execution path.
            if program_name in self.processes:
                del self.processes[program_name]
            return True
        # This 'except' is now correctly aligned with the 'try' starting at line 335.
        except Exception as e:
            logger.error(f"Error during the termination process for '{program_name}': {e}")
            # Even in case of error, ensure it's removed from the list.
            if program_name in self.processes:
                del self.processes[program_name]
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
        self.processes.clear()
        self._terminated_programs.clear()
        
        # Wait for any helper app threads to finish if they are still running (e.g. if terminate_all is called early)
        # This is a bit tricky as threads might be in Popen.wait() or time.sleep()
        # For simplicity, we're not forcefully stopping threads here, assuming terminate_program handles Popen objects.
        # A more robust solution might involve signaling threads to exit.
        if self.helper_app_futures:
            logger.debug("Attempting to ensure helper app threads complete after termination signal.")
            # Wait for a short period for futures to complete if they haven't already
            for future in self.helper_app_futures:
                if not future.done():
                    try:
                        future.result(timeout=0.1) # Short timeout
                    except: # Catch any exception, including TimeoutError
                        pass
            self.helper_app_futures.clear()


        logger.info("All programs have been terminated and ProcessManager state cleared.")

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
                
        return running_programs

    def reset(self) -> None:
        """
        Resets the ProcessManager, clearing all lists and stopping threads if any.
        Note: This is a simple reset. For full cleanup during application exit,
        `terminate_all_programs` should be used.
        """
        logger.info("Resetting ProcessManager state.")
        # Terminate any running programs first before clearing lists
        self.terminate_all_programs()

        self.processes.clear()
        self._terminated_programs.clear()
        self.main_program_proc = None
        self.main_program_name = None
        
        # Ensure futures list is cleared
        if hasattr(self, 'helper_app_futures'):
            self.helper_app_futures.clear()