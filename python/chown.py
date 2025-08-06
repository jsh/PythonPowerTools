#!/usr/bin/env python3
"""
Name: chown
Description: change ownership of files
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse

# The pwd and grp modules are not available on Windows.
try:
    import pwd
    import grp
except ImportError:
    print("Error: This script requires a Unix-like environment and is not compatible with Windows.", file=sys.stderr)
    sys.exit(1)

# This global variable tracks the overall exit status.
exit_status = 0

def change_owner(path: str, uid: int, gid: int, follow_links: bool, program_name: str):
    """
    Changes the owner and/or group of a single file or directory.
    """
    global exit_status
    try:
        # The 'follow_symlinks' parameter controls whether we affect the link
        # itself (False, like lchown) or its target (True, like chown).
        os.chown(path, uid, gid, follow_symlinks=not follow_links)
    except OSError as e:
        print(f"{program_name}: cannot access '{path}': {e.strerror}", file=sys.stderr)
        exit_status = 1

def main():
    """Parses arguments and orchestrates the chown process."""
    # We use argparse for simple flag parsing but will handle logic manually
    # due to the complex, order-dependent arguments.
    parser = argparse.ArgumentParser(
        description="Change file owner and group.",
        usage="%(prog)s [-R [-H | -L | -P]] user[:group] file...",
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

    owner_spec = remaining_args[0]
    files_to_process = remaining_args[1:]
    
    # Validate flag combinations
    if sum([args.H, args.L, args.P]) > 1:
        print(f"{program_name}: options -H, -L, -P are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    if (args.H or args.L or args.P) and not args.R:
        print(f"{program_name}: options -H, -L, -P require -R", file=sys.stderr)
        sys.exit(1)
        
    # --- 2. Get User ID (UID) and Group ID (GID) ---
    uid, gid = -1, -1
    if ':' in owner_spec:
        owner, group = owner_spec.split(':', 1)
    else:
        owner, group = owner_spec, None

    # Get UID
    if owner:
        if owner.isdigit():
            uid = int(owner)
        else:
            try:
                uid = pwd.getpwnam(owner).pw_uid
            except KeyError:
                print(f"{program_name}: invalid user: '{owner}'", file=sys.stderr)
                sys.exit(1)
    
    # Get GID
    if group:
        if group.isdigit():
            gid = int(group)
        else:
            try:
                gid = grp.getgrnam(group).gr_gid
            except KeyError:
                print(f"{program_name}: invalid group: '{group}'", file=sys.stderr)
                sys.exit(1)

    # --- 3. Process Files ---
    if not args.R:
        # --- Non-Recursive Mode ---
        # By default, chown follows symlinks that are command-line arguments.
        for path in files_to_process:
            change_owner(path, uid, gid, follow_links=True, program_name=program_name)
    else:
        # --- Recursive Mode ---
        if args.L: # Follow all symlinks
            for path in files_to_process:
                # First, change the top-level item itself.
                change_owner(path, uid, gid, follow_links=True, program_name=program_name)
                # Then, walk the tree, following all links.
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path, followlinks=True):
                        for name in dirs + files:
                            change_owner(os.path.join(root, name), uid, gid, follow_links=True, program_name=program_name)
        
        elif args.H: # Follow command-line symlinks only
            for path in files_to_process:
                # Change the top-level item, following the link if it is one.
                change_owner(path, uid, gid, follow_links=True, program_name=program_name)
                # Walk the tree, but do NOT follow links encountered during the walk.
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path, followlinks=False):
                        for name in dirs + files:
                            change_owner(os.path.join(root, name), uid, gid, follow_links=False, program_name=program_name)

        else: # -P is the default: Do not follow any symlinks
            for path in files_to_process:
                # Change the top-level item without following links.
                change_owner(path, uid, gid, follow_links=False, program_name=program_name)
                # Walk the tree without following any links.
                if os.path.isdir(path) and not os.path.islink(path):
                    for root, dirs, files in os.walk(path, followlinks=False):
                        for name in dirs + files:
                            change_owner(os.path.join(root, name), uid, gid, follow_links=False, program_name=program_name)

    sys.exit(exit_status)

if __name__ == "__main__":
    main()
