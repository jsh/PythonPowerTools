#!/usr/bin/env python3
"""
Name: sleep
Description: suspend execution for a number of seconds
Author: Randy Yarger, randy.yarger@nextel.com (Original Perl Author)
License: perl

A Python port of the 'sleep' utility.

Suspends execution for a specified number of whole seconds.
"""
import os
import sys
import time

# Define constants for exit codes for clarity
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

__version__ = "1.203"

def usage(program_name):
    """Prints a usage message to stderr and exits with failure."""
    print(f"usage: {program_name} SECONDS", file=sys.stderr)
    sys.exit(EXIT_FAILURE)

def main():
    """Validates arguments and sleeps for the specified duration."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]

    # --- Argument Validation ---

    # 1. Check for the correct number of arguments (exactly one).
    if len(args) == 0:
        print(f"{program_name}: missing operand", file=sys.stderr)
        usage(program_name)

    if len(args) > 1:
        print(f"{program_name}: extra operand '{args[1]}'", file=sys.stderr)
        usage(program_name)

    seconds_str = args[0]

    # 2. Validate that the argument is a non-negative integer string.
    # The original script does not allow options or floating-point numbers.
    if not seconds_str.isdigit():
        print(f"{program_name}: invalid time interval '{seconds_str}'", file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    # --- Sleep Operation ---
    try:
        seconds_to_sleep = int(seconds_str)
        # time.sleep() is Python's direct equivalent to Perl's sleep function.
        time.sleep(seconds_to_sleep)
    except (ValueError, InterruptedError):
        # This handles rare cases, like a signal interrupting the sleep.
        # Exiting with failure is a safe default.
        sys.exit(EXIT_FAILURE)

    # If the sleep completes without interruption, exit
