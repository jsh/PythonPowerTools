#!/usr/bin/env python3
"""
Name: cp
Description: copy files and/or directories
Author: brian d foy, bdfoy@cpan.org (Original Perl Author)
License: artistic2
"""

import sys
import os
import shutil
import argparse

# This global variable tracks the overall exit status.
exit_status = 0

def copy_file(source: str, dest: str, opts: argparse.Namespace):
    """
    Copies a single file, handling options for verbosity, interactivity,
    and preserving metadata.
    """
    global exit_status
    program_name = os.path.basename(sys.argv[0])

    # Prevent copying a file onto itself.
    if os.path.exists(dest) and os.path.samefile(source, dest):
        print(f"{program_name}: '{source}' and '{dest}' are the same file", file=sys.stderr)
        exit_status = 1
        return

    # -i (interactive): Prompt before overwriting. The -f (force) option overrides this.
    if not opts.force and opts.interactive and os.path.exists(dest):
        try:
            answer = input(f"overwrite '{dest}'? (y/n) [n] ")
            if not answer.lower().startswith('y'):
                return # Skip this file
        except (EOFError, KeyboardInterrupt):
            print() # Print a newline for clarity
            sys.exit(1)

    # -v (verbose): Print the operation being performed.
    if opts.verbose:
        print(f"'{source}' -> '{dest}'")

    try:
        # -p (preserve): Use shutil.copy2 to preserve metadata (timestamps, etc.).
        # Otherwise, use shutil.copy for a standard copy.
        if opts.preserve:
            shutil.copy2(source, dest)
        else:
            shutil.copy(source, dest)
    except Exception as e:
        print(f"{program_name}: error copying '{source}' to '{dest}': {e}", file=sys.stderr)
        exit_status = 1


def main():
    """Parses arguments and orchestrates the file copying process."""
    parser = argparse.ArgumentParser(
        description="Copy files.",
        usage="%(prog)s [-fipv] source_file target_file\n       %(prog)s [-fipv] source_file ... target_directory"
    )
    parser.add_argument('-f', '--force', action='store_true', help='force copy by removing existing destinations')
    parser.add_argument('-i', '--interactive', action='store_true', help='prompt before overwrite')
    parser.add_argument('-p', '--preserve', action='store_true', help='preserve file attributes (mode, timestamps)')
    parser.add_argument('-v', '--verbose', action='store_true', help='explain what is being done')
    parser.add_argument('paths', nargs='+', help='source and destination paths')
    
    args = parser.parse_args()
    
    if len(args.paths) < 2:
        parser.error("missing destination file operand after source(s)")

    # The last path on the command line is always the destination.
    destination = args.paths.pop()
    sources = args.paths
    
    # --- Determine the copying scenario ---

    # Scenario 1: Copying multiple files into a directory.
    if len(sources) > 1 and not os.path.isdir(destination):
        parser.error(f"target '{destination}' is not a directory")

    if os.path.isdir(destination):
        for source in sources:
            dest_path = os.path.join(destination, os.path.basename(source))
            copy_file(source, dest_path, args)
    
    # Scenario 2: Copying a single file to a new file.
    else:
        copy_file(sources[0], destination, args)

    sys.exit(exit_status)


if __name__ == "__main__":
    main()
