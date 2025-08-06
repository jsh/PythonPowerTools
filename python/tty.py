#!/usr/bin/env python3
"""
Name: tty
Description: return user's terminal name
Author:
License:
"""

import os
import sys

def main():
    """Checks for a TTY and prints its name."""
    # The file descriptor for standard input is 0.
    stdin_fd = sys.stdin.fileno()

    # Exit with an error if standard input is not a terminal.
    if not os.isatty(stdin_fd):
        # sys.exit() prints to stderr and exits with status 1.
        sys.exit("not a tty")

    # Get and print the name of the terminal for standard input.
    try:
        print(os.ttyname(stdin_fd))
    except OSError:
        # This handles cases where ttyname might fail.
        sys.exit("not a tty")

if __name__ == "__main__":
    main()
