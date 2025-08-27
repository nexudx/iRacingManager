#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Console UI: ASCII logo, framed log display. Optimized for 120x30."""

import logging
import sys
import time
import os
import shutil
from typing import List, Optional, Dict, Any, Tuple
import threading

# Logo
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


# Frame chars
UNICODE_FRAME = {
    'top_left': '╭',
    'top_right': '╮',
    'bottom_left': '╰',
    'bottom_right': '╯',
    'horizontal': '─',
    'vertical': '│',
}

# ASCII frame (compatibility)
ASCII_FRAME = {
    'top_left': '+',
    'top_right': '+',
    'bottom_left': '+',
    'bottom_right': '+',
    'horizontal': '-',
    'vertical': '|',
}

# Select frame style
def get_frame_chars():
    """Selects frame chars (ASCII for Windows, Unicode otherwise)."""
    if os.name == 'nt': # ASCII on Windows for compatibility
        return ASCII_FRAME
    else:
        return UNICODE_FRAME

# Frame chars to use
FRAME = get_frame_chars()

# Colors
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

# Terminal size
def get_terminal_size():
    """Gets terminal size (default 120x30)."""
    cols, lines = shutil.get_terminal_size((120, 30))
    return cols, lines

class LogFrame:
    """Manages a framed console log display. Adapts to terminal width."""
    
    def __init__(self, max_messages: int = 14, width: Optional[int] = None, frame_type: str = "log"):
        """Init. Args: max_messages (int), width (Optional[int]), frame_type (str: "log"/"logo")."""
        self.max_messages = max_messages
        columns, _ = get_terminal_size()
        self.width = width or columns or 120
        self.messages = []
        self.lock = threading.Lock()
        self.frame_type = frame_type
        
    def _clean_message(self, message: str) -> str:
        """Removes trailing 'X's and whitespace from message. Returns cleaned str."""
        clean_msg = message.rstrip() # Basic whitespace
        
        while clean_msg.endswith('X'): # Trailing 'X' artifacts
            clean_msg = clean_msg[:-1].rstrip()
            
        return clean_msg
        
    def _truncate_message(self, message: str, max_length: int) -> str:
        """Cleans then truncates message if > max_length. Returns str."""
        clean_msg = self._clean_message(message) # Clean first
        
        if len(clean_msg) > max_length:
            return clean_msg[:max_length-3] + "..."
        return clean_msg
    
    def add_message(self, message: str) -> None:
        """Adds message to log frame."""
        with self.lock:
            self.messages.append(message) # Add
            if len(self.messages) > self.max_messages: # Prune old
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
        """Updates frame width."""
        with self.lock:
            self.width = new_width
    
    def render(self) -> str:
        """Renders framed log or logo. Returns str."""
        with self.lock:
            # Calculate inner width (accounting for frame borders and padding)
            inner_width = self.width - 4  # Borders + padding
            
            frame_lines = []
            
            frame_lines.append(f"{FRAME['top_left']}{FRAME['horizontal'] * (self.width - 2)}{FRAME['top_right']}") # Top
            
            if self.frame_type == "logo": # Logo frame
                frame_lines.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}") # Padding line
                for line in LOGO_LINES: # Center logo (shifted left)
                    pad_left = max(0, (inner_width - len(line)) // 2 - 6)
                    pad_right = inner_width - len(line) - pad_left
                    frame_lines.append(f"{FRAME['vertical']} {' ' * pad_left}{line}{' ' * pad_right} {FRAME['vertical']}")
                frame_lines.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}") # Padding line
                
            else: # Log frame
                if not self.messages: # Placeholder if no messages
                    placeholder = "No log messages yet"
                    pad_left = (inner_width - len(placeholder)) // 2
                    pad_right = inner_width - len(placeholder) - pad_left
                    frame_lines.append(f"{FRAME['vertical']} {' ' * pad_left}{placeholder}{' ' * pad_right} {FRAME['vertical']}")
                else:
                    for i in range(self.max_messages): # Fill with messages/empty lines
                        if i < len(self.messages):
                            msg = self.messages[i]
                            color = self._get_level_color(msg)
                            msg = self._truncate_message(msg, inner_width - 2)  # Truncate (dot + space)
                            
                            plain_msg = msg # For length calc
                            for code in COLORS.values(): plain_msg = plain_msg.replace(code, '')
                            
                            visible_len = len(plain_msg) + 2  # Dot + space
                            padding = ' ' * max(0, inner_width - visible_len)
                            
                            dot = f"{color}●{COLORS['reset']}" # Colored dot
                            frame_lines.append(f"{FRAME['vertical']} {dot} {msg}{padding} {FRAME['vertical']}")
                        else:
                            frame_lines.append(f"{FRAME['vertical']} {' ' * inner_width} {FRAME['vertical']}") # Empty line
            
            frame_lines.append(f"{FRAME['bottom_left']}{FRAME['horizontal'] * (self.width - 2)}{FRAME['bottom_right']}") # Bottom
            
            return '\n'.join(frame_lines)
