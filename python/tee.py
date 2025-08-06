#!/usr/bin/env python3
"""
Name: tee
Description: pipe fitting
Author: Tom Christiansen, tchrist@perl.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import signal

# This global variable tracks the overall exit status.
# It starts at 0 (success) and is set to a non-zero value on the first failure.
exit_status = 0

def main():
    """Parses arguments and runs the tee logic."""
    global exit_status
    
    parser = argparse.ArgumentParser(
        description="Read from standard input and write to standard output and files.",
        usage="%(prog)s [-ai] [file ...]"
    )
    parser.add_argument(
        '-a', '--append',
        action='store_true',
        help='append output to the files instead of overwriting them'
    )
    parser.add_argument(
        '-i', '--ignore-interrupts',
        action='store_true',
        help='ignore the SIGINT signal (e.g., Ctrl+C)'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='One or more files to write to, in addition to standard output.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # Handle the -i flag by ignoring the SIGINT signal.
    if args.ignore_interrupts:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    # --- Open all output files ---
    output_files = []
    # We write to stdout's binary buffer to handle all data types correctly.
    output_files.append(sys.stdout.buffer)

    # Determine the file mode based on the -a flag. 'b' is for binary mode.
    file_mode = 'ab' if args.append else 'wb'

    for filename
