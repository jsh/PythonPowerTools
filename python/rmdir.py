#!/usr/bin/env python3
"""
Name: rmdir
Description: remove directories
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl

A Python port of the 'rmdir' utility.

Removes empty directories. With the -p option, it also removes parent
directories as they become empty.
"""

import os
import sys
import argparse

# This global variable will track the overall exit status.
# It starts at 0 (success) and is set to 1 on the first failure.
exit_status = 0

def remove_directory(path: str, program_name: str) -> bool:
    """
    Attempts to remove a single empty directory.

    Args:
        path: The path to the directory to remove.
        program_name: The name of the script for error messages.

    Returns:
        True if the directory was successfully removed, False otherwise.
    """
    global exit_status
    try:
        # os.rmdir() is Python's direct equivalent to Perl's rmdir function.
        # It will raise an OSError if the directory is not empty or on other errors.
        os.rmdir(path)
        return True
    except OSError as e:
        # The exception object contains the error details.
        # e.strerror is the message (e.g., "Directory not empty")
        print(f"{program_name}: failed to remove '{path}': {e.strerror}", file=sys.stderr)
