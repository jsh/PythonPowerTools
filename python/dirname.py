#!/usr/bin/env python3
"""
Name: dirname
Description: print the directory name of a path
Author: Michael Mikonos, Abigail (Original Perl Authors)
License: perl

A Python port of the 'dirname' utility.

Prints the directory component of a path. Everything starting
from the last path separator is deleted.
"""
import os
import sys
import argparse

__version__ = "1.3"

def main():
    """Parses arguments and prints the directory name of a path."""
    parser = argparse.ArgumentParser(
        description="Print the directory component of a path.",
        # A custom usage message matches the original script's simplicity.
        usage=f"{os.path.basename(sys.argv[0])} string"
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        'string',
        help='The path string from which to extract the directory name.'
    )

    # argparse will automatically handle errors if the 'string' argument
    # is missing or if extra arguments are provided.
    args = parser.parse_args()

    # The core logic: os.path.dirname is Python's direct equivalent
    # to the function used in the Perl script.
    directory_name = os.path.dirname(args.string)
    
    print(directory_name)
    sys.exit(0)

if __name__ == "__main__":
    main()
