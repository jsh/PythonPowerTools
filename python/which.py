#!/usr/bin/env python3
"""
Name: which
Description: report full paths of commands
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import shutil
import argparse

def find_all_executables(cmd):
    """
    Finds all occurrences of an executable in the system's PATH.
    This is a manual implementation to support the '-a' flag.
    Returns a list of full paths.
    """
    paths_found = []
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    # On Windows, check for executable extensions (e.g., .exe, .bat)
    if sys.platform == "win32":
        # Ensure the command itself is checked first if it has an extension
        _, ext = os.path.splitext(cmd)
        pathext = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").lower().split(';')
        if ext.lower() not in pathext:
             check_extensions = pathext
        else:
             check_extensions = [''] # Already has an extension
    else:
        # On Unix-like systems, files are executable by permission, not extension.
        check_extensions = ['']

    for directory in path_dirs:
        for ext in check_extensions:
            full_path = os.path.join(directory, cmd + ext)
            # A file is considered an executable if it's a file and the
            # current user has execute permissions.
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                paths_found.append(full_path)
    
    return paths_found

def main():
    """Parses arguments and finds executables in the system PATH."""
    parser = argparse.ArgumentParser(
        description="Prints the full paths to the commands given.",
        usage="%(prog)s [-a] filename ..."
    )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Print all instances of a command found in the PATH.'
    )
    parser.add_argument(
        'commands',
        nargs='+', # Requires one or more command names.
        help='One or more command names to search for.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    
    # This tracks if ANY of the commands were not found.
    not_found_count = 0

    for command in args.commands:
        if args.all:
            # --- -a (All) Mode ---
            # Manually search the PATH to find all occurrences.
            results = find_all_executables(command)
            if results:
                for path in results:
                    print(path)
            else:
                print(f"{program_name}: {command}: command not found", file=sys.stderr)
                not_found_count += 1
        else:
            # --- Default Mode ---
            # shutil.which() is the standard, cross-platform way to do this.
            # It automatically handles PATH, path separators, and executable extensions.
            result = shutil.which(command)
            if result:
                print(result)
            else:
                print(f"{program_name}: {command}: command not found", file=sys.stderr)
                not_found_count += 1
                
    # Exit with 0 if all were found, 1 otherwise.
    sys.exit(1 if not_found_count > 0 else 0)

if __name__ == "__main__":
    main()
