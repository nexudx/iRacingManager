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
from typing import List, Optional, Dict, Any
import threading

# Bitmap-style logo for iRacing Manager
IRACING_LOGO = r"""
╔──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╗
│                                                                                                                      │
│                                _  ____               _                                                               │
│                               (_)|  _ \  __ _   ___ (_) _ __    __ _                                                 │
│                               | || |_) |/ _` | / __|| || '_ \  / _` |                                                │
│                               | ||  _ <| (_| || (__ | || | | || (_| |                                                │
│                               |_||_| \_\\__,_| \___||_||_| |_| \__, |                                                │
│                                          __  __                |___/                                                 │
│                                         |  \/  |  __ _  _ __    __ _   __ _   ___  _ __                              │
│                                         | |\/| | / _` || '_ \  / _` | / _` | / _ \| '__|                             │
│                                         | |  | || (_| || | | || (_| || (_| ||  __/| |                                │
│                                         |_|  |_| \__,_||_| |_| \__,_| \__, | \___||_|                                │
│                                                                       |___/                                          │
│                                                                                                                      │
╚──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╝
"""

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
    
    The frame is optimized for a terminal width of 120 characters and can display
    a configurable number of log messages (default 5).
    """
    
    def __init__(self, max_messages: int = 14, width: Optional[int] = None):
        """
        Initialize the log frame.
        
        Args:
            max_messages (int): Maximum number of log messages to display (default: 15)
            width (Optional[int]): Frame width, defaults to terminal width or 120
        """
        self.max_messages = max_messages
        columns, _ = get_terminal_size()
        self.width = width or columns or 120
        self.messages = []
        self.lock = threading.Lock()
        
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
    
    def render(self) -> str:
        """
        Render the framed log display.
        
        Returns:
            str: The complete framed log display as a string
        """
        with self.lock:
            # Calculate inner width (accounting for frame borders and padding)
            inner_width = self.width - 4  # 2 chars for borders and 2 for padding
            
            # Build the frame
            frame = []
            
            # Top border
            frame.append(f"{FRAME['top_left']}{FRAME['horizontal'] * (self.width - 2)}{FRAME['top_right']}")
            
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
            
            # Clear screen and redraw
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Use direct access to sys.__stdout__ to bypass our redirect for the frame itself
            # This ensures the frame display doesn't recursively log itself
            sys.__stdout__.write(IRACING_LOGO + "\n")
            sys.__stdout__.write(self.log_frame.render() + "\n")
            sys.__stdout__.flush()
            
            # No need to flush redirected stdout
        except Exception:
            self.handleError(record)


def setup_console_ui(logger: logging.Logger, max_log_messages: int = 10) -> LogFrameHandler:
    """
    Set up the console UI with logo and framed log display.
    
    Args:
        logger (logging.Logger): The logger to attach the handler to
        max_log_messages (int): Maximum number of log messages to display (default: 15)
        
    Returns:
        LogFrameHandler: The configured log handler
    """
    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Create log frame and handler
    log_frame = LogFrame(max_messages=max_log_messages)
    handler = LogFrameHandler(log_frame)
    
    # Configure formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Print initial empty frame through our redirected system
    handler.emit(logging.LogRecord("startup", logging.INFO, "", 0, "Starting iRacing Manager...", None, None))
    
    # Redirect stdout and stderr to ensure all output stays within the frame
    sys.stdout = OutputRedirector(log_frame, logger)
    sys.stderr = OutputRedirector(log_frame, logger, is_stderr=True)
    
    return handler


# For testing purposes when run directly
if __name__ == "__main__":
    # Set up logging - but don't use basicConfig which sets up its own handlers
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Make sure any existing handlers are removed
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Set up console UI - this will configure our custom handler
    setup_console_ui(logger)
    
    # Log some test messages
    logger.info("Starting test application")
    time.sleep(1)
    logger.debug("This is a debug message")
    time.sleep(1)
    logger.info("Processing data...")
    time.sleep(1)
    logger.warning("Resource usage is high")
    time.sleep(1)
    logger.error("Failed to connect to server")
    time.sleep(1)
    logger.info("Test complete")