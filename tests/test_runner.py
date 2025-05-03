#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Runner for iRacing Manager.

This module provides a flexible test framework for the iRacing Manager
that works without starting actual processes. It uses mock objects to
simulate program behavior and allows testing the core functionality.

Key features:
1. Mocks all external dependencies (processes, windows, etc.)
2. Allows running the full iRacing Manager workflow in test mode
3. Provides simulated events (like iRacing termination)
4. Can test various scenarios and failure conditions
"""

import os
import sys
import time
import logging
import threading
import json
import argparse
from typing import Dict, List, Any, Optional, Callable

# Add the parent directory to sys.path to import the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import mock modules (must be imported before application modules)
from tests.mock_process import MockProcessManager, setup_mocks, restore_originals
from tests.mock_windows import MockWindowManager, setup_win32_mocks, restore_win32_originals

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("TestRunner")

class TestRunner:
    """
    Main test runner for the iRacing Manager.
    
    This class:
    - Sets up the mock environment
    - Runs the iRacing Manager with mocked components
    - Simulates events (like iRacing closing)
    - Validates the behavior
    """
    
    def __init__(self, config_path='tests/test_config.json'):
        """Initialize the test runner with the test configuration path."""
        self.config_path = config_path
        self.original_process_functions = None
        self.original_win32_functions = None
        self.manager = None
        self.WINDOWS_IMPORTS_AVAILABLE = True  # Force this to True for tests
    
    def setup(self):
        """Set up the test environment with mocks."""
        logger.info("Setting up test environment...")
        
        # Patch psutil and subprocess functions
        self.original_process_functions = setup_mocks()
        
        # Patch win32gui functions if available
        try:
            self.original_win32_functions = setup_win32_mocks()
        except ImportError:
            logger.warning("Windows-specific modules not available, some tests may be limited")
        
        # Patch the WINDOWS_IMPORTS_AVAILABLE flag to allow testing on any platform
        from src.utils import process_utils
        process_utils.WINDOWS_IMPORTS_AVAILABLE = True
        
        logger.info("Test environment set up successfully")
    
    def teardown(self):
        """Clean up the test environment after tests."""
        logger.info("Tearing down test environment...")
        
        # Restore original functions if they were patched
        if self.original_process_functions:
            restore_originals(self.original_process_functions)
        
        if self.original_win32_functions:
            restore_win32_originals(self.original_win32_functions)
        
        # Reset mock managers
        MockProcessManager.reset()
        MockWindowManager.reset()
        
        logger.info("Test environment cleaned up")
    
    def run_test(self, test_func, *args, **kwargs):
        """
        Run a specific test function with proper setup and teardown.
        
        Args:
            test_func: The test function to run
            *args, **kwargs: Arguments to pass to the test function
        """
        test_name = test_func.__name__
        logger.info(f"Starting test: {test_name}")
        
        try:
            self.setup()
            result = test_func(*args, **kwargs)  # Don't pass self again, test_func is already a method of self
            logger.info(f"Test {test_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}", exc_info=True)
            raise
        finally:
            self.teardown()
    
    def test_initialize_manager(self):
        """Test initializing the iRacing Manager."""
        from src.core.iracing_manager import iRacingManager
        
        logger.info("Testing manager initialization...")
        manager = iRacingManager(config_path=self.config_path)
        
        # Check that the manager initialized correctly
        assert manager.config_manager is not None, "Config manager was not initialized"
        assert manager.process_manager is not None, "Process manager was not initialized"
        
        logger.info("Manager initialization successful")
        return manager
    
    def test_start_programs(self):
        """Test starting programs from the configuration."""
        from src.core.iracing_manager import iRacingManager
        
        logger.info("Testing program start...")
        manager = iRacingManager(config_path=self.config_path)
        
        # Start all programs
        result = manager.start_programs()
        assert result is True, "Failed to start programs"
        
        # Check that processes were "started"
        programs = manager.config_manager.get_programs()
        for program in programs:
            name = program["name"]
            assert name in manager.process_manager.processes, f"Program {name} was not started"
        
        # Verify the main program was identified
        assert manager.main_program_info is not None, "Main program info was not set"
        
        logger.info("Program start test successful")
        return manager
    
    def test_watch_iracing(self):
        """Test the iRacing watching functionality."""
        # First start programs
        manager = self.test_start_programs()
        
        logger.info("Testing iRacing watching...")
        
        # Start watching
        manager.watch_iracing()
        
        # Verify watcher is active
        assert manager.iracing_watcher is not None, "iRacing watcher was not created"
        assert manager.iracing_watcher.is_watching(), "iRacing watcher is not active"
        
        logger.info("iRacing watching test successful")
        return manager
    
    def test_simulate_iracing_exit(self):
        """Test the behavior when iRacing exits."""
        # First start watching
        manager = self.test_watch_iracing()
        
        logger.info("Testing iRacing exit simulation...")
        
        # Get the main program PID
        iracing_pid = manager.main_program_info["pid"]
        
        # Simulate iRacing closing after a short delay
        def delayed_exit():
            time.sleep(1)  # Wait a bit to simulate running
            logger.info(f"Simulating iRacing (PID {iracing_pid}) termination...")
            MockProcessManager.terminate_process(iracing_pid)
        
        # Start the delayed exit in a separate thread
        exit_thread = threading.Thread(target=delayed_exit)
        exit_thread.daemon = True
        exit_thread.start()
        
        # Set a timeout to avoid hanging indefinitely
        manager._stop_event.wait(timeout=5)
        
        # Check that the manager reacted to the exit
        assert manager._stop_event.is_set(), "Manager did not detect iRacing exit"
        
        # Check if all processes were terminated
        running_programs = manager.process_manager.get_running_programs()
        assert len(running_programs) == 0, f"Not all programs were terminated: {running_programs}"
        
        logger.info("iRacing exit simulation test successful")
        return manager
    
    def test_full_workflow(self):
        """Test the full iRacing Manager workflow."""
        logger.info("Testing full workflow...")
        
        # Initialize manager
        manager = self.test_initialize_manager()
        
        # Start all programs
        result = manager.start_programs()
        assert result is True, "Failed to start programs"
        
        # Create mock windows for each process
        for name, process_info in manager.process_manager.processes.items():
            pid = process_info["pid"]
            # Create a main window for the process
            MockWindowManager.create_window(pid, f"{name} Window")
            
            # Create extra windows for some programs to test multiple window handling
            if name == "MockOculus":
                MockWindowManager.create_window(pid, "Oculus Debug Window")
        
        # Start watching iRacing
        manager.watch_iracing()
        
        # Simulate running for a short time
        time.sleep(1)
        
        # Simulate iRacing closing
        iracing_pid = manager.main_program_info["pid"]
        logger.info(f"Simulating iRacing (PID {iracing_pid}) termination...")
        MockProcessManager.terminate_process(iracing_pid)
        
        # Wait for the manager to react (with timeout)
        manager._stop_event.wait(timeout=5)
        
        # Verify all processes were terminated
        running_programs = manager.process_manager.get_running_programs()
        assert len(running_programs) == 0, f"Not all programs were terminated: {running_programs}"
        
        logger.info("Full workflow test successful")
        return manager


def run_all_tests():
    """Run all test cases."""
    runner = TestRunner()
    
    tests = [
        runner.test_initialize_manager,
        runner.test_start_programs,
        runner.test_watch_iracing,
        runner.test_simulate_iracing_exit,
        runner.test_full_workflow
    ]
    
    success_count = 0
    for test in tests:
        try:
            runner.run_test(test)
            success_count += 1
        except Exception:
            # The error was already logged in run_test
            pass
    
    logger.info(f"Test summary: {success_count}/{len(tests)} tests passed")
    return success_count == len(tests)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run iRacing Manager tests')
    parser.add_argument(
        '--config', '-c',
        default='tests/test_config.json',
        help='Path to test configuration file'
    )
    parser.add_argument(
        '--test', '-t',
        choices=['all', 'init', 'start', 'watch', 'exit', 'workflow'],
        default='all',
        help='Specific test to run'
    )
    
    args = parser.parse_args()
    
    # Create a runner with the specified config
    runner = TestRunner(config_path=args.config)
    
    # Run the selected test
    if args.test == 'all':
        success = run_all_tests()
    elif args.test == 'init':
        success = runner.run_test(runner.test_initialize_manager)
    elif args.test == 'start':
        success = runner.run_test(runner.test_start_programs)
    elif args.test == 'watch':
        success = runner.run_test(runner.test_watch_iracing)
    elif args.test == 'exit':
        success = runner.run_test(runner.test_simulate_iracing_exit)
    elif args.test == 'workflow':
        success = runner.run_test(runner.test_full_workflow)
    
    sys.exit(0 if success else 1)