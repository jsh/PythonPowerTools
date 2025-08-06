#!/usr/bin/env python3
"""
Name: rev
Description: reverse lines of a file
Author: Andy Murren, andy@murren.org (Original Perl Author)
License: gpl
"""

import sys
import os
import argparse
import fileinput

# This global variable tracks the overall exit status.
# It starts at 0 (success) and is set to 1 on the first failure.
exit_status = 0

def main():
    """Parses arguments and runs the line-reversing logic."""
    global exit_status
    
    parser = argparse.ArgumentParser(
        description="Reverse the order of characters in every line of a file.",
        usage="%(prog)s [file ...]"
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.5'
    )
    parser.add_argument(
        'files',
        nargs='*', # Zero or more file arguments.
        help='One or more files to process. Reads from stdin if none are given.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # The fileinput module provides a convenient way to iterate over lines
    # from multiple input streams (stdin or files).
    try:
        # The 'with' statement ensures the fileinput object is closed properly.
        # fileinput.input() with no files defaults to sys.stdin.
        with fileinput.input(files=args.files or ('-',)) as f:
            for line in f:
                # Before processing the first line of a new file, check if it's a directory.
                if f.isfirstline() and fileinput.filename() != '<stdin>':
                    if os.path.isdir(fileinput.filename()):
                        print(f"{program_name}: '{fileinput.filename()}' is a directory", file=sys.stderr)
                        exit_status = 1
                        f.nextfile() # Skip to the next file in the list
                        continue
                
                # The core logic:
                # 1. line.rstrip('\n') removes the trailing newline.
                # 2. [::-1] is Python's slice notation for reversing a string.
                # 3. print() adds the newline back by default.
                # 4. flush=True ensures unbuffered output, like the original script.
                print(line.rstrip('\n')[::-1], flush=True)

    except FileNotFoundError as e:
        print(f"{program_name}: cannot open '{e.filename}': {e.strerror}", file=sys.stderr)
        exit_status = 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        exit_status = 1
        
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
