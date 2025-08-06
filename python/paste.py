#!/usr/bin/env python3
"""
Name: paste
Description: merge corresponding or subsequent lines of files
Author: Randy Yarger, randy.yarger@nextel.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import itertools
import codecs

def expand_delimiters(d_str: str) -> list:
    """
    Expands a string containing backslash escapes (e.g., "\\t\\n")
    into a list of actual delimiter characters.
    """
    # 'unicode_escape' is the codec for handling Python-style string literals.
    return list(codecs.decode(d_str, 'unicode_escape'))

def serial_paste(file_handles: list, delimiters: list):
    """
    Handles the -s (serial) mode. Concatenates all lines from one file
    into a single output line, then moves to the next file.
    """
    delimiter_cycle = itertools.cycle(delimiters)
    for fh in file_handles:
        # Read all lines, stripping the trailing newline from each.
        lines = [line.rstrip('\n') for line in fh]
        
        # Interleave lines and delimiters to build the final output string.
        output_parts = []
        if lines:
            output_parts.append(lines[0])
            for line in lines[1:]:
                output_parts.append(next(delimiter_cycle))
                output_parts.append(line)
        
        print("".join(output_parts))

def parallel_paste(file_handles: list, delimiters: list):
    """
    Handles the default (parallel) mode. Merges the corresponding lines
    from all files into single output lines.
    """
    # itertools.zip_longest is perfect for this. It iterates through all
    # files in parallel. If one file is shorter than others, it fills the
    # missing columns with the specified fillvalue.
    for row in itertools.zip_longest(*file_handles, fillvalue=''):
        delimiter_cycle = itertools.cycle(delimiters)
        # Strip the newline from each column in the current row.
        cleaned_row = [col.rstrip('\n') for col in row]
        
        output_parts = []
        if cleaned_row:
            output_parts.append(cleaned_row[0])
            # Interleave the remaining columns and delimiters.
            for col in cleaned_row[1:]:
                output_parts.append(next(delimiter_cycle))
                output_parts.append(col)
        
        print("".join(output_parts))

def main():
    """Parses arguments, opens files, and orchestrates the pasting logic."""
    parser = argparse.ArgumentParser(
        description="Merge corresponding or subsequent lines of files.",
        usage="%(prog)s [-s] [-d list] file ..."
    )
    parser.add_argument(
        '-s', '--serial',
        action='store_true',
        help='paste one file at a time instead of in parallel'
    )
    parser.add_argument(
        '-d', '--delimiters',
        default='\t',
        help='reuse characters in LIST as delimiters instead of TAB'
    )
    parser.add_argument(
        'files',
        nargs='+', # Requires one or more file arguments.
        help="Files to process. Use '-' for standard input."
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    
    delimiters = expand_delimiters(args.delimiters)
    
    # --- Open all file handles ---
    file_handles = []
    try:
        for filename in args.files:
            if filename == '-':
                file_handles.append(sys.stdin)
            else:
                if os.path.isdir(filename):
                    print(f"{program_name}: '{filename}': is a directory", file=sys.stderr)
                    sys.exit(1)
                file_handles.append(open(filename, 'r'))
        
        # --- Run the appropriate mode ---
        if args.serial:
            serial_paste(file_handles, delimiters)
        else:
            parallel_paste(file_handles, delimiters)

    except FileNotFoundError as e:
        print(f"{program_name}: '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    finally:
        # --- Clean up and close all opened files ---
        for fh in file_handles:
            if fh is not sys.stdin:
                fh.close()

    sys.exit(0)

if __name__ == "__main__":
    main()
