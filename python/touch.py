#!/usr/bin/env python3
"""
Name: touch
Description: change access and modification times of files
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import time
from datetime import datetime

def parse_timestamp(time_str: str) -> float:
    """
    Parses the complex [[CC]YY]MMDDhhmm[.SS] timestamp format and returns
    it as an epoch float (seconds since 1970-01-01).
    """
    try:
        # Separate the main part from the optional seconds
        parts = time_str.split('.')
        main_part = parts[0]
        seconds = int(parts[1]) if len(parts) > 1 else 0

        # Determine year, century, month, day, etc. based on length
        now = datetime.now()
        if len(main_part) == 12: # CCYYMMDDhhmm
            cent, year = int(main_part[0:2]), int(main_part[2:4])
            year = cent * 100 + year
            main_part = main_part[4:]
        elif len(main_part) == 10: # YYMMDDhhmm
            year = int(main_part[0:2])
            # Infer century based on POSIX standard for 'touch'
            year += 2000 if year < 69 else 1900
            main_part = main_part[2:]
        elif len(main_part) == 8: # MMDDhhmm
            year = now.year
        else:
            raise ValueError("Invalid time format length")

        month, day, hour, minute = (int(main_part[i:i+2]) for i in range(0, 8, 2))
        
        dt = datetime(year, month, day, hour, minute, seconds)
        return dt.timestamp()
    except (ValueError, IndexError):
        raise ValueError(f"Illegal time format '{time_str}'")

def main():
    """Parses arguments and runs the touch logic."""
    parser = argparse.ArgumentParser(
        description="Change file access and modification times.",
        usage="%(prog)s [-acm] [-r file] [-t [[CC]YY]MMDDhhmm[.SS]] file..."
    )
    parser.add_argument('-a', action='store_true', help='Change only the access time.')
    parser.add_argument('-c', '--no-create', action='store_true', help="Don't create any files.")
    parser.add_argument('-m', action='store_true', help='Change only the modification time.')
    parser.add_argument('-f', action='store_true', help='Ignored (for compatibility).')
    
    # -r and -t are mutually exclusive
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('-r', '--reference', help='Use this file\'s times instead of the current time.')
    time_group.add_argument('-t', '--time', help='Use a specific time instead of the current time.')
    
    parser.add_argument('files', nargs='+', help='One or more files to touch.')
    
    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    exit_status = 0

    # --- 1. Determine the Target Timestamps ---
    atime, mtime = None, None
    try:
        if args.reference:
            stats = os.stat(args.reference)
            atime, mtime = stats.st_atime, stats.st_mtime
        elif args.time:
            atime = mtime = parse_timestamp(args.time)
        else:
            # Default to the current time
            atime = mtime = time.time()
    except (ValueError, OSError) as e:
        print(f"{program_name}: {e}", file=sys.stderr)
        sys.exit(1)
        
    # --- 2. Process Each File ---
    for filepath in args.files:
        try:
            # Handle file creation
            if not os.path.lexists(filepath): # lexists handles symlinks
                if args.no_create:
                    continue
                # Create an empty file
                open(filepath, 'a').close()
            
            # Get the file's current times to preserve one if needed
            current_stats = os.stat(filepath)
            
            # Determine which times to change
            final_atime = atime if (args.a or not args.m) else current_stats.st_atime
            final_mtime = mtime if (args.m or not args.a) else current_stats.st_mtime
            
            # os.utime sets the new access and modification times.
            os.utime(filepath, (final_atime, final_mtime))

        except OSError as e:
            print(f"{program_name}: {filepath}: {e.strerror}", file=sys.stderr)
            exit_status = 1
            continue

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
