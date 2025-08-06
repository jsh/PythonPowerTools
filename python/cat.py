#!/usr/bin/env python3
"""
Name: cat
Description: concatenate and print files
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import fileinput

def format_line_for_printing(line: str, opts: argparse.Namespace) -> str:
    """
    Applies the various formatting options (-e, -t, -v) to a single line.
    """
    # -e implies -v, -t implies -v
    show_non_printing = opts.v or opts.e or opts.t
    
    if opts.e:
        # Strip original newline and add '$' before it.
        line = line.rstrip('\n') + '$\n'

    if not show_non_printing:
        return line
        
    result = []
    for char in line:
        val = ord(char)
        # Pass through standard printable ASCII and newlines
        if ' ' <= char <= '~' or char == '\n':
            if char == '\t' and opts.t:
                result.append('^I')
            else:
                result.append(char)
        # High-bit (meta) characters
        elif val >= 128:
            # Re-enable the non-printing check on the lower 7 bits
            char_low = chr(val & 0x7f)
            result.append('M-')
            # This recursive-like call is needed for M-^? etc.
            result.append(format_line_for_printing(char_low, opts))
        # DEL character
        elif val == 127:
            result.append('^?')
        # Tab (if -t is not set, but -v is)
        elif char == '\t':
            result.append(char)
        # Other control characters
        else:
            result.append(f'^{chr(val + 64)}')

    return "".join(result)

def main():
    """Parses arguments and runs the cat logic."""
    parser = argparse.ArgumentParser(
        description="Concatenate and print files.",
        usage="%(prog)s [-benstuv] [file ...]"
    )
    # The flags are defined to be compatible with OpenBSD/POSIX cat.
    parser.add_argument('-b', action='store_true', help='Number non-empty output lines.')
    parser.add_argument('-e', action='store_true', help='Display $ at end of each line (implies -v).')
    parser.add_argument('-n', action='store_true', help='Number all output lines.')
    parser.add_argument('-s', action='store_true', help='Squeeze multiple adjacent empty lines.')
    parser.add_argument('-t', action='store_true', help='Display TAB characters as ^I (implies -v).')
    parser.add_argument('-u', action='store_true', help='Disable output buffering (ignored, as Python I/O is sufficiently fast).')
    parser.add_argument('-v', action='store_true', help='Display non-printing characters.')
    
    parser.add_argument('files', nargs='*', help='Files to process. Reads from stdin if none are given.')
    
    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # The -b option overrides -n
    if args.b:
        args.n = False
        
    # Determine if we need to do line-by-line "cooked" processing
    is_cooked_mode = any([args.b, args.e, args.n, args.s, args.t, args.v])
    
    exit_status = 0
    
    try:
        # Use fileinput to handle reading from files or stdin.
        # It's opened in binary mode for the fast path to avoid codec errors.
        with fileinput.input(files=args.files or ('-',), mode='rb' if not is_cooked_mode else 'r') as f:
            if not is_cooked_mode:
                # --- Fast Path (Raw Mode) ---
                # If no formatting is needed, copy in efficient chunks.
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    sys.stdout.buffer.write(chunk)
            else:
                # --- Slow Path (Cooked Mode) ---
                was_empty = False
                line_number = 1
                for line in f:
                    # Handle -s (squeeze blank lines)
                    if args.s:
                        is_empty = (line == '\n')
                        if is_empty and was_empty:
                            continue
                        was_empty = is_empty
                        
                    prefix = ""
                    # Handle -n and -b (line numbering)
                    if args.n or (args.b and line.strip()):
                        prefix = f"{line_number:6d}\t"
                        line_number += 1
                        
                    # Handle -e, -t, -v (character formatting)
                    processed_line = format_line_for_printing(line, args)
                    
                    print(prefix + processed_line, end='')

    except FileNotFoundError as e:
        print(f"{program_name}: {e.filename}: {e.strerror}", file=sys.stderr)
        exit_status = 1
    except IsADirectoryError:
        # fileinput doesn't raise this, so we check manually if needed,
        # but for cat, the OS usually provides the error.
        # This is a placeholder for a more specific check if required.
        print(f"{program_name}: Input is a directory", file=sys.stderr)
        exit_status = 1

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
