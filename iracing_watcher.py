#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Watcher for the iRacing Manager.

This module specializes in continuously monitoring the iRacing process.
It offers the following main functions:

1. Finding the iRacing process based on the process ID
2. Continuous monitoring of the process status in a separate thread
3. Automatic notification via a callback when iRacing is terminated
4. Clean thread management and resource release

The monitoring is resource-efficient through regular status queries
with short pauses between checks.
"""

import logging
import threading
import time
import os
import sys
from typing import Dict, Optional, Callable, Any

# Windows-specific imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil module not available. Process monitoring limited.")

# Set up logger - Configuration should be done in the main entry point
logger = logging.getLogger("iRacingWatcher")


class iRacingWatcher:
    """
    Main class for monitoring the iRacing process.
    
    This class implements a reliable monitoring mechanism
    that detects when the iRacing process is terminated and then automatically
    calls a callback function. This allows the iRacing Manager to
    terminate all other programs once iRacing is closed.
    
    The monitoring occurs in a separate thread so as not to block the main program
    and uses psutil for process monitoring.
    """

    def __init__(self, on_exit_callback: Optional[Callable[[], None]] = None):
        """
        Initializes the iRacing Watcher.

        Args:
            on_exit_callback (Optional[Callable[[], None]]): Callback function that is called
                                                      when the iRacing process is terminated.
        """
        self.iracing_pid: Optional[int] = None
        self.iracing_process: Optional[psutil.Process] = None # Use psutil.Process type hint
        self.on_exit_callback = on_exit_callback
        self._stop_event = threading.Event() # Event to signal thread termination
        self.watch_thread: Optional[threading.Thread] = None
        self._check_requirements()

    def _check_requirements(self) -> None:
        """
        Checks if all required modules and system requirements are available.
        
        This method checks:
        1. Whether the psutil module is installed, which is needed for process monitoring
        2. Whether the program is running on a Windows system
        
        If any of the requirements are not met, the program exits with a
        meaningful error message, as reliable process monitoring is not possible
        without these requirements.
        """
        if not PSUTIL_AVAILABLE:
            logger.error("psutil module is required for process monitoring.")
            logger.error("Please install it with: pip install psutil")
            sys.exit(1)
        
        # Check if we are running on Windows
        if sys.platform != "win32":
            logger.error("This program is designed only for Windows systems.")
            sys.exit(1)

    def find_iracing_process(self, process_info: Dict[str, Any]) -> bool:
        """
        Finds the iRacing process based on the information provided by the ProcessManager.
        
        This method:
        1. Extracts the PID from the process information
        2. Attempts to find the process using psutil
        3. Stores the process object and PID for later monitoring
        4. Logs detailed information about the found process
        
        In case of errors (non-existent PID, process no longer exists), an
        appropriate error message is logged and False is returned.

        Args:
            process_info (Dict[str, Any]): Information about the started process,
                                         contains at least a "pid" key

        Returns:
            bool: True if the process was found and can be monitored,
                False in case of errors or if the process was not found
        """
        if not process_info:
            logger.error("No process information provided for iRacing.")
            return False

        pid = process_info.get("pid")
        if not pid:
            logger.error("No PID found in the process information.")
            return False

        try:
            # Try to find the process via the PID
            # Check if PID exists first for a slightly cleaner check
            if not psutil.pid_exists(pid):
                 logger.error(f"Process with PID {pid} does not exist.")
                 return False

            process = psutil.Process(pid) # Now get the process object
            self.iracing_pid = pid
            self.iracing_process = process

            proc_name = process.name()
            logger.info(f"Main process found: {proc_name} (PID: {pid})")
            return True
            
        except psutil.NoSuchProcess:
            logger.error(f"Process with PID {pid} does not exist.")
            return False
        except Exception as e:
            logger.error(f"Error finding the iRacing process: {e}")
            return False

    def is_process_running(self) -> bool:
        """
        Precisely checks if the iRacing process is still active.
        
        This method uses multiple checks to determine the status:
        1. Basic check if a process object exists
        2. psutil.is_running() to check if the process still exists
        3. Checking the process status for "zombie" status
           (terminated but not yet fully released)
        
        The method catches NoSuchProcess exceptions that can occur
        if the process is terminated between the different checks.

        Returns:
            bool: True if the process is still actively running,
                False if the process no longer exists or is a zombie
        """
        if not self.iracing_process:
            return False
            
        try:
            # Check if the process is still running
            if not self.iracing_process.is_running():
                return False
                
            # Check the status of the process
            status = self.iracing_process.status()
            # "zombie" means the process has been terminated but not yet fully released
            return status != "zombie"
            
        except psutil.NoSuchProcess:
            # Process no longer exists
            return False
        except Exception as e:
            logger.error(f"Error checking the iRacing process status: {e}")
            return False

    def start_watching(self) -> None:
        """
        Starts the continuous monitoring of the iRacing process in the background.
        
        This method:
        1. Checks if a valid process object exists
        2. Avoids duplicate monitoring by checking the running flag
        3. Starts a daemon thread for continuous monitoring
           (Daemon threads are automatically terminated when the main program ends)
        4. Logs the start of the monitoring
        
        The thread executes the _watch_process method, which regularly
        checks the process status and calls the callback when terminated.
        """
        if not self.iracing_process:
            logger.error("No iRacing process found to monitor.")
            return

        # Use the stop event to check if running
        if self.watch_thread and self.watch_thread.is_alive():
            logger.warning("Monitoring thread is already running.")
            return

        self._stop_event.clear() # Ensure event is clear before starting
        self.watch_thread = threading.Thread(target=self._watch_process, daemon=True)
        # Daemon threads are automatically terminated when the main program ends,
        # but we also implement graceful shutdown via the event.
        self.watch_thread.start()

        logger.info(f"Monitoring of main process (PID: {self.iracing_pid}) started.")

    def stop_watching(self) -> None:
        """
        Stops the monitoring of the iRacing process cleanly and in a controlled manner.
        
        This method ensures that all resources are properly released:
        1. Sets the running flag to False to end the thread loop
        2. Logs the termination of the monitoring
        3. Waits for the monitoring thread to end (with timeout)
        4. Avoids deadlocks by checking if we are ourselves the monitoring thread
        
        The method is idempotent and can safely be called multiple times
        without causing errors, even if no monitoring is active.
        """
        if not self.watch_thread or not self.watch_thread.is_alive():
            logger.debug("Stop watching called, but monitoring thread is not running.")
            return

        logger.info("Stopping the monitoring of the main process...")
        self._stop_event.set() # Signal the thread to stop

        # Wait for the end of the monitoring thread, but only if called from a different thread.
        # Avoids deadlock if stop_watching is called from the callback within the watch thread itself.
        current_thread = threading.current_thread()
        if self.watch_thread and self.watch_thread.is_alive() and current_thread != self.watch_thread:
            try:
                self.watch_thread.join(timeout=2.0) # Wait max 2 seconds
            except Exception as e:
                logger.warning(f"Could not wait for the end of the monitoring thread: {e}")

    def _watch_process(self) -> None:
        """
        Core of the monitoring logic - runs in a separate thread and continuously checks the process status.
        
        This method implements:
        1. A loop that runs as long as the running flag is set
        2. Regular checking of the iRacing process status
        3. Calling the callback function when iRacing is terminated
        4. Error handling for the callback
        5. Resource-conserving pauses between checks
        
        The monitoring is automatically terminated when:
        - iRacing is no longer running (successful detection)
        - stop_watching() has been called (external deactivation)
        - A severe error occurs
        
        The thread logs its start and end for better diagnosis.
        """
        logger.info(f"Monitoring thread started for PID {self.iracing_pid}.")
        process_terminated = False

        while not self._stop_event.is_set():
            try:
                if not self.is_process_running():
                    logger.info(f"Main process (PID: {self.iracing_pid}) has terminated.")
                    process_terminated = True
                    break # Exit loop cleanly
            except Exception as e:
                 # Log unexpected errors during the check itself
                 logger.error(f"Error during process status check for PID {self.iracing_pid}: {e}", exc_info=True)
                 # Decide whether to break or continue based on the error? For now, break on error.
                 break

            # Wait for the specified interval or until the stop event is set
            # Use wait() for responsiveness to the stop signal
            stopped = self._stop_event.wait(timeout=1.0) # Check every 1 second
            if stopped:
                 logger.debug("Stop event received, exiting monitoring loop.")
                 break

        # --- Loop finished ---

        # Call the callback *after* the loop, only if the process terminated naturally
        if process_terminated and self.on_exit_callback:
            logger.info("Executing exit callback...")
            try:
                self.on_exit_callback()
            except Exception as e:
                logger.error(f"Error executing exit callback: {e}", exc_info=True)

        # Ensure the stop event is set if the loop exited due to process termination or error
        self._stop_event.set()

        logger.info(f"Monitoring thread for PID {self.iracing_pid} finished.")

    def is_watching(self) -> bool:
        """Returns True if the monitoring thread is currently active."""
        # Check the event flag and thread status
        return not self._stop_event.is_set() and self.watch_thread is not None and self.watch_thread.is_alive()


# Comment out this test block to import it as a module more cleanly
# if __name__ == "__main__":
#     # Test code for directly executing this file
#     def on_exit():
#         print("iRacing has been terminated!")
#
#     # Fallback for tests: Use Notepad as "iRacing"
#     import subprocess
#     proc = subprocess.Popen(["notepad.exe"])
#
#     watcher = iRacingWatcher(on_exit_callback=on_exit)
#     process_info = {"pid": proc.pid}
#
#     if watcher.find_iracing_process(process_info):
#         watcher.start_watching()
#
#         print("Notepad simulates iRacing for the test.")
#         print("Close Notepad to trigger the callback.")
#
#         # Wait until the monitoring thread is terminated
#         while watcher.running:
#             time.sleep(1.0)