#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for iRacing Manager.

This script provides a convenient entry point for running the tests
and checking if the testing framework is working as expected.
"""

import os
import sys
import time
import logging
import subprocess
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("TestScript")

def run_test_runner():
    """Run the automated test suite."""
    logger.info("Running test runner...")
    
    # Run the test runner and capture the output
    try:
        result = subprocess.run(
            ["python", "tests/test_runner.py"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Display stdout output
        logger.info("Test runner completed successfully.")
        print("\n--- Test Runner Output ---")
        print(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Test runner failed with error code {e.returncode}")
        # Display the error output
        print("\n--- Test Runner Error Output ---")
        print(e.stdout)
        print(e.stderr)
        
        return False

def run_mock_main():
    """Run the mock main script to verify interactive mode."""
    logger.info("Running mock main script...")
    
    # Run mock_main with a short delay
    try:
        result = subprocess.run(
            ["python", "tests/mock_main.py", "--delay", "3"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Display stdout output
        logger.info("Mock main script completed successfully.")
        print("\n--- Mock Main Output ---")
        print(result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Mock main script failed with error code {e.returncode}")
        # Display the error output
        print("\n--- Mock Main Error Output ---")
        print(e.stdout)
        print(e.stderr)
        
        return False

def check_test_files():
    """Check that all required test files exist."""
    logger.info("Checking test files...")
    
    required_files = [
        "tests/__init__.py",
        "tests/mock_process.py",
        "tests/mock_windows.py",
        "tests/test_runner.py",
        "tests/mock_main.py",
        "tests/test_config.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing test files: {', '.join(missing_files)}")
        return False
    
    logger.info("All required test files are present.")
    return True

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description='Validate iRacing Manager test framework')
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running the tests (just check files)'
    )
    
    args = parser.parse_args()
    
    logger.info("Validating iRacing Manager test framework...")
    
    # Check files first
    if not check_test_files():
        logger.error("Test validation failed: Missing required files.")
        sys.exit(1)
    
    if args.skip_tests:
        logger.info("Skipping test execution as requested.")
        logger.info("Test framework validation completed successfully.")
        sys.exit(0)
    
    # Run tests
    test_runner_success = run_test_runner()
    mock_main_success = run_mock_main()
    
    if test_runner_success and mock_main_success:
        logger.info("Test framework validation completed successfully.")
        sys.exit(0)
    else:
        logger.error("Test framework validation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()