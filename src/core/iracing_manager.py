#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Manager - Main Program

This module serves as the central coordination point of the iRacing Manager.
It orchestrates the complete workflow:

1. Reading the configuration (via ConfigManager)
2. Starting all helper programs in the correct order (via ProcessManager)
3. Starting iRacing as the main program
4. Continuous monitoring of the iRacing process (via iRacingWatcher)
5. Automatically terminating all programs when iRacing is closed
6. Clean handling of signals and program termination

All external actions (process start, window minimization, process monitoring)
are delegated to the specialized helper modules.
"""

import os
import sys
import time
import logging
import signal
import atexit
import threading
import argparse # Import argparse
from typing import Dict, List, Any, Optional

# Import the other modules - updated imports for new structure
from src.utils.config_manager import ConfigManager, ConfigError
from src.core.process_manager import ProcessManager
from src.core.iracing_watcher import iRacingWatcher
from src.ui.console_ui import setup_console_ui

# Set up logger but don't add handlers yet - the console UI will handle that
logger = logging.getLogger("iRacingManager")
logger.setLevel(logging.INFO)

# We'll set up the console UI in the main function to ensure proper initialization order
# This will also properly redirect all output through our frame


class iRacingManager:
    """
    Main class for the iRacing Manager.

    This class forms the heart of the system and is responsible for:
    - Initialization and configuration of all components
    - Execution of the main workflow (program start and monitoring)
    - Handling of signals and clean termination
    - Response to the closing of iRacing

    The actual functionality is implemented by the following helper classes:
    - ConfigManager: Loads and manages the configuration
    - ProcessManager: Starts, minimizes, and terminates programs
    - iRacingWatcher: Monitors the iRacing process

    All actions are logged to facilitate troubleshooting.
    """

    def __init__(self, config_path: str = "config/config.json"):
        """
        Initializes the iRacing Manager.

        Args:
            config_path (str): Path to the configuration file. Default is 'config/config.json'.
        """
        logger.info("Initializing iRacing Manager...")
        self._cleanup_done = False # Initialize cleanup flag
        self.config_manager = ConfigManager(config_path)
        self.process_manager = ProcessManager()
        self.iracing_watcher = None
        self.main_program_info: Optional[Dict[str, Any]] = None
        self._stop_event = threading.Event() # Event to signal termination

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup) # Ensure cleanup runs on exit

    def _signal_handler(self, sig, frame) -> None:
        """
        Handler for operating system signals (SIGINT, SIGTERM).
        
        This method is called when:
        - The user presses Ctrl+C (SIGINT)
        - The system wants to terminate the program (SIGTERM)
        - Other termination signals are sent
        
        It ensures a clean termination by:
        1. Logging the signal
        2. Performing the cleanup (_cleanup)
        3. Terminating the program with exit code 0
        
        Args:
            sig: The received signal
            frame: The current stack frame
        """
        logger.info(f"Signal {sig} received. Initiating shutdown...")
        self._stop_event.set() # Signal the main loop to exit

    def _cleanup(self) -> None:
        """
        Central cleanup function for clean program termination.
        
        This method is called:
        - At normal program end
        - During signal handling (Ctrl+C)
        - By atexit (registered during initialization)
        - On unexpected errors
        
        It ensures the following cleanup tasks:
        1. Avoids multiple executions through the _cleanup_done flag
        2. Stops the iRacing monitoring if active
        3. Terminates all started programs through the ProcessManager
        
        This ensures that no processes continue running in the background,
        even if the iRacing Manager is unexpectedly terminated.
        """
        # Prevent multiple executions of the cleanup tasks
        if not self._cleanup_done:
            logger.info("Performing cleanup tasks...")

            # Mark as done immediately to prevent re-entry
            self._cleanup_done = True

            # Stop the monitoring if active
            # Check if iracing_watcher exists and has the method before calling
            if hasattr(self, 'iracing_watcher') and self.iracing_watcher:
                try:
                    self.iracing_watcher.stop_watching()
                except Exception as e:
                    logger.error(f"Error stopping iRacing watcher during cleanup: {e}")

            # Terminate all started programs
            # Check if process_manager exists and has the method before calling
            if hasattr(self, 'process_manager') and self.process_manager:
                try:
                    self.process_manager.terminate_all_programs()
                except Exception as e:
                    logger.error(f"Error terminating programs during cleanup: {e}")
            logger.info("Cleanup tasks finished.")


    def start_programs(self) -> bool:
        """
        Starts all configured programs in the correct order.
        
        This method:
        1. Loads the program configurations from the ConfigManager
        2. First starts all helper programs (non-iRacing)
        3. Then starts iRacing as the last program
        4. Performs a second minimization run for programs that could not be minimized immediately
        
        The two-stage start process ensures that all helper programs are already running
        when iRacing is started.

        Returns:
            bool: True if all programs were successfully started, otherwise False
        """
        logger.info("Starting all configured programs...")
        programs = self.config_manager.get_programs()
        main_program = self.config_manager.get_main_program()
        
        # Collect the non-iRacing programs
        other_programs = [program for program in programs if program != main_program]
        
        # First start the other programs
        logger.info(f"Starting {len(other_programs)} helper programs...")
        for program in other_programs:
            name = program["name"]
            
            # Start the program
            success, _ = self.process_manager.start_program(program)
            if not success:
                logger.error(f"Error starting '{name}'. Aborting.")
                return False
        
        # Start iRacing last
        logger.info(f"Starting main program: {main_program['name']}...")
        success, proc = self.process_manager.start_program(main_program)
        if not success:
            logger.error(f"Error starting '{main_program['name']}'. Aborting.")
            return False
        
        # Store information about the main program for monitoring
        self.main_program_info = {
            "config": main_program,
            "process": proc,
            "pid": proc.pid
        }
        
        # Try again to minimize all windows that were not minimized at first attempt
        logger.info("Performing second minimization run for programs...")
        self.process_manager.retry_minimize_all()
        
        return True

    def watch_iracing(self) -> None:
        """
        Starts the continuous monitoring of the iRacing process.
        
        This method:
        1. Checks if iRacing was successfully started
        2. Creates an iRacingWatcher with a callback for the termination (_on_iracing_exit)
        3. Finds the iRacing process using the stored information
        4. Starts the active monitoring in a separate thread
        
        The monitoring runs continuously in the background until iRacing is terminated
        or the user stops the manager with Ctrl+C.
        """
        if not self.main_program_info:
            logger.error("No main program found to monitor.")
            return
            
        logger.info("Starting the monitoring of the main program...")
        
        # Create the watcher with callback function
        self.iracing_watcher = iRacingWatcher(on_exit_callback=self._on_iracing_exit)
        
        # Find the iRacing process
        if not self.iracing_watcher.find_iracing_process(self.main_program_info):
            logger.error("Could not find the main program for monitoring.")
            return
            
        # Start the monitoring
        self.iracing_watcher.start_watching()
        
        logger.info(f"Monitoring of the main program active. Press Ctrl+C to exit.")

    def _on_iracing_exit(self) -> None:
        """
        Callback function triggered when iRacing is terminated.
        
        This central method is called by the iRacingWatcher as soon as
        the termination of the iRacing process is detected. It is the core
        of the automation functionality of the manager.
        
        The method performs the following actions:
        1. Logging the termination of iRacing
        2. Stopping the monitoring to free up resources
        3. Coordinated termination of all helper programs
        4. Logging of successful completion
        
        This function doesn't terminate the process itself but sets the
        watcher to a state that allows proper termination of the main loop.
        """
        logger.info("Main program has been terminated. Terminating all other programs...")
        
        # Stop the monitoring
        if self.iracing_watcher:
            self.iracing_watcher.stop_watching()
            
        # Terminate all started programs
        self.process_manager.terminate_all_programs()
        
        logger.info("All programs have been terminated.")
        self._stop_event.set() # Signal the main loop to exit

    def run(self) -> None:
        """
        Main method to execute the complete iRacing Manager workflow.
        
        This method coordinates the complete lifecycle of the manager:
        1. Logging of program start
        2. Starting all configured programs
        3. Setting up the iRacing monitoring
        4. Continuous checking of the monitoring status
        5. Catching user interruptions (KeyboardInterrupt)
        6. Calling the cleanup routines at program end
        
        The method implements a robust main loop that continuously
        monitors whether the iRacing process is still active and reacts accordingly.
        """
        # Start all programs
        if not self.start_programs():
            logger.error("Error starting the programs. Exiting...")
            self._cleanup()
            sys.exit(1)
        
        # Monitor iRacing
        self.watch_iracing()
        
        # Keep the main program running until the stop event is set
        # (either by iRacing exiting or by a signal like Ctrl+C)
        if self.iracing_watcher and self.iracing_watcher.is_watching():
            logger.info("Manager running in the background. Waiting for main program exit or Ctrl+C...")
            self._stop_event.wait() # Wait here until event is set
            logger.info("Stop event received.")
        elif not self.main_program_info:
             logger.warning("Main program info not available, cannot wait for termination signal.")
        else:
             logger.warning("iRacing watcher not active, cannot wait for termination signal.")

        # Cleanup is handled by atexit, no need for explicit call here unless specific logic needed before exit
        logger.info("iRacing Manager shutting down.")


def main() -> None:
    """
    Entry point for the iRacing Manager.
    
    This function:
    1. Parses command line arguments for an optional configuration path.
    2. Sets up the console UI with logo and framed log display.
    3. Creates an instance of iRacingManager.
    4. Starts the main method run().
    5. Catches configuration errors and unexpected exceptions, logs them, and exits.

    The function ensures clean error handling at the top level
    and is the main entry point of the program when directly executed.
    """
    parser = argparse.ArgumentParser(description="iRacing Manager - Start and manage iRacing and helper applications.")
    parser.add_argument(
        "-c", "--config",
        default="config/config.json",
        help="Path to the configuration file (default: config/config.json)"
    )
    args = parser.parse_args()

    try:
        # Set up the console UI with the ASCII logo and framed log display
        setup_console_ui(logger)
        
        # Create the iRacing Manager instance using the parsed config path
        manager = iRacingManager(config_path=args.config)

        # Start the main workflow
        manager.run()

    except (FileNotFoundError, ConfigError) as e:
        # Log specific configuration or file not found errors and exit
        logger.error(f"Initialization error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
         # Handle Ctrl+C gracefully during startup if needed (though signal handler should cover runtime)
         logger.info("Shutdown requested by user during startup.")
         # Cleanup might be partially done by atexit, but ensure manager cleanup runs if initialized
         if 'manager' in locals() and hasattr(manager, '_cleanup'):
             manager._cleanup()
         sys.exit(0)
    except Exception as e:
        # Log any other unexpected errors during startup or runtime
        logger.exception(f"An unexpected critical error occurred: {e}")
        # Attempt cleanup if manager was initialized
        if 'manager' in locals() and hasattr(manager, '_cleanup'):
             manager._cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()