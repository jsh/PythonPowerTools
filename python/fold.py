#!/usr/bin/env python3
"""
Name: fold
Description: wrap each input line to fit specified width
Author: Clinton Pierce, Tom Christiansen (Original Perl Authors)
License: perl
"""

import sys
import os
import argparse
import re
import textwrap
import fileinput

def preprocess_argv(args_list: list) -> list:
    """
    Translates the historical '-WIDTH' syntax to the standard '-w WIDTH'.
    For example, '-72' becomes ['-w', '72'].
    """

    processed_args = []
    for arg in args_list:
        match = re.match(r'^-(\d+)$', arg)
        if match:
            # Replace with standard -w syntax
            processed_args.extend(['-w', match.group(1)])
        else:
            processed_args.append(arg)
    return processed_args

def expand_tabs_and_backspaces(line: str, tab_width: int = 8) -> str:
    """
    Pre-processes a line to handle special characters before wrapping.
    - Expands tabs to spaces based on column position.
    - Processes backspaces to remove the preceding character.
    """
    expanded = []
    col = 0
    for char in line:
        if char == '\t':
            spaces_to_add = tab_width - (col % tab_width)
            expanded.append(' ' * spaces_to_add)
            col += spaces_to_add
        elif char == '\b':
            if expanded:
                expanded.pop()
                col -= 1
        # In this context, carriage return resets the line.
        elif char == '\r':
            expanded = []
            col = 0
        else:
            expanded.append(char)
            col += 1
    return "".join(expanded)

def main():
    """Parses arguments and runs the line-folding logic."""
    # Pre-process arguments to handle the '-WIDTH' syntax.
    args_to_parse = preprocess_argv(sys.argv[1:])

    parser = argparse.ArgumentParser(
        description="Wrap each input line to fit a specified width.",
        usage="%(prog)s [-bs] [-w width] [file ...]"
    )
    parser.add_argument(
        '-b', '--bytes',
        action='store_true',
        help='Count bytes rather than columns (ignores tabs, backspaces, etc.).'
    )
    parser.add_argument(
        '-s', '--spaces',
        action='store_true',
        help='Break lines at spaces.'
    )
    parser.add_argument(
        '-w', '--width',
        type=int,
        default=80,
        help='Use a maximum line width of WIDTH (default: 80).'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to process. Reads from stdin if none are given.'
    )
    
    try:
        args = parser.parse_args(args_to_parse)
    except SystemExit:
        sys.exit(1)

    if args.width <= 0:
        print(f"{os.path.basename(sys.argv[0])}: illegal width value '{args.width}'", file=sys.stderr)
        sys.exit(1)
        
    # --- Configure the TextWrapper ---
    # The textwrap module does all the heavy lifting of wrapping text.
    wrapper = textwrap.TextWrapper(
        width=args.width,
        # -s: break on spaces (default for textwrap)
        # not -s: break anywhere, even mid-word
        break_long_words=not args.spaces,
        break_on_hyphens=args.spaces,
        # The -b flag in Perl was a fast path that ignored tabs and backspaces.
        # textwrap does this by default, so we only expand tabs if -b is NOT set.
        expand_tabs=args.bytes,
        replace_whitespace=False,
    )

    # --- Process Input ---
    exit_status = 0
    try:
        # fileinput handles reading from stdin or a list of files seamlessly.
        with fileinput.input(files=args.files or ('-',)) as f:
            for line in f:
                # The original line's trailing newline is handled by print().
                line_to_wrap = line.rstrip('\n')
                
                # If not in simple byte mode, we must manually process tabs/backspaces
                # because textwrap's tab expansion is simpler than what's required.
                if not args.bytes:
                    line_to_wrap = expand_tabs_and_backspaces(line_to_wrap)
                
                # The fill() method wraps the text and returns a single formatted string.
                print(wrapper.fill(line_to_wrap))

    except FileNotFoundError as e:
        print(f"{sys.argv[0]}: failed to open '{e.filename}': {e.strerror}", file=sys.stderr)
        exit_status = 1
    except IsADirectoryError:
        # fileinput raises this if an argument is a directory
        print(f"{sys.argv[0]}: '{fileinput.filename()}': is a directory", file=sys.stderr)
        exit_status = 1

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
