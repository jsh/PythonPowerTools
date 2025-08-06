#!/usr/bin/env python3
"""
Name: uname
Description: print system information
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl
"""

import platform
import sys
import argparse

def main():
    """Parses arguments and prints system information."""
    parser = argparse.ArgumentParser(
        description="Print certain system information. With no options, -s is assumed.",
        usage="%(prog)s [-snrvma]"
    )
    # The flags are stored as boolean attributes on the 'args' object.
    parser.add_argument('-s', action='store_true', help='print the kernel name')
    parser.add_argument('-n', action='store_true', help='print the network node hostname')
    parser.add_argument('-r', action='store_true', help='print the kernel release')
    parser.add_argument('-v', action='store_true', help='print the kernel version')
    parser.add_argument('-m', action='store_true', help='print the machine hardware name')
    parser.add_argument('-a', '--all', action='store_true', help='print all information, in the order -s, -n, -r, -v, -m')

    # argparse will exit with an error if any non-flag arguments are given.
    args = parser.parse_args()

    # platform.uname() returns an object with named attributes like .system and .node.
    uname_result = platform.uname()
    output_parts = []

    # --- Build the output list based on flags ---
    # The order of these 'if' statements is important as it defines the output order.

    if args.s or args.all:
        output_parts.append(uname_result.system)
    
    if args.n or args.all:
        output_parts.append(uname_result.node)

    if args.r or args.all:
        output_parts.append(uname_result.release)

    if args.v or args.all:
        output_parts.append(uname_result.version)

    if args.m or args.all:
        output_parts.append(uname_result.machine)

    # --- Default behavior ---
    # If the output list is empty, it means no flags were provided.
    if not output_parts:
        output_parts.append(uname_result.system)
    
    # Print the collected parts, joined by a single space.
    print(" ".join(output_parts))
    sys.exit(0)

if __name__ == "__main__":
    main()