# Output redirection
class OutputRedirector:
    """Redirects stdout/stderr to log frame."""
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
    """Monitors terminal size changes in bg thread, updates UI frames."""
    
    def __init__(self, update_callback, check_interval: float = 0.5):
        """Init. Args: update_callback (Callable), check_interval (float)."""
        self.update_callback = update_callback
        self.check_interval = check_interval
        self.last_size: Tuple[int, int] = (0, 0)
        self._stop_event = threading.Event()
        self._thread = None
    
    def _monitor_loop(self):
        """BG thread: checks terminal size, calls update_callback on change."""
        while not self._stop_event.is_set():
            curr_size = get_terminal_size()
            
            if curr_size != self.last_size: # Size changed
                self.last_size = curr_size
                self.update_callback(curr_size[0], curr_size[1])
            
            time.sleep(self.check_interval) # Check interval
    
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
    """Custom logging handler for framed log display."""
    
    def __init__(self, log_frame: LogFrame):
        """Init. Args: log_frame (LogFrame)."""
        super().__init__()
        self.log_frame = log_frame
        self.logo_frame = None  # Will be initialized in emit
        self.size_monitor = None  # Will be initialized in emit
        self.render_lock = threading.Lock()  # Thread-safe rendering
        self._enable_resize_monitoring = True  # Enable resize monitoring by default
        
    def update_ui_on_resize(self, terminal_width: int, terminal_height: int):
        """Updates UI frames on terminal resize. Adjusts log messages based on height."""
        with self.render_lock:
                try:
                    # Calculate log messages based on terminal height.
                    # Logo frame: fixed height (LOGO_LINES + padding + borders).
                    # Log frame: adjusts to remaining space.
                    
                    logo_h = len(LOGO_LINES) + 4 # Logo height
                    
                    # Available log content height (subtract logo, spacing, log borders)
                    avail_log_h = max(5, terminal_height - logo_h - 3)
                    
                    adj_max_msgs = max(1, avail_log_h) # At least 1 message
                    
                    self.log_frame.update_width(terminal_width) # Update log frame
                    self.log_frame.max_messages = adj_max_msgs
                    
                    if self.logo_frame is None: # Init/update logo frame
                        self.logo_frame = LogFrame(width=terminal_width, frame_type="logo")
                    else:
                        self.logo_frame.update_width(terminal_width)
                    
                    os.system('cls' if os.name == 'nt' else 'clear') # Clear & redraw
                    
                    # Use sys.__stdout__ to bypass redirect for frame (prevent recursion)
                    sys.__stdout__.write(self.logo_frame.render() + "\n")
                    sys.__stdout__.write(self.log_frame.render() + "\n")
                    sys.__stdout__.flush()
                except Exception as e:
                    sys.__stderr__.write(f"Error updating UI: {str(e)}\n") # UI update errors
    def emit(self, record: logging.LogRecord) -> None:
        """Processes log record, adds to frame, updates UI."""
        try:
            msg = self.format(record) # Format
            self.log_frame.add_message(msg) # Add to frame
            
            term_w, term_h = get_terminal_size() # Current dimensions
            
            # Start size monitor if enabled and not running
            if self._enable_resize_monitoring and self.size_monitor is None:
                self.size_monitor = TerminalSizeMonitor(self.update_ui_on_resize)
                self.size_monitor.start()
            
            self.update_ui_on_resize(term_w, term_h) # Update UI
        except Exception:
            self.handleError(record)
    
    def close(self):
        """Closes handler, stops background threads."""
        if self.size_monitor is not None: # Stop size monitor
            self.size_monitor.stop()
            self.size_monitor = None
        
        super().close() # Parent close


def setup_console_ui(logger: logging.Logger, max_log_messages: int = 10, test_mode: bool = False,
                    monitor_resize: bool = True) -> LogFrameHandler:
    """Sets up console UI (logo, framed log). Returns LogFrameHandler."""
    if not test_mode: # Clear console
        os.system('cls' if os.name == 'nt' else 'clear')
    
    log_frame = LogFrame(max_messages=max_log_messages) # Create frame/handler
    handler = LogFrameHandler(log_frame)
    handler._enable_resize_monitoring = monitor_resize
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') # Formatter
    handler.setFormatter(formatter)
    
    logger.addHandler(handler) # Add handler
    
    # Initial frame via redirected system
    handler.emit(logging.LogRecord("startup", logging.INFO, "", 0,
                                 "Starting iRacing Manager..." + (" (TEST MODE)" if test_mode else ""),
                                 None, None))
    
    if not test_mode: # Redirect stdout/stderr
        sys.stdout = OutputRedirector(log_frame, logger)
        sys.stderr = OutputRedirector(log_frame, logger, is_stderr=True)
    
    return handler