#!/usr/bin/env python3
"""
Name: rain
Description: let it rain
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl

A Python port of the 'rain' utility.

This program simulates rain on the terminal. Any command-line argument
will cause it to print its version and exit.
"""

import sys
import os

__version__ = "1.2"

def main():
    """
    Checks for command-line arguments to either print version info
    or start the infinite "rain" loop.
    """
    # If any command-line argument is given (e.g., 'rain --version'),
    # print the script's version information and exit.
    if len(sys.argv) > 1:
        script_name = os.path.basename(sys.argv[0])
        print(f"{script_name} (Python port) {__version__}")
        sys.exit(0)

    # This is the main "rain" loop.
    try:
        # Multiplying a string creates a repeated sequence.
        rain_line = "/" * 72
        while True:
            print(rain_line)
            
    except KeyboardInterrupt:
        # This allows the user to stop the script with Ctrl+C
        # without seeing a Python error message.
        sys.exit(0)
        
    except BrokenPipeError:
        # This handles cases where the output is piped to a command
        # that exits early (e.g., `python rain.py | head -n 10`).
        # It prevents a "Broken Pipe" error from being displayed.
        sys.stderr.close()

if __name__ == "__main__":
    main()
