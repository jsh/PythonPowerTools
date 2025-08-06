#!/usr/bin/env python3
"""
Name: time
Description: times the execution of a command
Author: dkulp (Original Perl Author)
License: perl

A Python port of the 'time' utility.

Times the execution of a given command and reports the real (wall-clock)
time, as well as the user and system CPU time consumed by the command
and its children.
"""

import os
import sys
import time
import subprocess

def main():
    """Parses arguments, runs and times the command, and reports results."""
    # The command to run consists of all arguments after the script name.
    command_to_run = sys.argv[1:]

    # If no command is given, print a usage message and exit.
    if not command_to_run:
        script_name = os.path.basename(sys.argv[0])
        print(f"Usage: {script_name} command [argument ...]", file=sys.stderr)
        sys.exit(1)

    # --- Start Timers ---
    # `os.times()` gets cumulative CPU times for the current process AND its children.
    # By measuring the change across the subprocess call, we isolate the time
    # consumed by that specific subprocess.
    cpu_time_start = os.times()
    # `time.monotonic()` is a wall-clock timer unaffected by system time changes.
    real_time_start = time.monotonic()

    # --- Execute the Command ---
    # We wrap this in a `try...except` block to gracefully handle cases where
    # the command doesn't exist or fails to execute.
    try:
        # `subprocess.run()` executes the command.
        proc = subprocess.run(command_to_run)
        # Store the return code of the child process.
        exit_code = proc.returncode
    except FileNotFoundError:
        # This error is raised if the command is not found in the system's PATH.
        print(f"{command_to_run[0]}: command not found", file=sys.stderr)
        sys.exit(127) # 127 is the standard exit code for "command not found".
    except Exception as e:
        # Catch other potential execution errors.
        print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1) # Generic failure code

    # --- Stop Timers ---
    real_time_end = time.monotonic()
    cpu_time_end = os.times()

    # --- Calculate and Report Times ---
    # The difference in the cumulative CPU times gives us the
