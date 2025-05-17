#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
iRacing Manager - Main Entry Point

This file serves as the entry point for the iRacing Manager application.
It simply imports and calls the main function from the core module.
"""

import sys
import traceback # Add this import

if __name__ == "__main__":
    try:
        from src.core.iracing_manager import main # Move import here to catch import errors too
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()