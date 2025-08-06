#!/usr/bin/env python3
"""
Name: shar
Description: create a shell archive of files
Author: Rich Salz (Original Perl Author)
License: public domain
"""

import sys
import os
import binascii
import argparse
import shlex

# This global variable tracks the overall exit status.
# It starts at 0 (success) and is set to 1 on the first failure.
exit_status = 0

def is_binary_file(filepath: str, block_size=1024) -> bool:
    """
    Heuristically determines if a file is binary by checking for null bytes
    in the first block of the file. This is a common and effective method.
    """
    try:
        with open(filepath, 'rb') as f:
            block = f.read(block_size)
        return b'\x00' in block
    except IOError:
        return False # Assume not binary if we can't read it

def main():
    """Parses arguments and generates the shell archive."""
    global exit_status
    
    parser = argparse.ArgumentParser(
        description="Create a shell archive of files.",
        usage="%(prog)s file..."
    )
    parser.add_argument(
        'files',
        nargs='+', # Requires one or more file arguments.
        help='One or more files or directories to archive.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- Print the shar header ---
    print("""# --cut here--
# To extract, remove everything before the "cut here" line
# and run the command "sh file".
""")

    files_processed = 0
    for fpath in args.files:
        if not fpath:
            print(f"{program_name}: empty file name", file=sys.stderr)
            exit_status = 1
            continue

        # shlex.quote is the standard, safe way to quote filenames for the shell.
        quoted_path = shlex.quote(fpath)

        # --- Handle Directories ---
        if
