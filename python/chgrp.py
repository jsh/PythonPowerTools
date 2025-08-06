#!/usr/bin/env python3
"""
Name: chgrp
Description: change group ownership of files
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse

# The grp module is not available on Windows.
try:
    import grp
except ImportError:
    print("Error: This script requires a Unix-like environment and is not compatible with Windows.", file=sys.stderr)
    sys.exit(1)

# This global variable tracks the overall exit status.
exit_status = 0

def change_group(path: str, gid: int, program_name: str):
    """
    Changes the group of a single file or directory. Does not follow symlinks.
    """
    global exit_status
    try:
        # Use lchown to change the group of the link itself, not its target.
        # We need the original UID, so we get it from lstat first.
        uid = os.lstat(path).st_uid
        os.lchown(path, uid, gid)
    except OSError as e:
        print(f"{program_name}: cannot access '{path}': {e.strerror}", file=sys.stderr)
        exit_status = 1

def main():
    """Parses arguments and orchestrates the chgrp process."""
    # We use argparse for simple flag parsing but will handle logic manually.
    parser = argparse.ArgumentParser(
        description="Change group ownership of files.",
        usage="%(prog)s [-R [-H | -L | -P]] group file...",
        add_help=False # Manual parsing requires custom help handling.
    )
    # These are just for detection; their logic is handled manually.
    parser.add_argument('-R', action='store_true')
    parser.add_argument('-H', action='store_true')
    parser.add_argument('-L', action='store_true')
    parser.add_argument('-P', action='store_true')
    
    # Use parse_known_args to separate flags from positional args.
    args, remaining_args = parser.parse_known_args()
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Validate Arguments ---
    if len(remaining_args) < 2:
        parser.print_usage(sys.stderr)
        sys.exit(1)

    group_spec = remaining_args[0]
    files_to_process = remaining_args[1:]
    
    # Validate flag combinations
    if sum([args.H, args.L, args.P]) > 1:
        print(f"{program_name}: options -H, -L, -P are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    if (args.H or args.L or args.P) and not args.R:
        print(f"{program_name}: options -H, -L, -P require -R", file=sys.stderr)
        sys.exit(1)
        
    # --- 2. Get Group ID (GID) ---
    gid = -1
    if group_spec.isdigit():
        gid = int(group_spec)
    else:
        try:
            gid = grp.getgrnam(group_spec).gr_gid
        except KeyError:
            print(f"{program_name}: '{group_spec}' is an invalid group", file=sys.stderr)
            sys.exit(1)

    # --- 3. Process Files ---
    if not args.R:
        # --- Non-Recursive Mode ---
        for path in files_to_process:
            change_group(path, gid, program_name)
    else:
        # --- Recursive Mode ---
        if args.L: # Follow all symlinks
            for path in files_to_process:
                for root, dirs, files in os.walk(path, followlinks=True):
                    for name in dirs + files:
                        change_group(os.path.join(root, name), gid, program_name)
        
        elif args.H: # Follow command-line symlinks only
            for path in files_to_process:
                change_group(path, gid, program_name) # Change the link/file itself
                if os.path.islink(path):
                    # If it's a link, walk its target but don't follow links within.
                    try:
                        target = os.readlink(path)
                        # Make sure the target is an absolute path if the link is relative
                        if not os.path.isabs(target):
                            target = os.path.join(os.path.dirname(path), target)
                        
                        for root, dirs, files in os.walk(target, followlinks=False):
                            for name in dirs + files:
                                change_group(os.path.join(root, name), gid, program_name)
                    except OSError:
                        # Broken symlink, already handled by the first change_group call.
                        pass
                elif os.path.isdir(path):
                     # If it's a directory, walk it without following links.
                     for root, dirs, files in os.walk(path, followlinks=False):
                        for name in dirs + files:
                            change_group(os.path.join(root, name), gid, program_name)

        else: # -P is the default: Do not follow any symlinks
            for path in files_to_process:
                change_group(path, gid, program_name)
                if os.path.isdir(path) and not os.path.islink(path):
                    for root, dirs, files in os.walk(path, followlinks=False):
                        for name in dirs + files:
                            change_group(os.path.join(root, name), gid, program_name)

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
