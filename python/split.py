#!/usr/bin/env python3
"""
Name: split
Description: split a file into pieces
Author: Rich Lafferty, rich@alcor.concordia.ca (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import itertools

def parse_size(size_str: str) -> int:
    """
    Parses a size string (e.g., '10k', '2m') and returns the number of bytes/lines.
    """
    match = re.match(r'^(\d+)([km]?)$', size_str.lower())
    if not match:
        raise ValueError(f"'{size_str}' is an invalid size format")
        
    value, multiplier_char = match.groups()
    value = int(value)
    
    if multiplier_char == 'k':
        value *= 1024
    elif multiplier_char == 'm':
        value *= 1024 * 1024
        
    return value

def generate_suffixes():
    """
    A generator that yields three-letter suffixes from 'aaa' to 'zzz'.
    """
    # Create all combinations of three lowercase letters.
    chars = "abcdefghijklmnopqrstuvwxyz"
    for combo in itertools.product(chars, repeat=3):
        yield "".join(combo)

def main():
    """Parses arguments and orchestrates the file splitting process."""
    parser = argparse.ArgumentParser(
        description="Split a file into pieces.",
        usage="%(prog)s [-b byte_count[k|m] | -l line_count[k|m] | -p regexp] [file [prefix]]"
    )
    # The splitting modes are mutually exclusive.
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('-b', '--bytes', help='Split by byte count (e.g., 10k, 2m).')
    mode_group.add_argument('-l', '--lines', help='Split by line count (default: 1000).')
    mode_group.add_argument('-p', '--pattern', help='Split on lines matching a regex pattern.')
    
    parser.add_argument('file', nargs='?', default='-', help="Input file (default: stdin).")
    parser.add_argument('prefix', nargs='?', default='x', help="Output file prefix (default: 'x').")

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Open Input Stream ---
    input_stream = None
    try:
        if args.file == '-':
            input_stream = sys.stdin.buffer # Always use binary mode for stdin
        else:
            if os.path.isdir(args.file):
                print(f"{program_name}: '{args.file}' is a directory", file=sys.stderr)
                sys.exit(1)
            input_stream = open(args.file, 'rb')
    except IOError as e:
        print(f"{program_name}: Can't open '{args.file}': {e.strerror}", file=sys.stderr)
        sys.exit(1)

    # --- 2. Run the Appropriate Splitting Logic ---
    suffix_generator = generate_suffixes()
    output_file = None
    
    try:
        with input_stream:
            # --- Byte Mode (-b) ---
            if args.bytes:
                byte_count = parse_size(args.bytes)
                while True:
                    chunk = input_stream.read(byte_count)
                    if not chunk:
                        break
                    suffix = next(suffix_generator)
                    with open(args.prefix + suffix, 'wb') as f_out:
                        f_out.write(chunk)

            # --- Pattern Mode (-p) ---
            elif args.pattern:
                try:
                    regex = re.compile(args.pattern.encode('utf-8'))
                except re.error as e:
                    print(f"{program_name}: invalid regular expression: {e}", file=sys.stderr)
                    sys.exit(1)
                
                for line in input_stream:
                    # Open a new file if one isn't open or if the line matches.
                    if output_file is None or regex.search(line):
                        if output_file: output_file.close()
                        suffix = next(suffix_generator)
                        output_file = open(args.prefix + suffix, 'wb')
                    output_file.write(line)

            # --- Line Mode (-l) ---
            else:
                line_count = parse_size(args.lines) if args.lines else 1000
                line_num = 0
                for line in input_stream:
                    # Open a new file if one isn't open or we've hit the line limit.
                    if output_file is None or line_num % line_count == 0:
                        if output_file: output_file.close()
                        suffix = next(suffix_generator)
                        output_file = open(args.prefix + suffix, 'wb')
                    output_file.write(line)
                    line_num += 1

    except StopIteration:
        print(f"{program_name}: can only create 17576 files", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"{program_name}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if output_file and not output_file.closed:
            output_file.close()

    sys.exit(0)

if __name__ == "__main__":
    main()
