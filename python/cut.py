#!/usr/bin/env python3
"""
Name: cut
Description: select portions of each line of a file
Author: Rich Lafferty, rich@alcor.concordia.ca (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import fileinput

def parse_list(list_str: str) -> tuple:
    """
    Parses a cut-style list string (e.g., "1,5-7,10-") into a sorted
    list of indices and a flag for ranges that go to the end of the line.
    
    Returns a tuple: (sorted_indices, from_end_index).
    from_end_index is None if no 'N-' range is used.
    """
    indices = set()
    from_end_index = None

    for part in list_str.split(','):
        if not part: continue # Skip empty parts from trailing commas etc.

        # Case 1: A range like 'N-M', 'N-', or '-M'
        match = re.match(r'^(\d*)-(\d*)$', part)
        if match:
            start_str, end_str = match.groups()
            
            if not start_str and not end_str: # A lone '-' is invalid
                raise ValueError("invalid range with no endpoint")
            
            start = int(start_str) if start_str else 1
            if start == 0: raise ValueError("fields are numbered from 1")
                
            if end_str: # N-M or -M
                end = int(end_str)
                if end == 0: raise ValueError("fields are numbered from 1")
                if start > end: raise ValueError(f"invalid decreasing range '{part}'")
                indices.update(range(start, end + 1))
            else: # N-
                if from_end_index is None or start < from_end_index:
                    from_end_index = start
        
        # Case 2: A single number 'N'
        elif part.isdigit():
            num = int(part)
            if num == 0: raise ValueError("fields are numbered from 1")
            indices.add(num)
        
        else:
            raise ValueError(f"invalid byte/field list '{part}'")
            
    return sorted(list(indices)), from_end_index

def handle_bytes(stream, indices, from_end_index):
    """Processes the stream in byte/character mode."""
    for line in stream:
        line = line.rstrip('\n')
        line_len = len(line)
        output = []
        
        # Add individually specified characters
        for i in indices:
            if i <= line_len:
                output.append(line[i-1]) # Convert 1-based index to 0-based
        
        # Add the 'N-' range if it exists
        if from_end_index and from_end_index <= line_len:
            output.append(line[from_end_index-1:])
            
        print("".join(output))

def handle_fields(stream, indices, from_end_index, delimiter, suppress_no_delim):
    """Processes the stream in field mode."""
    for line in stream:
        line = line.rstrip('\n')
        
        if delimiter not in line:
            if not suppress_no_delim:
                print(line)
            continue
            
        fields = line.split(delimiter)
        num_fields = len(fields)
        out_fields = []
        
        # Add individually specified fields
        for i in indices:
            if i <= num_fields:
                out_fields.append(fields[i-1])
        
        # Add the 'N-' range if it exists
        if from_end_index and from_end_index <= num_fields:
            out_fields.extend(fields[from_end_index-1:])

        print(delimiter.join(out_fields))

def main():
    """Parses arguments and dispatches to the correct handler."""
    parser = argparse.ArgumentParser(
        description="Select portions of each line of a file.",
        usage="%(prog)s [-b list | -c list | -f list] [-d delim] [-s] [file ...]"
    )
    # The main modes are mutually exclusive.
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('-b', dest='byte_list', help='The list specifies byte positions.')
    mode_group.add_argument('-c', dest='char_list', help='The list specifies character positions.')
    mode_group.add_argument('-f', dest='field_list', help='The list specifies fields.')
    
    # Options that modify field mode.
    parser.add_argument('-d', '--delimiter', default='\t',
                        help="Use DELIM instead of TAB for field delimiter.")
    parser.add_argument('-s', '--only-delimited', action='store_true',
                        help='Suppress lines with no delimiter characters.')
    
    parser.add_argument('files', nargs='*', help='Files to process. Reads from stdin if none are given.')
    
    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    try:
        if args.byte_list or args.char_list:
            list_str = args.byte_list or args.char_list
            indices, from_end = parse_list(list_str)
            handle_bytes(fileinput.input(files=args.files or ('-',)), indices, from_end)
        
        elif args.field_list:
            indices, from_end = parse_list(args.field_list)
            delimiter = args.delimiter[0] # Only the first character is used
            handle_fields(fileinput.input(files=args.files or ('-',)), indices, from_end, delimiter, args.only_delimited)
    
    except ValueError as e:
        print(f"{program_name}: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"{program_name}: '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
