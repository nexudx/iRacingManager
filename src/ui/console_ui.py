#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Console UI elements for the iRacing Manager.

This module provides visual enhancements for the console interface including:
1. ASCII art logo display
2. Framed log display for a cleaner, more professional console output
3. Helper functions for terminal formatting

The UI elements are optimized for a terminal size of 120x30 characters.
"""

import logging
import sys
import time
import os
import shutil
from typing import List, Optional, Dict, Any, Tuple
import threading

# ASCII art logo lines for iRacing Manager
LOGO_LINES = [
    "_  ____               _              ",
    "(_)|  _ \\  __ _   ___ (_) _ __    __ _ ",
    "| || |_) |/ _` | / __|| || '_ \\  / _` |",
    "| ||  _ <| (_| || (__ | || | | || (_| |",
    "|_||_| \\_\\\\__,_| \\___||_||_| |_| \\__, |",
    "  __  __                         |___/ ",
    "           |  \\/  |  __ _  _ __    __ _   __ _   ___  _ __  ",
    "          | |\\/| | / _` || '_ \\  / _` | / _` | / _ \\| '__|",
    "          | |  | || (_| || | | || (_| || (_| ||  __/| |   ",
    "          |_|  |_| \\__,_||_| |_| \\__,_| \\__, | \\___||_|   ",
    "                                        |___/             "
]


# Frame characters for the log display box - Unicode and ASCII versions
UNICODE_FRAME = {
    'top_left': '╭',
    'top_right': '╮',
    'bottom_left': '╰',
    'bottom_right': '╯',
    'horizontal': '─',
    'vertical': '│',
}

# ASCII frame characters for better compatibility with more terminals
ASCII_FRAME = {
    'top_left': '+',
    'top_right': '+',
    'bottom_left': '+',
    'bottom_right': '+',
    'horizontal': '-',
    'vertical': '|',
}

# Determine which frame style to use based on platform and environment
def get_frame_chars():
    """Select appropriate frame characters based on terminal capabilities."""
    # Use ASCII frame on Windows by default for better compatibility
    if os.name == 'nt':
        return ASCII_FRAME
    else:
        return UNICODE_FRAME

# Select frame characters to use
FRAME = get_frame_chars()

# Terminal colors and styles
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'red': '\033[31m',
    'bg_black': '\033[40m',
}

# Get terminal size or use default
def get_terminal_size():
    """Get current terminal size or default to 120x30."""
    terminal_size = shutil.get_terminal_size((120, 30))
    return terminal_size.columns, terminal_size.lines

class LogFrame:
    """
    Manages a framed log display in the console that shows the most recent log messages.
    
    The frame dynamically adjusts to the terminal width and can display
    a configurable number of log messages.
    """
    
    def __init__(self, max_messages: int = 14, width: Optional[int] = None, frame_type: str = "log"):
        """
        Initialize the frame.
        
        Args:
            max_messages (int): Maximum number of log messages to display (default: 14)
            width (Optional[int]): Frame width, defaults to terminal width or 120
            frame_type (str): Type of frame to create - "log" or "logo" (default: "log")
        """
        self.max_messages = max_messages
        columns, _ = get_terminal_size()
        self.width = width or columns or 120
        self.messages = []
        self.lock = threading.Lock()
        self.frame_type = frame_type
        
    def _clean_message(self, message: str) -> str:
        """
        Clean a log message by removing any trailing 'X' characters and whitespace.
        
        Args:
            message (str): Message to clean
            
        Returns:
            str: Cleaned message
        """
        # First remove any basic whitespace
        clean_message = message.rstrip()
        
        # Remove trailing 'X' characters
        while clean_message.endswith('X'):
            clean_message = clean_message[:-1].rstrip()
            
        return clean_message
        
    def _truncate_message(self, message: str, max_length: int) -> str:
        """
        Truncate message if it's longer than max_length.
        
        Args:
            message (str): Message to truncate
            max_length (int): Maximum length
            
        Returns:
            str: Truncated message
        """
        # Clean the message first
        clean_message = self._clean_message(message)
        
        if len(clean_message) > max_length:
            return clean_message[:max_length-3] + "..."
        return clean_message
    
    def add_message(self, message: str) -> None:
        """
        Add a new message to the log frame.
        
        Args:
            message (str): The log message to add
        """
        with self.lock:
            # Keep only the most recent messages up to max_messages
            self.messages.append(message)
            if len(self.messages) > self.max_messages:
                self.messages.pop(0)
    
    def _get_level_color(self, message: str) -> str:
        """Get appropriate color based on log level in the message."""
        if " - ERROR - " in message:
            return COLORS['red']
        elif " - WARNING - " in message:
            return COLORS['yellow']
        elif " - INFO - " in message:
            return COLORS['green']
        elif " - DEBUG - " in message:
            return COLORS['blue']
        return COLORS['reset']
    
    def update_width(self, new_width: int) -> None:
        """
        Update the frame width to match the current terminal width.
        
        Args:
            new_width (int): New width for the frame
        """
        with self.lock:
            self.width = new_width
    
    def render(self) -> str:
        """
        Render the framed display (either log or logo).
        
        Returns:
            str: The complete framed display as a string
        """
        with self.lock:
            # Calculate inner width (accounting for frame borders and padding)
            inner_width = self.width - 4  # 2 chars for borders and 2 for padding
            
            # Build the frame
            frame = []
            
            # Top border
            frame.append(f"{FRAME['top_left']}{FRAME['horizontal'] * (self.width - 2)}{FRAME['top_right']}")
            
            # Handle logo frame
            if self.frame_type == "logo":
                # Empty line above logo
                frame.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}")
                
                # Add logo lines with centering
                for line in LOGO_LINES:
                    # Shift logo text 6 characters to the left from center
                    padding_left = max(0, (inner_width - len(line)) // 2 - 6)  # Ensure padding doesn't go negative
                    padding_right = inner_width - len(line) - padding_left
                    frame.append(f"{FRAME['vertical']} {' ' * padding_left}{line}{' ' * padding_right} {FRAME['vertical']}")
                
                # Empty line below logo
                frame.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}")
                
            # Handle log frame
            else:
                # If no messages, show empty frame with placeholder
                if not self.messages:
                    placeholder = "No log messages yet"
                    padding_left = (inner_width - len(placeholder)) // 2
                    padding_right = inner_width - len(placeholder) - padding_left
                    frame.append(f"{FRAME['vertical']} {' ' * padding_left}{placeholder}{' ' * padding_right} {FRAME['vertical']}")
                else:
                    # Fill with messages or empty lines
                    for i in range(self.max_messages):
                        if i < len(self.messages):
                            msg = self.messages[i]
                            color = self._get_level_color(msg)
                            # First truncate and clean the message
                            msg = self._truncate_message(msg, inner_width - 2)  # Account for colored dot and space
                            
                            # Get the plain message without color codes for proper length calculation
                            plain_msg = msg  # Create a copy for measurement
                            for color_code in COLORS.values():
                                plain_msg = plain_msg.replace(color_code, '')
                            
                            # Calculate correct padding without any trailing characters
                            # This ensures the 'X' characters don't impact padding calculation
                            visible_length = len(plain_msg) + 2  # +2 for dot and space
                            padding = ' ' * max(0, inner_width - visible_length)
                            
                            # Add colored dot at the beginning instead of coloring the whole message
                            colored_dot = f"{color}●{COLORS['reset']}"
                            frame.append(f"{FRAME['vertical']} {colored_dot} {msg}{padding} {FRAME['vertical']}")
                        else:
                            # Empty line for unused message slots
                            frame.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}")
            
            # Bottom border
            frame.append(f"{FRAME['bottom_left']}{FRAME['horizontal'] * (self.width - 2)}{FRAME['bottom_right']}")
            
            return '\n'.join(frame)

# Custom stdout/stderr redirection handler to ensure all output is inside the frame
class OutputRedirector:
    """
    Redirects stdout and stderr to the log frame to ensure all output stays within the frame.
    """
    def __init__(self, log_frame, logger, is_stderr=False):
        self.log_frame = log_frame
        self.logger = logger
        self.is_stderr = is_stderr
        self.prefix = "STDERR: " if is_stderr else "STDOUT: "

    def write(self, text):
        if text.strip():  # Only process non-empty output
            level = logging.ERROR if self.is_stderr else logging.INFO
            self.logger.log(level, f"{self.prefix}{text.strip()}")

    def flush(self):
        pass  # Required for stdout/stderr compatibility


class TerminalSizeMonitor:
    """
    Monitors terminal size changes in a background thread and updates UI frames.
    
    This class runs a background thread that periodically checks the terminal
    dimensions and triggers a UI refresh when the size changes, ensuring that
    frames stay properly sized even when no log messages are being generated.
    """
    
    def __init__(self, update_callback, check_interval: float = 0.5):
        """
        Initialize the terminal size monitor.
        
        Args:
            update_callback: Function to call when terminal size changes
            check_interval: How often to check terminal size in seconds (default: 0.5)
        """
        self.update_callback = update_callback
        self.check_interval = check_interval
        self.last_size: Tuple[int, int] = (0, 0)
        self._stop_event = threading.Event()
        self._thread = None
    
    def _monitor_loop(self):
        """Background thread loop that checks terminal size regularly."""
        while not self._stop_event.is_set():
            current_size = get_terminal_size()
            
            # If size changed, call the update callback
            if current_size != self.last_size:
                self.last_size = current_size
                self.update_callback(current_size[0], current_size[1])
            
            # Sleep for the check interval
            time.sleep(self.check_interval)
    
    def start(self):
        """Start the terminal size monitoring thread."""
        if self._thread is None or not self._thread.is_alive():
            self.last_size = get_terminal_size()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
    
    def stop(self):
        """Stop the terminal size monitoring thread."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)


