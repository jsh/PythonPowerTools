#!/usr/bin/env python3
"""
Name: colrm
Description: remove columns from a file
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl
"""

import sys
import os

def get_validated_arg(arg_str: str, program_name: str) -> int:
    """
    Validates that an argument is a positive integer string.
    Prints an error and exits if validation fails.
    """
    if not arg_str.isdigit() or int(arg_str) == 0:
        print(f"{program_name}: invalid column number '{arg_str}'", file=sys.stderr)
        sys.exit(1)
    return int(arg_str)

def main():
    """Parses arguments and runs the column-removal logic."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    num_args = len(args)

    # --- Case 1: More than 2 arguments ---
    if num_args > 2:
        print(f"usage: {program_name} [startcol [endcol]]", file=sys.stderr)
        sys.exit(1)

    # --- Case 2: No arguments ---
    # Acts like `cat`, printing input directly to output.
    if num_args == 0:
        for line in sys.stdin:
            print(line, end='')
        sys.exit(0)

    # --- Case 3: One argument (startcol) ---
    # Removes from startcol to the end of the line.
    if num_args == 1:
        start_col = get_validated_arg(args[0], program_name)
        for line in sys.stdin:
            # rstrip() is like Perl's chomp
            line = line.rstrip('\n')
            if start_col > len(line):
                print(line)
            else:
                # Python slices are 0-indexed, so we subtract 1.
                print(line[:start_col - 1])
        sys.exit(0)

    # --- Case 4: Two arguments (startcol, endcol) ---
    # Removes from startcol to endcol, inclusive.
    if num_args == 2:
        start_col = get_validated_arg(args[0], program_name)
        end_col = get_validated_arg(args[1], program_name)

        if start_col > end_col:
            print(f"{program_name}: bad range: {start_col},{end_col}", file=sys.stderr)
            sys.exit(1)
        
        for line in sys.stdin:
            line = line.rstrip('\n')
            line_len = len(line)

            if start_col > line_len:
                print(line)
            else:
                # Get the part before start_col
                part1 = line[:start_col - 1]
                # Get the part after end_col
                part2 = line[end_col:] if end_col < line_len else ''
                print(part1 + part2)
        sys.exit(0)

if __name__ == "__main__":
    main()
