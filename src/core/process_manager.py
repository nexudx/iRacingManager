#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Process Manager: Handles program start, minimization, and termination.
"""

import subprocess
import time
import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

# Imports
from src.core.utils.process_utils import WINDOWS_IMPORTS_AVAILABLE, check_windows_requirements
from src.core.utils.window_manager import WindowManager


# Logger
logger = logging.getLogger("ProcessManager")

# Minimization constants
DEFAULT_MAX_MINIMIZE_ATTEMPTS = 6  # Max attempts
DEFAULT_MINIMIZE_RETRY_DELAY = 1.0  # Retry delay (s)
DEFAULT_PROGRAM_START_TIMEOUT = 15 # Program start timeout (s)
class ProcessManager:
    """Manages program start, minimization, termination. Requires Windows libs."""

    def __init__(self):
        """Initializes ProcessManager."""
        self.processes: Dict[str, Dict[str, Any]] = {}
        self._terminated_programs: set[str] = set()
        self._window_manager = WindowManager()
        self._check_requirements()
        self.main_program_proc: Optional[subprocess.Popen] = None
        self.main_program_name: Optional[str] = None
        self.helper_app_futures = [] # For parallel helper app startup

    def _check_requirements(self) -> None:
        """Checks for required modules."""
        if not check_windows_requirements():
            sys.exit(1)

    def _handle_program_startup_and_minimization(self, program_config: Dict[str, Any]) -> Tuple[bool, Optional[subprocess.Popen], str]:
        """Starts one program, minimizes if helper. For threaded use. Returns (success, proc, name)."""
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
            
            creation_flags = subprocess.CREATE_NO_WINDOW # No window for helpers
            stdout_pipe = subprocess.DEVNULL
            stderr_pipe = subprocess.DEVNULL

            if is_main:
                logger.info(f"Launching main program '{name}' visibly. Output to DEVNULL.")
                creation_flags = 0 # Show window for main
            
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=stdout_pipe,
                stderr=stderr_pipe,
                creationflags=creation_flags
            )

            if is_main:
                time.sleep(2.0) # Main prog init delay
                if proc.poll() is not None:
                    logger.error(f"Main program '{name}' (PID: {proc.pid}) exited early: {proc.returncode}.")
                    return False, proc, name # Failure

            # Store process info
            self.processes[name] = {
                "process": proc, "pid": proc.pid, "config": program_config,
                "was_minimized": False # Initial state; updated for helpers later
            }
            logger.info(f"Program '{name}' (PID: {proc.pid}) started.")

            if not is_main:
                # Persistent minimization for helper apps
                time.sleep(program_config.get("initial_delay_before_minimize_s", 2.0)) # Initial delay
                
                starts_in_tray = program_config.get("starts_in_tray", False)
                minimized_successfully = self._minimize_program_persistently(
                    pid=proc.pid, program_name=name, starts_in_tray=starts_in_tray,
                    max_attempts=program_config.get("max_minimize_attempts", DEFAULT_MAX_MINIMIZE_ATTEMPTS),
                    retry_delay=program_config.get("minimize_retry_delay_s", DEFAULT_MINIMIZE_RETRY_DELAY),
                    timeout_seconds=program_config.get("minimize_timeout_s", DEFAULT_PROGRAM_START_TIMEOUT)
                )
                if name in self.processes: # Check existence
                    self.processes[name]["was_minimized"] = minimized_successfully
            else:
                self.main_program_proc = proc # Main program
                self.main_program_name = name
            
            return True, proc, name
        except Exception as e:
            logger.error(f"Error starting/handling '{name}': {e}")
            if name in self.processes: # Remove if failed
                del self.processes[name]
            return False, None, name

    def _minimize_program_persistently(self, pid: int, program_name: str, starts_in_tray: bool, max_attempts: int, retry_delay: float, timeout_seconds: float) -> bool:
        """Persistently tries to minimize program window(s), unless starts_in_tray is True."""
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
            if not self._is_pid_running(pid): # Check process existence
                logger.info(f"Process '{program_name}' (PID: {pid}) gone. Stopping minimize.")
                return False # Or True if "handled"

            logger.info(f"Attempt {attempt}/{max_attempts} to minimize '{program_name}' (PID: {pid}).")
            
            # WindowManager.minimize_window has its own retries.
            # Outer loop for more persistent attempts.
            if self._window_manager.minimize_window(pid, program_name, max_attempts=3, retry_delay=0.5): # Short inner attempts
                logger.info(f"Minimized '{program_name}' (PID: {pid}) on attempt {attempt}.")
                return True
            
            logger.debug(f"Minimize attempt {attempt} for '{program_name}' (PID: {pid}) failed. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
        logger.warning(f"Failed to minimize '{program_name}' (PID: {pid}) after {max_attempts} attempts.")
        return False

    def _is_pid_running(self, pid: int) -> bool:
        """Checks if PID is running. Uses psutil if available, else internal records."""
        if not WINDOWS_IMPORTS_AVAILABLE:
            # Fallback: check internal records
            for p_info in self.processes.values():
                if p_info["pid"] == pid: return p_info["process"].poll() is None
            return False # Not found
        else: # This else corresponds to 'if not WINDOWS_IMPORTS_AVAILABLE:'
            try:
                import psutil
                return psutil.pid_exists(pid)
            except ImportError:
                logger.warning("psutil not installed. Using fallback for PID check (Windows).")
                # Fallback: check Popen object
                for p_info in self.processes.values(): # Corrected variable, was p_name
                    if p_info["pid"] == pid: return p_info["process"].poll() is None
                return False # Not found
            except Exception as e:
                logger.error(f"Error checking PID {pid} existence: {e}")
                return False # Assume not running
    def start_all_programs(self, program_configs: List[Dict[str, Any]], parallel_workers: int = 4) -> None:
        """Starts main program, then helpers in parallel."""
        main_program_config = None
        helper_program_configs = []

        for config in program_configs:
            if config.get("is_main", False):
                if main_program_config:
                    logger.warning("Multiple main programs defined. Using first, others as helpers.")
                    helper_program_configs.append(config) # Subsequent "main" as helper
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
                return # Or handle gracefully
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
                
                # Wait for helper app startup/minimization, get results/exceptions.
                for future in as_completed(self.helper_app_futures):
                    try:
                        success, proc_obj, prog_name = future.result()
                        if success:
                            logger.info(f"Helper '{prog_name}' (PID: {proc_obj.pid if proc_obj else 'N/A'}) startup done.")
                        else:
                            logger.warning(f"Helper '{prog_name}' failed startup.")
                    except Exception as exc:
                        logger.error(f"Helper app startup exception: {exc}")
        else:
            logger.info("No helper programs to start.")
        
        logger.info("All program startup sequences initiated.")

    def wait_for_main_program_exit(self, timeout: Optional[float] = None) -> None:
        """Waits for main program exit."""
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
        """Terminates a program by name. Uses psutil (terminate then kill). Returns True on success."""
        logger.debug(f"terminate_program called for: '{program_name}'. Current _terminated_programs: {self._terminated_programs}")
        # Check if already terminated
        if program_name in self._terminated_programs:
            logger.debug(f"Program '{program_name}' already in _terminated_programs set.")
            return True

        if program_name not in self.processes:
            logger.warning(f"Cannot terminate '{program_name}': Not found in active self.processes: {list(self.processes.keys())}")
            return False

        logger.info(f"Adding '{program_name}' to _terminated_programs set.")
        self._terminated_programs.add(program_name) # Mark as terminating

        process_info = self.processes.get(program_name)
        if not process_info: # Defensive check
            logger.error(f"Internal error: Process info for '{program_name}' disappeared after initial check.")
            return False

        proc = process_info["process"]
        pid = process_info["pid"]
        logger.info(f"Attempting to terminate program: '{program_name}' (PID: {pid})")

        try:
            initial_poll = proc.poll()
            logger.debug(f"Process '{program_name}' (PID: {pid}) poll before termination: {initial_poll}")
            
            if initial_poll is None:  # If running
                logger.info(f"Process '{program_name}' (PID: {pid}) is running. Proceeding with termination.")
                if WINDOWS_IMPORTS_AVAILABLE:
                    try:
                        import psutil
                        logger.debug(f"psutil available. Attempting to get psutil.Process({pid}) for '{program_name}'.")
                        process = psutil.Process(pid)
                        logger.info(f"Sending SIGTERM to '{program_name}' (PID: {pid}) via psutil.")
                        process.terminate()  # SIGTERM
                        try:
                            # Wait a bit for graceful termination
                            process.wait(timeout=0.5) # Short wait
                            logger.info(f"Process '{program_name}' (PID: {pid}) terminated gracefully after SIGTERM.")
                        except psutil.TimeoutExpired:
                            logger.warning(f"Process '{program_name}' (PID: {pid}) did not terminate after SIGTERM and 0.5s. Sending SIGKILL.")
                            process.kill()  # SIGKILL
                            logger.info(f"SIGKILL sent to '{program_name}' (PID: {pid}).")
                        except psutil.NoSuchProcess: # Already gone after terminate
                             logger.info(f"Process '{program_name}' (PID: {pid}) already gone after SIGTERM (NoSuchProcess during wait).")
                             pass
                    except psutil.NoSuchProcess:
                        logger.info(f"Process '{program_name}' (PID: {pid}) already gone (NoSuchProcess before terminate/kill).")
                        pass # Already gone
                    except ImportError: # Should not happen if WINDOWS_IMPORTS_AVAILABLE is true and psutil is part of it
                        logger.error("psutil import error during termination despite WINDOWS_IMPORTS_AVAILABLE. This is unexpected.")
                        # Fallback to Popen.terminate()
                        logger.warning(f"Falling back to Popen.terminate() for '{program_name}' (PID: {pid}).")
                        proc.terminate()
                        time.sleep(0.1) # Brief pause
                        if proc.poll() is None:
                            logger.warning(f"Popen.terminate() failed for '{program_name}' (PID: {pid}). Falling back to Popen.kill().")
                            proc.kill()
                    except Exception as e_psutil:
                        logger.error(f"psutil error terminating '{program_name}' (PID: {pid}): {e_psutil}. Falling back.")
                        proc.terminate() # Fallback
                        time.sleep(0.1)
                        if proc.poll() is None: proc.kill()

                else: # No WINDOWS_IMPORTS_AVAILABLE (implies no psutil)
                    logger.warning(f"psutil unavailable for '{program_name}' (PID: {pid}). Using basic Popen terminate/kill.")
                    try:
                        proc.terminate()
                        time.sleep(0.1) # Brief pause
                        if proc.poll() is None: # Still running?
                            logger.warning(f"Popen.terminate() failed for '{program_name}' (PID: {pid}). Using Popen.kill().")
                            proc.kill()
                            logger.info(f"Popen.kill() used for '{program_name}' (PID: {pid}).")
                        else:
                            logger.info(f"Popen.terminate() successful for '{program_name}' (PID: {pid}).")
                    except OSError as e_os: # Ignore if already exited
                        logger.debug(f"Fallback Popen terminate/kill OSError for '{program_name}' (PID: {pid}): {e_os}")
                        pass
            else:
                logger.info(f"Process '{program_name}' (PID: {pid}) was already terminated (poll result: {initial_poll}).")

            final_poll = proc.poll()
            logger.debug(f"Process '{program_name}' (PID: {pid}) poll after termination attempts: {final_poll}")
            
            if program_name in self.processes:
                logger.debug(f"Removing '{program_name}' from self.processes dict.")
                del self.processes[program_name]
            logger.info(f"Termination attempt for '{program_name}' (PID: {pid}) completed. Returning True.")
            return True
        except Exception as e:
            logger.error(f"Unhandled exception terminating '{program_name}' (PID: {pid}): {e}")
            if program_name in self.processes: # Ensure removal on error
                logger.debug(f"Removing '{program_name}' from self.processes dict due to unhandled exception.")
                del self.processes[program_name]
            return False

    def terminate_all_programs(self) -> None:
        """Terminates all started programs cleanly. Idempotent."""
        logger.info(f"terminate_all_programs called. Current processes: {list(self.processes.keys())}")
        if not self.processes and not self._terminated_programs: # Check both, as _terminated_programs might have entries if called multiple times
            logger.info("No active programs or programs pending termination. Returning.")
            return
            
        logger.info("Proceeding to terminate all programs...")
            
        program_names_to_terminate = list(self.processes.keys()) # Copy keys for iteration, as terminate_program modifies self.processes
        logger.debug(f"Programs to iterate for termination: {program_names_to_terminate}")
            
        for name in program_names_to_terminate:
            logger.debug(f"Calling terminate_program for '{name}' from terminate_all_programs.")
            # terminate_program handles checks for _terminated_programs and self.processes internally
            self.terminate_program(name)
            
        # Post-loop checks and cleanup
        if self.processes: # Should be empty if all went well
            logger.warning(f"self.processes not empty after terminate_all_programs loop: {list(self.processes.keys())}. Clearing now.")
            self.processes.clear()

        if self._terminated_programs: # Should ideally be cleared if this is the final cleanup
            logger.debug(f"_terminated_programs not empty: {self._terminated_programs}. Clearing now.")
            self._terminated_programs.clear()
            
        # Attempt to let helper app threads finish
        # Threads not stopped forcefully; Popen handled.
        if self.helper_app_futures:
            logger.debug("Ensuring helper app threads (futures) complete post-termination.")
            active_futures_before_wait = sum(1 for f in self.helper_app_futures if not f.done())
            logger.debug(f"Number of active futures before waiting: {active_futures_before_wait}")

            for i, future in enumerate(self.helper_app_futures):
                if not future.done():
                    logger.debug(f"Waiting for future {i} (max 0.1s)...")
                    try:
                        future.result(timeout=0.1) # Short timeout
                        logger.debug(f"Future {i} completed or timed out.")
                    except Exception as e_future: # Catch all, including TimeoutError
                        logger.warning(f"Exception waiting for future {i}: {e_future}")
            
            active_futures_after_wait = sum(1 for f in self.helper_app_futures if not f.done())
            logger.debug(f"Number of active futures after waiting: {active_futures_after_wait}")
            self.helper_app_futures.clear()
            logger.debug("helper_app_futures cleared.")
    
            logger.info("All programs terminated; ProcessManager state cleared after terminate_all_programs.")
    def is_program_running(self, program_name: str) -> bool:
        """Checks if a program is running. Args: program_name (str). Returns bool."""
        if program_name not in self.processes:
            return False
        
        proc = self.processes[program_name]["process"]
        return proc.poll() is None

    def get_running_programs(self) -> List[str]:
        """Returns list of running program names."""
        running_programs = []
        for name in list(self.processes.keys()):
            if self.is_program_running(name):
                running_programs.append(name)
            else:
                del self.processes[name] # Remove non-running
                
        return running_programs

    def reset(self) -> None:
        """Resets ProcessManager. Calls terminate_all_programs first."""
        logger.info("Resetting ProcessManager state.")
        # Terminate running programs first
        self.terminate_all_programs()

        self.processes.clear()
        self._terminated_programs.clear()
        self.main_program_proc = None
        self.main_program_name = None
        
        if hasattr(self, 'helper_app_futures'): # Clear futures
            self.helper_app_futures.clear()