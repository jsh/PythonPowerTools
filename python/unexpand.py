#!/usr/bin/env python3
"""
Name: unexpand
Description: convert spaces to tabs
Author: Thierry Bezecourt, thbzcrt@worldnet.fr (Original Perl Author)
License: perl
"""

import sys
import os
import fileinput

def is_tab_stop(cursor: int, tab_width: int, tab_stops: list) -> bool:
    """
    Checks if the given cursor position is a defined tab stop.
    """
    if tab_stops:
        # Check against a specific list of stops.
        return (cursor + 1) in tab_stops
    # Check against a repeating tab width.
    return (cursor % tab_width == 0)

def unexpand_line(line: str, is_all_mode: bool, tab_width: int, tab_stops: list):
    """
    Processes a single line, converting spaces to tabs.
    """
    output_buffer = ""
    cursor = 0
    
    # Process the line character by character to correctly track the cursor position.
    for i, char in enumerate(line):
        # The decision to convert spaces to a tab is made only when the
        # cursor is at a tab stop boundary.
        if is_tab_stop(cursor, tab_width, tab_stops) and output_buffer.endswith(' '):
            # Find the start of the trailing space block in the buffer.
            j = len(output_buffer) - 1
            while j >= 0 and output_buffer[j] == ' ':
                j -= 1
            
            non_space_part = output_buffer[:j+1]
            
            # If there was at least one space, print the non-space part
            # followed by a tab, then clear the buffer.
            if j < len(output_buffer) - 1:
                print(non_space_part, end='')
                print('\t', end='')
                output_buffer = ""

        # Default mode (not -a): stop processing for tabs after the first
        # non-space character is encountered.
        if not is_all_mode and char != ' ' and cursor > 0:
            # Print the buffer, the current char, and the rest of the line, then we're done.
            print(output_buffer + line[i:], end='')
            return

        # Add the current character to the buffer and update the cursor position.
        output_buffer += char
        if char == '\b':
            cursor = max(0, cursor - 1)
        else:
            cursor += 1
            
    # Print any remaining content in the buffer at the end of the line.
    print(output_buffer, end='')


def main():
    """Parses arguments and orchestrates the file processing."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    
    # --- 1. Manual Argument Parsing ---
    is_all_mode = False
    tab_width = 8
    tab_stops = []
    
    while args and args[0].startswith('-'):
        opt = args.pop(0)
        if opt == '--':
            break # Stop option processing
        elif opt == '-a':
            is_all_mode = True
        else:
            val = opt[1:]
            try:
                stops = [int(n) for n in val.split(',')]
                if not all(s > 0 for s in stops): raise ValueError
                
                if len(stops) == 1:
                    tab_width = stops[0]
                else:
                    tab_stops = sorted(list(set(stops)))
            except ValueError:
                print(f"usage: {program_name} [-a] [-tabstop] [-tab1,tab2,...] [file ...]", file=sys.stderr)
                sys.exit(1)

    # --- 2. Process Files or Stdin ---
    files_to_process = args
    try:
        # fileinput handles reading from stdin or a list of files seamlessly.
        with fileinput.input(files=files_to_process or ('-',)) as f:
            for line in f:
                unexpand_line(line, is_all_mode, tab_width, tab_stops)
    except FileNotFoundError as e:
        print(f"{program_name}: couldn't open '{e.filename}' for reading: {e.strerror}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
