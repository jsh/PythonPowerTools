#!/usr/bin/env python3
"""
Name: mkdir
Description: create directories
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import stat

def parse_symbolic_mode(sym_mode: str) -> int:
    """
    Parses a chmod-style symbolic permission string (e.g., "u+r,g-w").
    It is applied relative to a starting mode of a=rwx (0o777).
    """
    mode = 0o777
    
    who_map = {'u': stat.S_IRWXU, 'g': stat.S_IRWXG, 'o': stat.S_IRWXO, 'a': stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO}
    perm_map = {'r': stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH,
                'w': stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH,
                'x': stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH}

    for clause in sym_mode.split(','):
        match = re.match(r'([ugoa]*)([+-=])([rwx]+)', clause)
        if not match:
            return -1 # Invalid format

        who_str, op, perm_str = match.groups()
        who_mask = 0
        for char in who_str or 'a': # 'a' is the default 'who'
            who_mask |= who_map.get(char, 0)

        perm_mask = 0
        for char in perm_str:
            perm_mask |= perm_map.get(char, 0)
            
        # The permissions to apply are limited by the 'who' mask
        bits_to_change = who_mask & perm_mask

        if op == '+':
            mode |= bits_to_change
        elif op == '-':
            mode &= ~bits_to_change
        elif op == '=':
            # Clear the 'who' bits, then set the new permission bits
            mode &= ~who_mask
            mode |= bits_to_change
            
    return mode

def get_mode(mode_str: str) -> int:
    """
    Determines the file mode, supporting both octal and symbolic formats.
    """
    # Try to parse as an octal number first
    if re.match(r'^[0-7]{1,4}$', mode_str):
        return int(mode_str, 8)
    
    # Otherwise, parse as a symbolic mode
    return parse_symbolic_mode(mode_str)

def main():
    """Parses arguments and creates the specified directories."""
    parser = argparse.ArgumentParser(
        description="Create directories.",
        usage="%(prog)s [-p] [-m mode] directory ..."
    )
    parser.add_argument(
        '-p', '--parents',
        action='store_true',
        help='Create parent directories as needed.'
    )
    parser.add_argument(
        '-m', '--mode',
        help='Set the file permission mode (octal or symbolic, e.g., 755 or u+rwx).'
    )
    parser.add_argument(
        'directories',
        nargs='+', # Requires one or more directory names.
        help='One or more directories to create.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    exit_status = 0
    final_mode = -1 # -1 means use the system default mode (respecting umask)

    # --- Determine the final mode for directory creation ---
    if args.mode:
        final_mode = get_mode(args.mode)
        if final_mode < 0:
            print(f"{program_name}: invalid mode: '{args.mode}'", file=sys.stderr)
            sys.exit(1)

    # --- Create the Directories ---
    for dirname in args.directories:
        try:
            if args.parents:
                # os.makedirs is the direct equivalent of `mkdir -p`.
                # The `exist_ok=True` argument prevents an error if the
                # directory already exists.
                # If mode is -1, os.makedirs uses a default of 0o777.
                if final_mode != -1:
                    os.makedirs(dirname, mode=final_mode, exist_ok=True)
                else:
                    os.makedirs(dirname, exist_ok=True)
            else:
                # os.mkdir creates a single directory.
                if final_mode != -1:
                    os.mkdir(dirname, mode=final_mode)
                else:
                    os.mkdir(dirname)

        except FileExistsError:
            # This is only an error if -p is not specified.
            print(f"{program_name}: cannot create directory '{dirname}': File exists", file=sys.stderr)
            exit_status = 1
        except OSError as e:
            print(f"{program_name}: cannot create directory '{dirname}': {e.strerror}", file=sys.stderr)
            exit_status = 1
    
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
