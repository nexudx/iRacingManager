#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Manager - Main Entry Point

This file serves as the entry point for the iRacing Manager application.
It supports both normal mode and test mode (with mocked processes).
"""

import sys
import os
import argparse

def main():
    """
    Main entry point with support for real and test modes.
    
    When run with --test flag, uses the mock system instead of real processes.
    """
    parser = argparse.ArgumentParser(description="iRacing Manager - Start and manage iRacing and helper applications.")
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Path to the configuration file (default: config.json)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with mocked processes (no real programs started)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="In test mode, seconds to wait before simulating iRacing exit (default: 5)"
    )
    
    args = parser.parse_args()
    
    if args.test:
        # In test mode, use the mock system
        print("Starting iRacing Manager in TEST MODE (no real programs will be started)")
        run_test_mode(args.config, args.delay)
    else:
        # Normal mode - import and run the real manager
        from src.core.iracing_manager import main as run_real_manager
        run_real_manager()

def run_test_mode(config_path, delay_seconds=5):
    """Run the iRacing Manager with the mock system."""
    # Add the current directory to the path to ensure imports work
    if not os.path.dirname(__file__) in sys.path:
        sys.path.insert(0, os.path.dirname(__file__))
    
    # Import test modules
    try:
        from tests.mock_process import setup_mocks, restore_originals, MockProcessManager, MockPopen
        from tests.mock_windows import setup_win32_mocks, restore_win32_originals, MockWindowManager
        import logging
        import time
        import threading
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("TestMode")
        
        # Set up the mocks
        logger.info("Setting up test environment...")
        process_functions = setup_mocks()
        
        try:
            win32_functions = setup_win32_mocks()
        except ImportError:
            logger.warning("Windows-specific modules not available, some features will be simulated")
            win32_functions = {}
        
        # Patch the WINDOWS_IMPORTS_AVAILABLE flag
        from src.utils import process_utils
        process_utils.WINDOWS_IMPORTS_AVAILABLE = True
        
        # Use test config if not specified
        if config_path == "config.json":
            if os.path.exists("tests/test_config.json"):
                config_path = "tests/test_config.json"
                logger.info(f"Using test configuration: {config_path}")
        
        # Import and run the manager
        from src.core.iracing_manager import iRacingManager
        
        logger.info(f"Starting iRacing Manager in test mode with config: {config_path}")
        manager = iRacingManager(config_path=config_path)
        
        # Start the manager
        logger.info("Running the manager (won't block since we're using mocks)...")
        manager.run()
        
        # Create mock windows for each process
        logger.info("Creating mock windows for processes...")
        for name, process_info in manager.process_manager.processes.items():
            pid = process_info["pid"]
            # Create a main window for each process
            MockWindowManager.create_window(pid, f"{name} Main Window")
            
            # For programs that typically have multiple windows, create those too
            if "Oculus" in name:
                MockWindowManager.create_window(pid, "Oculus Debug Window")
        
        # Simulate iRacing exit if requested
        if delay_seconds > 0:
            if not manager.main_program_info:
                logger.error("Cannot simulate iRacing exit - main program info not available")
                return
            
            iracing_pid = manager.main_program_info["pid"]
            
            def delayed_exit():
                logger.info(f"Will simulate iRacing exit in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
                logger.info(f"Simulating iRacing (PID {iracing_pid}) termination...")
                MockProcessManager.terminate_process(iracing_pid)
            
            # Start the delayed exit in a separate thread
            exit_thread = threading.Thread(target=delayed_exit)
            exit_thread.daemon = True
            exit_thread.start()
            
            logger.info(f"Scheduled iRacing termination simulation after {delay_seconds} seconds")
            
            # Wait for the stop event to be set (with a maximum timeout)
            timeout = delay_seconds + 10
            manager._stop_event.wait(timeout=timeout)
            
            # Wait a moment for cleanup to complete
            time.sleep(1)
        else:
            logger.info("Test mode running indefinitely. Press Ctrl+C to exit.")
            try:
                # Wait for Ctrl+C or other interruption
                while not manager._stop_event.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
            
        logger.info("Test run completed")
        
    except ImportError as e:
        print(f"Error loading test modules: {e}")
        print("Make sure you have the test directory and modules installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error in test mode: {e}")
        sys.exit(1)
    finally:
        # Clean up the mocks
        if 'process_functions' in locals():
            restore_originals(process_functions)
        if 'win32_functions' in locals() and win32_functions:
            restore_win32_originals(win32_functions)

if __name__ == "__main__":
    main()