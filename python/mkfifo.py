#!/usr/bin/env python3
"""
Name: mkfifo
Description: make named pipes
Author: Jeffrey S. Haemer, Louis Krupp (Original Perl Authors)
License: perl
"""

import os
import sys
import argparse
import re

# This global variable tracks the overall exit status.
# It starts at 0 (success) and is set to 1 on the first failure.
exit_status = 0

def parse_symbolic_mode(sym_mode: str, base_mode: int) -> int:
    """
    Parses a chmod-style symbolic permission string (e.g., "u+r,g-w")
    and applies it to a base mode.
    """
    mode = base_mode
    
    # Maps for 'who' and 'what' parts of the symbolic mode
    who_map = {'u': 0o700, 'g': 0o070, 'o': 0o007, 'a': 0o777}
    perm_map = {'r': 0o444, 'w': 0o222, 'x': 0o111}

    # A symbolic mode can have multiple comma-separated clauses
    clauses = sym_mode.split(',')
    
    for clause in clauses:
        # Regex to parse 'who', 'how', and 'what' (e.g., 'ug', '+', 'rw')
        match = re.match(r'([ugoa]*)([+-=])([rwx]+)', clause)
        if not match:
            return -1 # Invalid format

        who_str, op, perm_str = match.groups()
        
        # If 'who' is not specified, it defaults to 'a' (all)
        if not who_str:
            who_str = 'a'
            
        # Calculate the masks for the operation
        who_mask = 0
        for char in who_str:
            who_mask |= who_map.get(char, 0)

        perm_mask = 0
        for char in perm_str:
            perm_mask |= perm_map.get(char, 0)
            
        # Apply the operation based on the operator
        if op == '+':
            mode |= (who_mask & perm_mask)
        elif op == '-':
            mode &= ~(who_mask & perm_mask)
        elif op == '=':
            mode = (mode & ~who_mask) | (who_mask & perm_mask)
            
    return mode

def get_mode(mode_str: str) -> int:
    """
    Determines the file mode, supporting both octal and symbolic formats.
    """
    # Try to parse as an octal number first
    if re.match(r'^[0-7]{1,4}$', mode_str):
        return int(mode_str, 8)
    
    # Otherwise, parse as a symbolic mode
    # The base mode for symbolic calculation is the default (0o666 & ~umask)
    original_umask = os.umask(0)
    os.umask(original_umask) # Restore it immediately
    default_mode = 0o666 & ~original_umask
    
    return parse_symbolic_mode(mode_str, default_mode)

def main():
    """Parses arguments and creates the named pipes."""
    global exit_status
    
    parser = argparse.ArgumentParser(
        description="Create named pipes (FIFOs).",
        usage="%(prog)s [-m mode] filename..."
    )
    parser.add_argument(
        '-m', '--mode',
        help='Set the file permission mode (octal or symbolic, e.g., 644 or g+w).'
    )
    parser.add_argument(
        'filenames',
        nargs='+', # Requires one or more filenames.
        help='One or more names for the FIFOs to create.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- Determine the final mode for mkfifo ---
    if args.mode:
        final_mode = get_mode(args.mode)
        if final_mode < 0:
            print(f"{program_name}: bad file mode: '{args.mode}'", file=sys.stderr)
            sys.exit(1)
    else:
        # Default mode: 0666 modified by the current umask
        original_umask = os.umask(0)
        os.umask(original_umask) # Restore it immediately
        final_mode = 0o666 & ~original_umask

    # --- Create the FIFOs ---
    for fifo_name in args.filenames:
        if os.path.exists(fifo_name):
            print(f"{program_name}: '{fifo_name}': file already exists", file=sys.stderr)
            exit_status = 1
            continue
        try:
            # os.mkfifo is the direct equivalent of POSIX::mkfifo
            os.mkfifo(fifo_name, final_mode)
        except OSError as e:
            print(f"{program_name}: '{fifo_name}': {e.strerror}", file=sys.stderr)
            exit_status = 1
            continue

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
