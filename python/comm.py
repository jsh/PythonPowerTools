#!/usr/bin/env python3
"""
Name: comm
Description: select or reject lines common to two files
Author: Mark-Jason Dominus (Original Perl Author)
License: public domain
"""

import sys
import os
import argparse

def open_file_safely(filepath: str):
    """
    Opens a file for reading or returns the stdin stream.
    Performs checks for directories and handles file-not-found errors.
    """
    if filepath == '-':
        return sys.stdin
    
    if os.path.isdir(filepath):
        print(f"{sys.argv[0]}: '{filepath}' is a directory", file=sys.stderr)
        return None
    
    try:
        return open(filepath, 'r')
    except IOError as e:
        print(f"{sys.argv[0]}: Couldn't open file '{filepath}': {e.strerror}", file=sys.stderr)
        return None

def main():
    """Parses arguments and runs the line comparison logic."""
    parser = argparse.ArgumentParser(
        description="Select or reject lines common to two sorted files.",
        usage="%(prog)s [-123] file1 file2"
    )
    parser.add_argument('-1', dest='suppress1', action='store_true', help='Suppress column 1 (lines unique to file1)')
    parser.add_argument('-2', dest='suppress2', action='store_true', help='Suppress column 2 (lines unique to file2)')
    parser.add_argument('-3', dest='suppress3', action='store_true', help='Suppress column 3 (lines common to both files)')
    parser.add_argument('file1', help='First file to compare, or - for stdin.')
    parser.add_argument('file2', help='Second file to compare, or - for stdin.')
    
    args = parser.parse_args()

    # --- Setup columns and file handles ---
    
    # This creates a boolean list where show_col[i] is True if we should print that column.
    show_col = [None, not args.suppress1, not args.suppress2, not args.suppress3]

    if args.file1 == '-' and args.file2 == '-':
        parser.error("only one file argument may be stdin")

    f1 = open_file_safely(args.file1)
    if not f1: sys.exit(1)

    f2 = open_file_safely(args.file2)
    if not f2: sys.exit(1)

    # --- Core Comparison Logic ---
    
    # The 'with' statement ensures files are automatically closed.
    with f1, f2:
        line1 = f1.readline()
        line2 = f2.readline()

        # This loop continues as long as both files have lines to be read.
        while line1 and line2:
