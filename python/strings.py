#!/usr/bin/env python3
"""
Name: strings
Description: find the printable strings in a binary file
Author: Nathan Scott Thompson (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import fileinput
from string import printable

def scan_stream(stream, display_name, args):
    """
    Reads a binary stream, finds all printable strings, and prints them.
    """
    # Read the entire stream into a bytes object.
    data = stream.read()
    
    # Define the set of printable characters as bytes. This includes tab (\t)
    # and the ASCII characters from space (0x20) to tilde (0x7e).
    printable_bytes = rb'[\t\x20-\x7e]'
    
    # We compile a regular expression to find sequences of these printable
    # characters that meet the minimum length requirement.
    # The pattern becomes, for example, rb'[\t\x20-\x7e]{4,}'
    try:
        pattern = re.compile(
            printable_bytes + b'{' + str(args.min_len).encode('ascii') + b',}'
        )
    except re.error as e:
        print(f"Error: Invalid regex pattern generated: {e}", file=sys.stderr)
        return

    # re.finditer is an efficient way to find all matches and their offsets.
    for match in pattern.finditer(data
