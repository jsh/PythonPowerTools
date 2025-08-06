#!/usr/bin/env python3
"""
Name: yes
Description: print out a string till doomsday
Author: Michael Mikonos, mb@iinet.net.au (Perl version)
License: perl

A Python port of the 'yes' utility.

This program repeatedly prints a string to standard output until it is
terminated (e.g., with Ctrl+C). If command-line arguments are provided,
they are joined together to form the string. If no arguments are given,
the default string is 'y'.
"""

import sys
import os

__version__ = "1.3"

def main():
    """Determines the string and prints it in an infinite loop."""
    # Check for command-line arguments. If none, default to 'y'.
    # Otherwise, join all arguments with a space.
    if len(sys.argv) > 1:
        output_string = " ".join(sys.argv[1:])
    else:
        output_string = "y"

    # Append a newline for printing.
    output_string += "\n"

    try:
        # Run an infinite loop, repeatedly writing the string.
        while True:
            sys.stdout.write(output_string)
    except KeyboardInterrupt:
        # This handles when the user presses Ctrl+C. We exit cleanly.
        sys.exit(0)
    except BrokenPipeError:
        # This handles cases where `yes` is piped to another command
        # that exits early (e.g., `yes | head`). We silence the error
        # that would normally occur and exit cleanly.
        # os.devnull redirects stderr to prevent a final error message.
        sys.stderr.close()


if __name__ == "__main__":
    main()
