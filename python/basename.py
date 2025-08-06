#!/usr/bin/env python3
"""
Name: basename
Description: print the basename of a file
Author: Abigail, Michael Mikonos (Original Perl Authors)
License: perl

A Python port of the 'basename' utility.

Prints the file component of a path. A second argument to
basename is interpreted as a suffix to remove from the file.
This implementation is compliant with POSIX standards.
"""
import os
import sys
import argparse

__version__ = "1.5"

def get_basename(path, suffix=None):
    """
    Implements the POSIX basename logic.

    1.  Strips the directory part from the path.
    2.  If a suffix is provided and it matches the end of the
        resulting string, it is removed.
    """
    # os.path.basename correctly handles stripping the directory and is
    # aware of the OS-specific path separator (e.g., '/' or '\').
    # It also correctly handles trailing slashes as per POSIX rules.
    base = os.path.basename(path)

    # If a suffix was provided, attempt to remove it.
    if suffix and base.endswith(suffix):
        # The POSIX standard specifies that the suffix should not be
        # removed if it constitutes the entire string.
        if len(base) > len(suffix):
            # Use string slicing to remove the suffix from the end.
            base = base[:-len(suffix)]

    return base

def main():
    """Parses command-line arguments and runs the basename logic."""
    parser = argparse.ArgumentParser(
        description="Print the filename component of a path, with an optional suffix removed.",
        usage="%(prog)s string [suffix]"
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        'string',
        help='The path string (e.g., /usr/bin/local).'
    )
    parser.add_argument(
        'suffix',
        nargs='?', # Makes the suffix argument optional.
        default=None,
        help='An optional suffix to remove
