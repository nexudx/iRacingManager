#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock Main Entry Point for iRacing Manager.

This file serves as an alternative entry point for the iRacing Manager 
application that uses mocks instead of real processes and Windows APIs.

It allows developers to run the full application workflow without starting
actual programs, using the mock system to simulate process and window behavior.
"""

import os
import sys
import time
import logging
import argparse
import threading
from typing import Dict, List, Any, Optional

# Add the parent directory to sys.path to import the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import mock modules first (must be imported before application modules)
from tests.mock_process import MockProcessManager, setup_mocks, restore_originals
from tests.mock_windows import MockWindowManager, setup_win32_mocks, restore_win32_originals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("MockMain")

def setup_mock_environment():
    """Set up all mocks needed for the simulation."""
    logger.info("Setting up mock environment...")
    
    # Patch process-related functions
    process_functions = setup_mocks()
    
    # Patch win32gui functions if available
    try:
        win32_functions = setup_win32_mocks()
    except ImportError:
        logger.warning("Windows-specific modules not available, some features will be simulated")
        win32_functions = {}
    
    # Patch the WINDOWS_IMPORTS_AVAILABLE flag to allow running on any platform
    from src.utils import process_utils
    process_utils.WINDOWS_IMPORTS_AVAILABLE = True
    
    logger.info("Mock environment set up successfully")
    return process_functions, win32_functions

def cleanup_mock_environment(process_functions, win32_functions):
    """Clean up the mock environment."""
    logger.info("Cleaning up mock environment...")
    
    # Restore original functions
    restore_originals(process_functions)
    
    if win32_functions:
        restore_win32_originals(win32_functions)
    
    # Reset mock state
    MockProcessManager.reset()
    MockWindowManager.reset()
    
    logger.info("Mock environment cleaned up")

def run_iracing_manager(config_path):
    """Run the iRacing Manager with mocks."""
    from src.core.iracing_manager import iRacingManager
    
    logger.info(f"Starting iRacing Manager with config: {config_path}")
    
    # Create manager instance
    manager = iRacingManager(config_path=config_path)
    
    # Start the manager (doesn't block since we use mocks)
    manager.run()
    
    logger.info("iRacing Manager run completed")
    return manager

def simulate_iracing_exit(manager, delay_seconds=5):
    """
    Simulate iRacing closing after a specified delay.
    
    Args:
        manager: The iRacing Manager instance
        delay_seconds: Seconds to wait before simulating iRacing exit
    """
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

def create_mock_windows(manager):
    """Create mock windows for each process."""
    logger.info("Creating mock windows for processes...")
    
    # Loop through all started processes
    for name, process_info in manager.process_manager.processes.items():
        pid = process_info["pid"]
        # Create a main window for each process
        main_hwnd = MockWindowManager.create_window(pid, f"{name} Main Window")
        
        # For programs that typically have multiple windows, create those too
        if "Oculus" in name:
            MockWindowManager.create_window(pid, "Oculus Debug Window")
            MockWindowManager.create_window(pid, "Oculus Settings")
    
    logger.info("Mock windows created")

def main():
    """Main entry point for the mock iRacing Manager."""
    parser = argparse.ArgumentParser(description='Run iRacing Manager with mocks')
    parser.add_argument(
        '--config', '-c',
        default='tests/test_config.json',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--delay', '-d',
        type=int,
        default=5,
        help='Seconds to wait before simulating iRacing exit'
    )
    parser.add_argument(
        '--no-auto-exit',
        action='store_true',
        help='Do not automatically simulate iRacing exit'
    )
    
    args = parser.parse_args()
    
    # Set up the mock environment
    process_functions, win32_functions = setup_mock_environment()
    
    try:
        # Run the manager
        manager = run_iracing_manager(args.config)
        
        # Create mock windows for visual components
        create_mock_windows(manager)
        
        # If auto-exit is enabled, simulate iRacing closing after the specified delay
        if not args.no_auto_exit:
            simulate_iracing_exit(manager, args.delay)
        
        # Wait for the stop event to be set (with a maximum timeout)
        # This happens when iRacing exits or when the user presses Ctrl+C
        timeout = args.delay + 10 if not args.no_auto_exit else 3600  # Long timeout if no auto-exit
        manager._stop_event.wait(timeout=timeout)
        
        # Wait a moment for cleanup to complete
        time.sleep(1)
        
    finally:
        # Clean up the mock environment
        cleanup_mock_environment(process_functions, win32_functions)
    
    logger.info("Mock iRacing Manager session completed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running mock iRacing Manager: {e}", exc_info=True)
        sys.exit(1)