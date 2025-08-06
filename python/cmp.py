#!/usr/bin/env python3
"""
Name: cmp
Description: compare two files
Author: D Roland Walker, walker@pobox.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import math

# --- Exit Codes ---
EX_SUCCESS = 0   # Files are identical
EX_DIFFERENT = 1 # Files are different
EX_FAILURE = 2   # Usage error or file system error

def parse_skip_offset(offset_str: str) -> int:
    """Parses an offset string that can be decimal, octal, or hex."""
    if not offset_str:
        return 0
    try:
        # int(str, 0) automatically detects 0x, 0o, 0b prefixes.
        # We handle the '0' octal prefix manually for compatibility.
        if offset_str.startswith('0') and not offset_str.startswith(('0x', '0X')):
            return int(offset_str, 8)
        return int(offset_str, 0)
    except ValueError:
        raise ValueError(f"invalid offset number '{offset_str}'")

def main():
    """Parses arguments and runs the file comparison logic."""
    parser = argparse.ArgumentParser(
        description="Compare two files byte by byte.",
        usage="%(prog)s [-l | -s] file1 file2 [skip1 [skip2]]"
    )
    # The -l and -s modes are mutually exclusive.
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '-l', '--verbose', action='store_true',
        help='Output the byte number and differing byte values for all differences.'
    )
    mode_group.add_argument(
        '-s', '--quiet', '--silent', action='store_true',
        help='Suppress all output; only return an exit code.'
    )
    
    parser.add_argument('file1', help="First file to compare, or '-' for stdin.")
    parser.add_argument('file2', help="Second file to compare, or '-' for stdin.")
    parser.add_argument('skip1', nargs='?', default='0', help="Bytes to skip in file1.")
    parser.add_argument('skip2', nargs='?', default='0', help="Bytes to skip in file2.")

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Argument and File Validation ---
    try:
        skip1 = parse_skip_offset(args.skip1)
        skip2 = parse_skip_offset(args.skip2)
    except ValueError as e:
        print(f"{program_name}: {e}", file=sys.stderr)
        sys.exit(EX_FAILURE)
        
    if args.file1 == '-' and args.file2 == '-':
        print(f"{program_name}: standard input is allowed for one argument only", file=sys.stderr)
        sys.exit(EX_FAILURE)

    # --- 2. Open Input Streams ---
    f1, f2 = None, None
    try:
        if args.file1 == '-':
            f1 = sys.stdin.buffer
        else:
            if os.path.isdir(args.file1):
                print(f"{program_name}: '{args.file1}' is a directory", file=sys.stderr)
                sys.exit(EX_FAILURE)
            # Quick check for identical files via inode
            if args.file2 != '-' and os.path.samefile(args.file1, args.file2):
                sys.exit(EX_SUCCESS)
            f1 = open(args.file1, 'rb')

        if args.file2 == '-':
            f2 = sys.stdin.buffer
        else:
            if os.path.isdir(args.file2):
                print(f"{program_name}: '{args.file2}' is a directory", file=sys.stderr)
                sys.exit(EX_FAILURE)
            f2 = open(args.file2, 'rb')

        with f1, f2:
            # --- 3. Handle Skip Offsets ---
            # For non-seekable streams (like stdin), we must read to skip.
            if skip1 > 0: f1.seek(skip1) if f1.seekable() else f1.read(skip1)
            if skip2 > 0: f2.seek(skip2) if f2.seekable() else f2.read(skip2)

            # --- 4. Main Comparison Loop ---
            byte_num = 1
            line_num = 1
            has_difference = False
            
            while True:
                chunk1 = f1.read(8192)
                chunk2 = f2.read(8192)

                if chunk1 == chunk2:
                    if not chunk1: # Both are empty, files are identical
                        sys.exit(EX_SUCCESS if not has_difference else EX_DIFFERENT)
                    
                    # Update counters and continue
                    if not args.quiet:
                        line_num += chunk1.count(b'\n')
                        byte_num += len(chunk1)
                    continue

                # --- Files Differ ---
                has_difference = True

                if args.quiet:
                    sys.exit(EX_DIFFERENT)
                    
                # Find all differences within the unequal chunks
                len1, len2 = len(chunk1), len(chunk2)
                min_len = min(len1, len2)
                
                for i in range(min_len):
                    if chunk1[i] != chunk2[i]:
                        current_byte = byte_num + i
                        # Count newlines up to this point in the chunk
                        current_line = line_num + chunk1[:i].count(b'\n')
                        
                        if args.verbose: # -l mode
                            print(f"{current_byte} {chunk1[i]:>3o} {chunk2[i]:>3o}")
                        else: # Default mode
                            print(f"{args.file1} {args.file2} differ: char {current_byte}, line {current_line}")
                            sys.exit(EX_DIFFERENT)

                # After the loop, check if one file is a prefix of the other
                if len1 != len2:
                    eof_file = args.file1 if len1 < len2 else args.file2
                    current_byte = byte_num + min_len
                    current_line = line_num + chunk1[:min_len].count(b'\n')
                    if not args.verbose:
                         print(f"{program_name}: EOF on {eof_file} after byte {current_byte}, in line {current_line}", file=sys.stderr)
                    sys.exit(EX_DIFFERENT)
                
                # Update counters for the next chunk in -l mode
                line_num += chunk1.count(b'\n')
                byte_num += len1

    except FileNotFoundError as e:
        print(f"{program_name}: '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(EX_FAILURE)
    except IOError as e:
        print(f"{program_name}: I/O error: {e.strerror}", file=sys.stderr)
        sys.exit(EX_FAILURE)

if __name__ == "__main__":
    main()
