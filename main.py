#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""iRacing Manager: Main entry point."""

import sys
import traceback

if __name__ == "__main__":
    try:
        from src.core.iracing_manager import main # Import main
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Traceback:")
        traceback.print_exc()