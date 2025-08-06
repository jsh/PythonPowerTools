#!/usr/bin/env python3
"""
Name: expand
Description: convert tabs to spaces
Author: Thierry Bezecourt, thbzcrt@worldnet.fr (Original Perl Author)
License: perl
"""

import sys
import os
import re
import fileinput

def expand_line(line: str, tab_width: int, tab_stops: list):
    """
    Processes a single line, converting tabs to spaces.
    """
    cursor = 0
    
    # Process the line character by character to correctly track the cursor position.
    for char in line:
        if char == '\t':
            if tab_stops:
                # --- Custom Tab Stop List Mode ---
                # Find the next tab stop that is greater than the current cursor position.
                # The `next()` function with a generator is an efficient way to do this.
                try:
                    next_stop = next(s for s in tab_stops if s > cursor + 1)
                    spaces_to_add = next_stop - (cursor + 1)
                except StopIteration:
                    # If the cursor is past the last defined tab stop, the original
                    # script's behavior is to fall back to a repeating width
                    # based on the *first* tab stop value in the list.
                    fallback_width = tab_stops[0]
                    spaces_to_add = fallback_width - (cursor % fallback_width)
            else:
                # --- Single Tab Width Mode ---
                # Calculate spaces needed to reach the next tab stop.
                spaces_to_add = tab_width - (cursor % tab_width)
            
            print(' ' * spaces_to_add, end='')
            cursor += spaces_to_add
        
        elif char == '\b':
            # Handle backspace: print it and move the cursor back.
            print('\b', end='')
            cursor = max(0, cursor - 1)
            
        elif char == '\n':
            # Print the newline but don't advance the cursor on the line.
            print('\n', end='')
            cursor = 0
            
        else:
            # Print any other character and advance the cursor.
            print(char, end='')
            cursor += 1

def main():
    """Parses arguments and orchestrates the file processing."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    
    # --- 1. Manual Argument Parsing ---
    # This is required to handle the non-standard -NUM and -N1,N2 syntax.
    tab_width = 8
    tab_stops = []
    
    if args and args[0].startswith('-'):
        opt = args.pop(0)
        if opt == '--':
            pass # End of options
        else:
            # Strip the leading '-'
            val = opt[1:]
            try:
                # Try to parse as a comma-separated list of numbers.
                stops = [int(n) for n in val.split(',')]
                if len(stops) == 1:
                    tab_width = stops[0]
                else:
                    # Sort the stops and ensure they are positive and unique.
                    tab_stops = sorted(list(set(s for s in stops if s > 0)))
                    if not tab_stops:
                        raise ValueError("Tab stops must be positive integers.")
            except ValueError:
                print(f"usage: {program_name} [-tabstop] [-tab1,tab2,...] [file ...]", file=sys.stderr)
                sys.exit(1)

    # --- 2. Process Files or Stdin ---
    files_to_process = args
    try:
        # fileinput handles reading from stdin or a list of files seamlessly.
        with fileinput.input(files=files_to_process or ('-',)) as f:
            for line in f:
                expand_line(line, tab_width, tab_stops)
    except FileNotFoundError as e:
        print(f"{program_name}: couldn't open '{e.filename}' for reading: {e.strerror}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
