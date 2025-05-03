#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mock Process Implementation for iRacing Manager Tests.

This module provides mock implementations of subprocess.Popen and psutil.Process
classes to simulate process behavior without actually starting processes.
This allows testing the iRacing Manager without running actual applications.

Key features:
1. MockPopen simulates subprocess.Popen behavior
2. MockProcess simulates psutil.Process behavior
3. MockProcessManager tracks all mock processes
4. Helper functions to manipulate process state during tests
"""

import time
import threading
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple

# Set up logger
logger = logging.getLogger("MockProcess")

class MockPopen:
    """
    Mock implementation of subprocess.Popen.
    
    Simulates a process without actually starting one. Includes:
    - pid property
    - poll() method to check if process is running
    - terminate() and kill() methods
    """
    
    def __init__(self, cmd, **kwargs):
        """Initialize a mock process."""
        # Get the next available PID from MockProcessManager
        self.pid = MockProcessManager.get_next_pid()
        self._cmd = cmd
        self._return_code = None  # None means process is running
        self._killed = False
        
        # Register this process with the manager
        MockProcessManager.register_process(self)
        logger.debug(f"Created mock process with PID {self.pid}: {cmd[0]}")
    
    def poll(self):
        """
        Check if the process has terminated.
        
        Returns:
            None if the process is running, or return code if terminated.
        """
        return self._return_code
    
    def terminate(self):
        """Simulate terminating the process."""
        if self._return_code is None:  # Only if still running
            self._return_code = 0
            MockProcessManager.terminate_process(self.pid)
            logger.debug(f"Terminated mock process with PID {self.pid}")
    
    def kill(self):
        """Simulate killing the process."""
        if self._return_code is None:  # Only if still running
            self._return_code = 1
            self._killed = True
            MockProcessManager.terminate_process(self.pid)
            logger.debug(f"Killed mock process with PID {self.pid}")


class MockProcess:
    """
    Mock implementation of psutil.Process.
    
    Simulates a psutil.Process object to allow testing process monitoring
    without actual processes.
    """
    
    def __init__(self, pid):
        """Initialize using a PID managed by MockProcessManager."""
        self.pid = pid
        self._status = "running"
        self._name = MockProcessManager.get_process_name(pid)
        
        if not MockProcessManager.is_pid_active(pid):
            from psutil import NoSuchProcess
            raise NoSuchProcess(pid=pid, name=self._name)
    
    def is_running(self):
        """Check if the process is still running."""
        return MockProcessManager.is_pid_active(self.pid)
    
    def name(self):
        """Get the name of the process."""
        return self._name
    
    def status(self):
        """Get the status of the process."""
        if not self.is_running():
            return "zombie"
        return self._status
    
    def terminate(self):
        """Terminate the process."""
        MockProcessManager.terminate_process(self.pid)
    
    def kill(self):
        """Kill the process."""
        MockProcessManager.terminate_process(self.pid)


class MockProcessManager:
    """
    Static manager class for tracking all mock processes.
    
    This class:
    - Assigns unique PIDs
    - Tracks active processes
    - Provides methods to query and manipulate processes for testing
    """
    
    _next_pid = 10000  # Start PIDs at 10000 to avoid conflicts with real processes
    _processes = {}    # Dict mapping PIDs to MockPopen instances
    _names = {}        # Dict mapping PIDs to process names
    
    @classmethod
    def reset(cls):
        """Reset all tracked processes and PIDs."""
        cls._processes = {}
        cls._names = {}
        cls._next_pid = 10000
        logger.debug("MockProcessManager reset")
    
    @classmethod
    def get_next_pid(cls):
        """Get the next available PID."""
        pid = cls._next_pid
        cls._next_pid += 1
        return pid
    
    @classmethod
    def register_process(cls, process: MockPopen):
        """Register a new mock process."""
        cls._processes[process.pid] = process
        
        # Extract name from command (use first part of path)
        if isinstance(process._cmd, list) and len(process._cmd) > 0:
            import os
            # Get the basename from the path
            name = os.path.basename(process._cmd[0])
            # Remove extension if present
            name = os.path.splitext(name)[0]
            cls._names[process.pid] = name
    
    @classmethod
    def terminate_process(cls, pid: int):
        """Terminate a process by PID."""
        if pid in cls._processes:
            process = cls._processes[pid]
            process._return_code = 0
            logger.debug(f"Marked process with PID {pid} as terminated")
    
    @classmethod
    def is_pid_active(cls, pid: int):
        """Check if a PID is active."""
        return pid in cls._processes and cls._processes[pid]._return_code is None
    
    @classmethod
    def get_process_name(cls, pid: int):
        """Get the name of a process by PID."""
        return cls._names.get(pid, "unknown")
    
    @classmethod
    def terminate_all(cls):
        """Terminate all active processes."""
        for pid in list(cls._processes.keys()):
            cls.terminate_process(pid)
    
    @classmethod
    def pid_exists(cls, pid: int):
        """Check if a PID exists (active or terminated)."""
        return pid in cls._processes


# Helper functions for testing

def mock_pid_exists(pid):
    """Mock implementation of psutil.pid_exists."""
    return MockProcessManager.pid_exists(pid)

def mock_Process(pid):
    """Mock implementation of psutil.Process constructor."""
    return MockProcess(pid)

def setup_mocks():
    """Set up all mocks for testing."""
    # Reset the process manager
    MockProcessManager.reset()
    
    # Patch psutil functions
    import psutil
    # Store original functions for restoration later
    original_functions = {
        'pid_exists': psutil.pid_exists,
        'Process': psutil.Process
    }
    
    # Replace with mock implementations
    psutil.pid_exists = mock_pid_exists
    psutil.Process = mock_Process
    
    # Patch subprocess.Popen
    import subprocess
    original_functions['Popen'] = subprocess.Popen
    subprocess.Popen = MockPopen
    
    return original_functions

def restore_originals(original_functions):
    """Restore original functions after testing."""
    # Restore psutil functions
    import psutil
    psutil.pid_exists = original_functions['pid_exists']
    psutil.Process = original_functions['Process']
    
    # Restore subprocess.Popen
    import subprocess
    subprocess.Popen = original_functions['Popen']