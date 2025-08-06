#!/usr/bin/env python3
"""
Name: uniq
Description: report or filter out repeated lines in a file
Author: Jonathan Feinberg, jdf@pobox.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import itertools
import re

def get_comparison_key(line: str, skip_fields: int, skip_chars: int) -> str:
    """
    Extracts the part of the line to be used for comparison,
    respecting the -f (fields) and -s (chars) options.
    """
    # 1. Skip fields: Split the line at most `skip_fields` times.
    parts = line.split(None, skip_fields)
    
    # The part to compare is the last element after splitting.
    if len(parts) > skip_fields:
        remainder = parts[-1]
    else:
        return '' # Line has fewer fields than the number to skip

    # 2. Skip characters from the remainder.
    if len(remainder) > skip_chars:
        return remainder[skip_chars:]
    
    return '' # Remainder has fewer chars than the number to skip

def main():
    """Parses arguments and runs the uniq logic."""
    # We use argparse for its robust error handling and help messages,
    # but we pre-process argv to handle the non-standard +/- NUMBER options.
    
    # --- 1. Pre-process argv for historic options ---
    raw_args = sys.argv[1:]
    processed_args = []
    i = 0
    while i < len(raw_args):
        arg = raw_args[i]
        # Translate -NUMBER to -f NUMBER
        if re.match(r'^-(\d+)$', arg):
            processed_args.extend(['-f', arg[1:]])
        # Translate +NUMBER to -s NUMBER
        elif re.match(r'^\+(\d+)$', arg):
            processed_args.extend(['-s', arg[1:]])
        else:
            processed_args.append(arg)
        i += 1

    # --- 2. Standard Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Report or filter out repeated adjacent lines in a file.",
        usage="%(prog)s [-c | -d | -u] [-f fields] [-s chars] [input_file [output_file]]"
    )
    # Mode flags are mutually exclusive
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-c', '--count', action='store_true', help='Precede each line with its repetition count.')
    mode_group.add_argument('-d', '--repeated', action='store_true', help='Only print duplicate lines, one for each group.')
    mode_group.add_argument('-u', '--unique', action='store_true', help='Only print lines that are not repeated.')
    
    parser.add_argument('-f', '--skip-fields', type=int, default=0, help='Avoid comparing the first N fields.')
    parser.add_argument('-s', '--skip-chars', type=int, default=0, help='Avoid comparing the first N characters.')
    
    parser.add_argument('input_file', nargs='?', default='-', help="Input file (default: stdin).")
    parser.add_argument('output_file', nargs='?', help="Output file (default: stdout).")

    args = parser.parse_args(processed_args)
    program_name = os.path.basename(sys.argv[0])

    # --- 3. Setup I/O Streams ---
    try:
        input_stream = open(args.input_file, 'r') if args.input_file != '-' else sys.stdin
        output_stream = open(args.output_file, 'w') if args.output_file else sys.stdout

        with input_stream, output_stream:
            # --- 4. Core Logic using itertools.groupby ---
            # Define a key function that will be used to group lines.
            key_func = lambda line: get_comparison_key(line, args.skip_fields, args.skip_chars)
            
            # itertools.groupby is the perfect tool for processing consecutive identical items.
            for _, group in itertools.groupby(input_stream, key=key_func):
                # We need to realize the group iterator to get its contents and count.
                group_lines = list(group)
                count = len(group_lines)
                first_line = group_lines[0]
                
                # Apply the selected output mode.
                if args.count:
                    output_stream.write(f"{count:7d} {first_line}")
                elif args.repeated:
                    if count > 1:
                        output_stream.write(first_line)
                elif args.unique:
                    if count == 1:
                        output_stream.write(first_line)
                else: # Default mode
                    output_stream.write(first_line)

    except FileNotFoundError as e:
        print(f"{program_name}: failed to open '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"{program_name}: I/O error: {e.strerror}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
