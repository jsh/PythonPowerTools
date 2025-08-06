#!/usr/bin/env python3
"""
Name: unlink
Description: simpler than rm
Author: Michael Mikonos (Original Perl Author)
License: artistic2

A Python port of the 'unlink' utility.

Removes a single specified file. It cannot be used to remove directories.
If the argument is a symbolic link, the link itself is removed.
"""
import os
import sys

# Define constants for exit codes for clarity
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

def main():
    """Validates arguments and unlinks the specified file."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]

    # --- Argument Validation ---

    # 1. Check for any options (e.g., -h), which are not allowed.
    if any(arg.startswith('-') for arg in args):
        print(f"usage: {program_name} FILE", file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    # 2. Check for the correct number of file operands (exactly one).
    if len(args) == 0:
        print(f"{program_name}: missing operand", file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    if len(args) > 1:
        print(f"{program_name}: extra operand: '{args[1]}'", file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    file_to_unlink = args[0]

    # --- Pre-operation Checks ---

    # 3. Check if the target is a directory.
    # os.path.isdir() correctly returns True for a symlink pointing to a directory.
    if os.path.isdir(file_to_unlink):
        print(f"{program_name}: cannot unlink '{file_to_unlink}': Is a directory", 
              file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    # --- Unlink Operation ---

    # 4. Attempt to unlink the file.
    try:
        # os.unlink() is Python's direct equivalent to Perl's unlink function.
        # It will raise an OSError if it fails for any reason.
        os.unlink(file_to_unlink)
    except OSError as e:
        # The exception object 'e' contains the system error details.
        # e.strerror is the message (e.g., "Permission denied")
        # e.filename is the path that caused the error.
        print(f"{program_name}: cannot unlink '{e.filename}': {e.strerror}", 
              file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    # If we reach here, the operation was successful.
    sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
