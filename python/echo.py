#!/usr/bin/env python3
"""
Name: echo
Description: echo arguments
Author: Randy Yarger, randy.yarger@nextel.com (Original Perl Author)
License: perl

A Python port of the 'echo' utility.

Prints the command line arguments separated by spaces. A newline is
printed at the end unless the '-n' option is given as the first argument.
"""

import sys

__version__ = "1.3"

def main():
    """
    The main entry point for the script. Handles argument parsing and printing.
    """
    args = sys.argv[1:] # Get all arguments except the script name
    print_newline = True

    # Manually check if the first argument is '-n'.
    # This mimics the simple parsing of the original script.
    if args and args[0] == '-n':
        print_newline = False
        args.pop(0) # Remove the '-n' from the list of arguments to print

    # Join the remaining arguments with a single space.
    output_string = " ".join(args)

    # Use the 'end' parameter of the print() function to control the
    # trailing newline character.
    if print_newline:
        print(output_string)
    else:
        print(output_string, end='')

    sys.exit(0)

# This standard Python construct ensures that main() is called only when
# the script is executed directly (e.g., `python echo.py hello`).
# It allows the script's functions to be safely imported into other modules
# without running the main logic.
if __name__ == "__main__":
    main()
