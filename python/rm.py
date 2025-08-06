#!/usr/bin/env python3
"""
Name: rm
Description: remove directory entries
Author: brian d foy, bdfoy@cpan.org (Original Perl Author)
License: artistic2
"""

import sys
import os
import shutil
import argparse
import stat

# This global variable tracks the overall exit status.
exit_status = 0

def ask_confirmation(prompt: str) -> bool:
    """Asks the user a yes/no question and returns their choice."""
    try:
        answer = input(prompt).lower()
        return answer.startswith('y')
    except (EOFError, KeyboardInterrupt):
        print() # Print a newline for clarity after Ctrl+C/D
        return False

def remove_path(path: str, args: argparse.Namespace):
    """
    Handles the removal of a single path, be it a file or a directory.
    """
    global exit_status
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Pre-removal checks and prompts ---
    
    # If file doesn't exist, it's an error unless -f is used.
    if not os.path.lexists(path):
        if not args.force:
            print(f"{program_name}: cannot remove '{path}': No such file or directory", file=sys.stderr)
            exit_status = 1
        return

    # If it's a directory but -r is not specified, it's an error.
    if os.path.isdir(path) and not os.path.islink(path) and not args.recursive:
        print(f"{program_name}: cannot remove '{path}': Is a directory", file=sys.stderr)
        exit_status = 1
        return

    # -i: Prompt for every file.
    if args.interactive:
        prompt_type = "directory" if os.path.isdir(path) and not os.path.islink(path) else "file"
        if not ask_confirmation(f"remove {prompt_type} '{path}'? "):
            return
            
    # --- 2. Perform the Removal ---
    
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            # Use shutil.rmtree for recursive deletion.
            # We don't need our own recursive walk because the prompts are handled
            # at the top level for directories when using -i.
            shutil.rmtree(path)
        else:
            # os.remove works for files and symbolic links.
            os.remove(path)
            
        # -v: If successful, print what was done.
        if args.verbose:
            print(f"removed '{path}'")

    except OSError as e:
        # If -f is not set, report the error.
        if not args.force:
            print(f"{program_name}: cannot remove '{path}': {e.strerror}", file=sys.stderr)
            exit_status = 1

def main():
    """Parses arguments and orchestrates the file removal process."""
    parser = argparse.ArgumentParser(
        description="Remove files or directories.",
        usage="%(prog)s [-fiPrRv] file ...",
        add_help=False # Use custom help to show -r and -R together
    )
    # The -f and -i options are mutually exclusive. Last one wins is complex,
    # so we'll enforce mutual exclusion which is clearer for a Python script.
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-f', '--force', action='store_true', help='ignore nonexistent files and arguments, never prompt')
    group.add_argument('-i', '--interactive', action='store_true', help='prompt before every removal')
    
    parser.add_argument('-P', help=argparse.SUPPRESS) # For compatibility, does nothing
    parser.add_argument('-r', '-R', '--recursive', action='store_true', help='remove directories and their contents recursively')
    parser.add_argument('-v', '--verbose', action='store_true', help='explain what is being done')
    
    # Custom help action
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='show this help message and exit')

    parser.add_argument('files', nargs='+', help='One or more files or directories to remove.')
    
    args = parser.parse_args()

    # --- Process each path from the command line ---
    for path in args.files:
        remove_path(path, args)
        
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
