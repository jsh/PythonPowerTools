#!/usr/bin/env python3
"""
Name: arch
Description: display system machine type
Author: Theo Van Dinter, felicity@kluge.net (Original Perl Author)
License: perl

A Python port of the 'arch' utility.

Displays the current system architecture type, which is generally
equivalent to `uname -m`. It applies special formatting for SunOS
and OpenBSD systems.
"""

import platform
import re
import sys
import argparse
import os

def main():
    """Parses arguments, determines the system architecture, and prints it."""
    
    # Use argparse for robust handling of command-line flags.
    # The usage string is customized to match the original script.
    parser = argparse.ArgumentParser(
        description="Display the system machine architecture type.",
        usage=f"{os.path.basename(sys.argv[0])} [-k]",
        add_help=False # Manually add help for more control
    )
    
    parser.add_argument(
        '-k', 
        action='store_true',
        help='On SunOS, display kernel architecture instead of system architecture.'
    )
    parser.add_argument(
        '-h', '--help', 
        action='help',
        help='Show this help message and exit.'
    )

    # argparse will automatically handle any arguments that are not '-k', '-h',
    # or '--help' by printing the usage message and exiting with an error.
    args = parser.parse_args()

    # Get system information using platform.uname().
    # This returns a result object with attributes like .system and .machine.
    uname_result = platform.uname()
    system_name = uname_result.system
    arch = uname_result.machine

    # --- Special Platform-Specific Logic ---

    # 1. On SunOS, unless the -k flag is used, truncate the architecture string.
    # For example, 'sun4m' becomes 'sun4'.
    if 'SunOS' in system_name and not args.k:
        arch = re.sub(r'^(sun\d+).*', r'\1', arch)

    # 2. On OpenBSD, prepend the system name to the architecture.
    if system_name == "OpenBSD":
        arch = f"{system_name}.{arch}"

    print(arch)
    sys.exit(0)

if __name__ == "__main__":
    main()