class LogFrameHandler(logging.Handler):
    """
    Custom logging handler that displays messages in a framed log display.
    
    This handler captures log messages and displays them in a framed box
    in the console, providing a cleaner and more professional appearance.
    """
    
    def __init__(self, log_frame: LogFrame):
        """
        Initialize the handler with a LogFrame instance.
        
        Args:
            log_frame (LogFrame): The log frame to display messages in
        """
        super().__init__()
        self.log_frame = log_frame
        self.logo_frame = None  # Will be initialized in emit
        self.size_monitor = None  # Will be initialized in emit
        self.render_lock = threading.Lock()  # Lock for thread-safe rendering
        self._enable_resize_monitoring = True  # By default, enable resize monitoring
        
    def update_ui_on_resize(self, terminal_width: int, terminal_height: int):
        """
        Update the UI frames when terminal size changes.
        
        Args:
            terminal_width (int): New terminal width
            terminal_height (int): New terminal height
        """
        with self.render_lock:
            try:
                # Calculate appropriate number of log messages based on terminal height
                # Logo frame height is fixed (LOGO_LINES plus padding), but log frame should adjust
                
                # Logo frame has LOGO_LINES + 2 padding lines + 2 border lines
                logo_frame_height = len(LOGO_LINES) + 4
                
                # Calculate available space for log frame (minus 3 for spacing and borders)
                available_height = max(5, terminal_height - logo_frame_height - 3)
                
                # Number of messages = available height minus top and bottom borders
                adjusted_max_messages = available_height - 2
                
                # Ensure it's not less than 1
                adjusted_max_messages = max(1, adjusted_max_messages)
                
                # Update log frame dimensions
                self.log_frame.update_width(terminal_width)
                self.log_frame.max_messages = adjusted_max_messages
                
                # Initialize or update logo frame with current terminal width
                if self.logo_frame is None:
                    self.logo_frame = LogFrame(width=terminal_width, frame_type="logo")
                else:
                    self.logo_frame.update_width(terminal_width)
                
                # Clear screen and redraw
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Use direct access to sys.__stdout__ to bypass our redirect for the frame itself
                # This ensures the frame display doesn't recursively log itself
                sys.__stdout__.write(self.logo_frame.render() + "\n")
                sys.__stdout__.write(self.log_frame.render() + "\n")
                sys.__stdout__.flush()
            except Exception as e:
                # Handle any errors during UI update
                # Can't use logger here as it might cause recursion
                sys.__stderr__.write(f"Error updating UI: {str(e)}\n")
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Process a log record by adding it to the log frame.
        
        Args:
            record (logging.LogRecord): The log record to process
        """
        try:
            # Format the message
            message = self.format(record)
            self.log_frame.add_message(message)
            
            # Get current terminal dimensions
            terminal_width, terminal_height = get_terminal_size()
            
            # Start terminal size monitoring if not already started and if enabled
            if self._enable_resize_monitoring and self.size_monitor is None:
                self.size_monitor = TerminalSizeMonitor(self.update_ui_on_resize)
                self.size_monitor.start()
            
            # Update UI with the new message
            self.update_ui_on_resize(terminal_width, terminal_height)
        except Exception:
            self.handleError(record)
    
    def close(self):
        """
        Close the handler and stop any background threads.
        
        This overrides the base class close method to ensure proper cleanup
        of background threads when the handler is removed from a logger.
        """
        # Stop the terminal size monitor thread if running
        if self.size_monitor is not None:
            self.size_monitor.stop()
            self.size_monitor = None
        
        # Call parent class close method
        super().close()


def setup_console_ui(logger: logging.Logger, max_log_messages: int = 10, test_mode: bool = False,
                    monitor_resize: bool = True) -> LogFrameHandler:
    """
    Set up the console UI with logo and framed log display.
    
    Args:
        logger (logging.Logger): The logger to attach the handler to
        max_log_messages (int): Maximum number of log messages to display (default: 10)
        test_mode (bool): If True, prevents programs from starting and stopping during testing (default: False)
        monitor_resize (bool): If True, monitors terminal size changes in background (default: True)
        
    Returns:
        LogFrameHandler: The configured log handler
    """
    # Clear the console
    if not test_mode:
        os.system('cls' if os.name == 'nt' else 'clear')
    
    # Create log frame and handler
    log_frame = LogFrame(max_messages=max_log_messages)
    handler = LogFrameHandler(log_frame)
    handler._enable_resize_monitoring = monitor_resize
    
    # Configure formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Print initial empty frame through our redirected system
    handler.emit(logging.LogRecord("startup", logging.INFO, "", 0,
                                 "Starting iRacing Manager..." + (" (TEST MODE)" if test_mode else ""),
                                 None, None))
    
    # Redirect stdout and stderr to ensure all output stays within the frame
    if not test_mode:
        sys.stdout = OutputRedirector(log_frame, logger)
        sys.stderr = OutputRedirector(log_frame, logger, is_stderr=True)
    
    return handler