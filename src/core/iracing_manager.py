#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Manager - Core Orchestration.

Coordinates config, program startup (helpers, then iRacing),
iRacing process monitoring, and auto-shutdown.
Delegates actions to helper modules.
"""

import os
import sys
import time
import logging
import signal
import atexit
import threading
import argparse
from typing import Dict, List, Any, Optional

# Imports
from src.utils.config_manager import ConfigManager, ConfigError
from src.core.process_manager import ProcessManager
from src.core.iracing_watcher import iRacingWatcher
from src.ui.console_ui import setup_console_ui

# Logger
logger = logging.getLogger("iRacingManager")
logger.setLevel(logging.INFO)

# UI setup in main()


class iRacingManager:
    """
    Core iRacing Manager class.

    Handles init, config, main workflow (start/monitor),
    signal handling, clean termination, and iRacing exit response.
    Uses ConfigManager, ProcessManager, iRacingWatcher. Logs actions.
    """

    def __init__(self, config_path: str = "config/config.json"):
        """Init. Args: config_path (str, default 'config/config.json')."""
        logger.info("Initializing iRacing Manager...")
        self._cleanup_done = False # Cleanup flag
        self.config_manager = ConfigManager(config_path)
        self.process_manager = ProcessManager()
        self.iracing_watcher = None
        self.main_program_info: Optional[Dict[str, Any]] = None
        self._stop_event = threading.Event() # Termination signal

        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup) # Ensure cleanup on exit

    def _signal_handler(self, sig, frame) -> None:
        """OS signal handler (SIGINT, SIGTERM). Logs, sets stop event."""
        logger.info(f"Signal {sig} received by _signal_handler. Frame: {frame}")
        logger.info("Setting _stop_event in _signal_handler...")
        self._stop_event.set() # Signal main loop exit
        logger.info("_stop_event set in _signal_handler.")

    def _cleanup(self) -> None:
        """Central cleanup: stops watcher, terminates progs. Prevents multiple runs."""
        logger.info(f"_cleanup called. _cleanup_done is {self._cleanup_done}")
        # Prevent multiple cleanups
        if not self._cleanup_done:
            logger.info("Performing cleanup tasks in _cleanup...")

            self._cleanup_done = True # Mark done
            logger.debug("_cleanup_done set to True.")

            # Stop watcher
            if hasattr(self, 'iracing_watcher') and self.iracing_watcher:
                logger.info("Attempting to stop iracing_watcher in _cleanup...")
                try:
                    self.iracing_watcher.stop_watching()
                    logger.info("iracing_watcher.stop_watching() called successfully in _cleanup.")
                except Exception as e:
                    logger.error(f"Error stopping watcher in _cleanup: {e}")
            else:
                logger.info("iracing_watcher not present or not initialized in _cleanup.")

            # Terminate programs
            if hasattr(self, 'process_manager') and self.process_manager:
                logger.info("Attempting to terminate all programs via process_manager in _cleanup...")
                try:
                    self.process_manager.terminate_all_programs()
                    logger.info("process_manager.terminate_all_programs() called successfully in _cleanup.")
                except Exception as e:
                    logger.error(f"Error terminating programs in _cleanup: {e}")
            else:
                logger.info("process_manager not present or not initialized in _cleanup.")
            logger.info("Cleanup tasks finished in _cleanup.")
        else:
            logger.info("_cleanup already performed, skipping.")


    def start_programs(self) -> bool:
        """Starts configured programs (helpers then main). Returns True on success."""
        logger.info("Starting all configured programs...")
        logger.info("Starting all configured programs...")
        all_program_configs = self.config_manager.get_programs()
        
        # PM handles start order, parallelism, minimization.
        self.process_manager.start_all_programs(all_program_configs)

        # Check main program status
        if self.process_manager.main_program_proc and self.process_manager.main_program_name:
            main_program_config = self.config_manager.get_main_program()
            if not main_program_config:
                 logger.error("Main program config not found after start.")
                 return False

            self.main_program_info = {
                "config": main_program_config,
                "process": self.process_manager.main_program_proc,
                "pid": self.process_manager.main_program_proc.pid
            }
            logger.info(f"Main program '{self.process_manager.main_program_name}' started (PID: {self.process_manager.main_program_proc.pid}).")
            
            # Minimization handled by ProcessManager.
            # logger.info("Performing second minimization run for programs...") # Redundant
            # self.process_manager.retry_minimize_all() # Redundant

            return True
        else:
            logger.error("Main program failed to start or info unavailable.")
            main_program_config_for_error = self.config_manager.get_main_program()
            if main_program_config_for_error:
                logger.error(f"Failed to start: {main_program_config_for_error.get('name', 'Unknown Main Program')}")
            else:
                logger.error("Failed to identify/start main program from config.")
            return False
    def watch_iracing(self) -> None:
        """Starts monitoring the main program process in a new thread."""
        if not self.main_program_info:
            logger.error("No main program found to monitor.")
            return
            
        logger.info("Starting main program monitoring...")
        
        self.iracing_watcher = iRacingWatcher(on_exit_callback=self._on_iracing_exit)
        
        if not self.iracing_watcher.find_iracing_process(self.main_program_info):
            logger.error("Could not find main program to monitor.")
            return
            
        self.iracing_watcher.start_watching()
        
        logger.info(f"Main program monitoring active. Ctrl+C to exit.")

    def _on_iracing_exit(self) -> None:
        """Callback for main program termination. Stops watcher, progs, signals main loop."""
        logger.info("_on_iracing_exit callback triggered.")
        
        if self.iracing_watcher:
            logger.info("Attempting to stop iracing_watcher in _on_iracing_exit...")
            try:
                self.iracing_watcher.stop_watching() # Stop monitoring
                logger.info("iracing_watcher.stop_watching() called successfully in _on_iracing_exit.")
            except Exception as e:
                logger.error(f"Error stopping watcher in _on_iracing_exit: {e}")
        else:
            logger.info("iracing_watcher not present in _on_iracing_exit (already stopped or not initialized).")
            
        logger.info("Attempting to terminate all programs via process_manager in _on_iracing_exit...")
        try:
            self.process_manager.terminate_all_programs() # Terminate helpers
            logger.info("process_manager.terminate_all_programs() called successfully in _on_iracing_exit.")
        except Exception as e:
            logger.error(f"Error terminating programs in _on_iracing_exit: {e}")
        
        logger.info("Setting _stop_event in _on_iracing_exit...")
        self._stop_event.set() # Signal main loop exit
        logger.info("_stop_event set in _on_iracing_exit. All programs should be terminated.")

    def run(self) -> None:
        """Executes main manager workflow: start progs, monitor, wait for exit."""
        if not self.start_programs(): # Start programs
            logger.error("Error starting programs. Exiting...")
            self._cleanup()
            sys.exit(1)
        
        self.watch_iracing() # Monitor main program
        
        # Wait for stop (main exit or Ctrl+C)
        if self.iracing_watcher and self.iracing_watcher.is_watching():
            logger.info("Manager running. Waiting for main program exit or Ctrl+C...")
            self._stop_event.wait() # Wait for signal
            logger.info("Stop event received.")
        elif not self.main_program_info:
             logger.warning("Main program info unavailable; cannot wait for termination.")
        else:
             logger.warning("Watcher not active; cannot wait for termination.")

        # atexit handles cleanup.
        logger.info("iRacing Manager shutting down.")


def main() -> None:
    """App entry point. Parses args, sets up UI, runs manager, handles errors."""
    parser = argparse.ArgumentParser(description="iRacing Manager - Start and manage iRacing and helper applications.")
    parser.add_argument(
        "-c", "--config",
        default="config/config.json",
        help="Path to the configuration file (default: config/config.json)"
    )
    args = parser.parse_args()

    try:
        setup_console_ui(logger) # Setup UI
        
        manager = iRacingManager(config_path=args.config) # Create manager

        manager.run() # Run workflow

    except (FileNotFoundError, ConfigError) as e:
        logger.error(f"Initialization error: {e}") # Config/file errors
        sys.exit(1)
    except KeyboardInterrupt:
         logger.info("User shutdown during startup.") # Ctrl+C at startup
         if 'manager' in locals() and hasattr(manager, '_cleanup'): # Ensure cleanup
             manager._cleanup()
         sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected critical error: {e}") # Other errors
        if 'manager' in locals() and hasattr(manager, '_cleanup'): # Attempt cleanup
             manager._cleanup()
        sys.exit(1)
if __name__ == "__main__":
    main()