#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Watcher: Monitors iRacing process.

Finds iRacing PID, monitors in thread, calls callback on exit.
Efficient, clean thread management.
"""

import logging
import threading
import time
import os
import sys
from typing import Dict, Optional, Callable, Any

# OS-specific imports
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil module not available. Process monitoring limited.")

# Logger
logger = logging.getLogger("iRacingWatcher")


class iRacingWatcher:
    """Monitors iRacing process. Calls callback on termination. Uses psutil in a thread."""

    def __init__(self, on_exit_callback: Optional[Callable[[], None]] = None):
        """Init. Args: on_exit_callback (Optional[Callable]): Called on iRacing exit."""
        self.iracing_pid: Optional[int] = None
        self.iracing_process: Optional[psutil.Process] = None # psutil.Process
        self.on_exit_callback = on_exit_callback
        self._stop_event = threading.Event() # Thread termination signal
        self.watch_thread: Optional[threading.Thread] = None
        self._check_requirements()

    def _check_requirements(self) -> None:
        """Checks for psutil and Windows OS. Exits if not met."""
        if not PSUTIL_AVAILABLE:
            logger.error("psutil module is required for process monitoring.")
            logger.error("Please install it with: pip install psutil")
            sys.exit(1)
        
        if sys.platform != "win32": # Windows only
            logger.error("This program is Windows-only.")
            sys.exit(1)

    def find_iracing_process(self, process_info: Dict[str, Any]) -> bool:
        """Finds iRacing process by PID from process_info. Returns True if found."""
        if not process_info:
            logger.error("No process information provided for iRacing.")
            return False

        pid = process_info.get("pid")
        if not pid:
            logger.error("No PID found in the process information.")
            return False
        
        # Corrected indentation for the try block
        try:
            if not psutil.pid_exists(pid): # Check PID existence
                 logger.error(f"PID {pid} does not exist.")
                 return False

            process = psutil.Process(pid) # Get process object
            self.iracing_pid = pid
            self.iracing_process = process

            proc_name = process.name()
            logger.info(f"Main process found: {proc_name} (PID: {pid})")
            return True
            
        except psutil.NoSuchProcess:
            logger.error(f"PID {pid} not found (NoSuchProcess).")
            return False
        except Exception as e:
            logger.error(f"Error finding iRacing process: {e}")
            return False
    def is_process_running(self) -> bool:
        """Checks if iRacing process is active (not zombie). Returns True if running."""
        if not self.iracing_process:
            return False
            
        try:
            if not self.iracing_process.is_running(): # Check running
                return False
                
            status = self.iracing_process.status() # Check status
            return status != "zombie" # Not a zombie
            
        except psutil.NoSuchProcess:
            return False # Process gone
        except Exception as e:
            logger.error(f"Error checking iRacing process status: {e}")
            return False

    def start_watching(self) -> None:
        """Starts iRacing process monitoring in a daemon thread."""
        if not self.iracing_process:
            logger.error("No iRacing process found to monitor.")
            return

        if self.watch_thread and self.watch_thread.is_alive(): # Prevent duplicates
            logger.warning("Monitoring thread already running.")
            return

        self._stop_event.clear() # Clear event
        self.watch_thread = threading.Thread(target=self._watch_process, daemon=True)
        # Daemon thread auto-terminates, but graceful shutdown via event.
        self.watch_thread.start()

        logger.info(f"Main process monitoring started (PID: {self.iracing_pid}).")

    def stop_watching(self) -> None:
        """Stops iRacing process monitoring cleanly. Idempotent."""
        if not self.watch_thread or not self.watch_thread.is_alive():
            logger.debug("Stop watching called, but monitoring thread is not running.")
            return

        logger.info("Stopping main process monitoring...")
        self._stop_event.set() # Signal thread stop

        # Wait for thread end (if not called from watch thread itself)
        current_thread = threading.current_thread()
        if self.watch_thread and self.watch_thread.is_alive() and current_thread != self.watch_thread:
            try:
                self.watch_thread.join(timeout=2.0) # 2s timeout
            except Exception as e:
                logger.warning(f"Could not join monitoring thread: {e}")

    def _watch_process(self) -> None:
        """Thread: continuously checks process status. Calls callback on exit."""
        logger.info(f"Monitoring thread started for PID {self.iracing_pid}.")
        process_terminated = False

        while not self._stop_event.is_set():
            try:
                if not self.is_process_running():
                    logger.info(f"Main process (PID: {self.iracing_pid}) has terminated.")
                    process_terminated = True
                    break # Exit loop cleanly
            except Exception as e:
                 logger.error(f"Error checking PID {self.iracing_pid}: {e}", exc_info=True) # Log error
                 break # Break on error

            # Wait or respond to stop signal
            stopped = self._stop_event.wait(timeout=1.0) # 1s check interval
            if stopped:
                 logger.debug("Stop event received; exiting loop.")
                 break

        # Callback after loop (if natural termination)
        if process_terminated and self.on_exit_callback:
            logger.info("Executing exit callback...")
            try:
                self.on_exit_callback()
            except Exception as e:
                logger.error(f"Error in exit callback: {e}", exc_info=True)

        self._stop_event.set() # Ensure stop event is set

        logger.info(f"Monitoring thread for PID {self.iracing_pid} finished.")

    def is_watching(self) -> bool:
        """True if monitoring thread is active."""
        return not self._stop_event.is_set() and self.watch_thread is not None and self.watch_thread.is_alive()