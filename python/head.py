#!/usr/bin/env python3
"""
Name: head
Description: print the first lines of a file
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import fileinput
import itertools
import re

def preprocess_argv(args_list: list) -> list:
    """
    Translates the historical '-NUMBER' syntax to the standard '-n NUMBER'.
    For example, '-20' becomes ['-n', '20'].
    """
    processed_args = []
    for arg in args_list:
        # Match arguments like '-20' but not '-' or '--' or '-n'
        match = re.match(r'^-(\d+)$', arg)
        if match:
            # Replace with standard -n syntax
            processed_args.extend(['-n', match.group(1)])
        else:
            processed_args.append(arg)
    return processed_args

def main():
    """Parses arguments and prints the first N lines of files or stdin."""
    program_name = os.path.basename(sys.argv[0])
    exit_status = 0
    
    # Pre-process arguments to handle the '-NUMBER' syntax before parsing.
    args_to_parse = preprocess_argv(sys.argv[1:])

    parser = argparse.ArgumentParser(
        description="Print the first lines of a file.",
        usage="%(prog)s [-n count] [file ...]"
    )
    parser.add_argument(
        '-n', '--lines',
        dest='count',
        type=int,
        default=10,
        help='The number of lines to print (default: 10).'
    )
    parser.add_argument(
        'files',
        nargs='*', # Zero or more file arguments.
        help='Files to process. Reads from stdin if none are given.'
    )

    try:
        args = parser.parse_args(args_to_parse)
    except SystemExit:
        # argparse exits on error, so we just re-exit with the failure code.
        sys.exit(1)

    # --- Validate arguments ---
    if args.count <= 0:
        print(f"{program_name}: count is too small", file=sys.stderr)
        sys.exit(1)

    # --- Process Files or Stdin ---
    is_multi_file = len(args.files) > 1
    needs_separator = False
    
    try:
        # fileinput handles reading from stdin or a list of files seamlessly.
        with fileinput.input(files=args.files or ('-',)) as f:
            for line in f:
                # On the first line of each new file, print a header if needed.
                if f.isfirstline():
                    if is_multi_file:
                        if needs_separator: print()
                        print(f"==> {f.filename()} <==")
                        needs_separator = True
                    
                    # Check for directories, which should be skipped.
                    if f.filename() != '<stdin>' and os.path.isdir(f.filename()):
                        print(f"{program_name}: '{f.filename()}' is a directory", file=sys.stderr)
                        exit_status = 1
                        f.nextfile() # Skip to the next file
                        continue
                
                # Only print lines up to the specified count for the current file.
                if f.filelineno() <= args.count:
                    print(line, end='')
                else:
                    # Once the count is reached, skip to the next file.
                    f.nextfile()

    except FileNotFoundError as e:
        print(f"{program_name}: failed to open '{e.filename}': {e.strerror}", file=sys.stderr)
        exit_status = 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        exit_status = 1

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
