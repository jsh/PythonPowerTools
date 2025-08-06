#!/usr/bin/env python3
"""
Name: ln
Description: create links
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse

# This global variable tracks the overall exit status.
# It starts at 0 (success) and is set to 1 on the first failure.
exit_status = 0

def create_link(source: str, dest: str, is_symbolic: bool, force: bool, program_name: str):
    """
    Creates a single link from a source to a destination.
    Handles force-unlinking and symbolic/hard link creation.
    """
    global exit_status
    
    # If the -f flag is used, try to remove the destination if it exists.
    # We use lexists to handle cases where the destination is a symlink.
    if force and os.path.lexists(dest):
        try:
            os.unlink(dest)
        except OSError as e:
            print(f"{program_name}: cannot unlink '{dest}': {e.strerror}", file=sys.stderr)
            exit_status = 1
            return # Do not proceed if unlinking fails

    # Attempt to create the link.
    try:
        if is_symbolic:
            os.symlink(source, dest)
        else:
            os.link(source, dest)
    except OSError as e:
        print(f"{program_name}: failed to link '{source}' to '{dest}': {e.strerror}", file=sys.stderr)
        exit_status = 1

def main():
    """Parses arguments and orchestrates the link creation process."""
    parser = argparse.ArgumentParser(
        description="Create hard or symbolic links between files.",
        usage="%(prog)s [-sf] source_file [target_file | source_file... target_directory]"
    )
    parser.add_argument(
        '-s', '--symbolic',
        action='store_true',
        help='create symbolic links instead of hard links'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='remove existing destination files'
    )
    parser.add_argument(
        'paths',
        nargs='+', # Requires at least one path argument.
        help='The source and target paths.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    
    # The last path on the command line is always the target.
    target = args.paths.pop()
    sources = args.paths

    # --- Determine the linking scenario ---

    # Scenario 1: `ln source_file` (no target specified)
    if not sources:
        source = target # In this case, the only argument is the source.
        # The target becomes the basename of the source in the current directory.
        dest_in_cwd = os.path.basename(source)
        create_link(source, dest_in_cwd, args.symbolic, args.force, program_name)

    # Scenario 2: `ln source_file ... target_directory`
    elif os.path.isdir(target):
        for source in sources:
            dest_in_dir = os.path.join(target, os.path.basename(source))
            create_link(source, dest_in_dir, args.symbolic, args.force, program_name)
    
    # Scenario 3: `ln source_file target_file`
    elif len(sources) == 1:
        source = sources[0]
        create_link(source, target, args.symbolic, args.force, program_name)

    # Scenario 4: Invalid usage (multiple sources to a non-directory target)
    else:
        print(f"{program_name}: target '{target}' is not a directory", file=sys.stderr)
        sys.exit(1)
        
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
