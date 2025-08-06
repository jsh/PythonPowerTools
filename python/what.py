#!/usr/bin/env python3
"""
Name: what
Description: extract version information from a file
Author: Ken Schumack, schumacks@att.net (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re

def process_file(filepath: str, stop_after_first: bool) -> int:
    """
    Scans a single file for SCCS version strings and prints them.

    Args:
        filepath: The path to the file to scan.
        stop_after_first: If True, stop after the first match is found.

    Returns:
        The number of matches found in the file.
    """
    program_name = os.path.basename(sys.argv[0])
    match_count = 0

    print(f"{filepath}:")

    if os.path.isdir(filepath):
        # The original script just prints the directory name and moves on.
        return 0
    
    try:
        # We must read the file in binary mode ('rb') to correctly find
        # the pattern in any type of file without decoding errors.
        with open(filepath, 'rb') as f:
            data = f.read()
    except IOError as e:
        print(f"{program_name}: Unable to open '{filepath}': {e.strerror}", file=sys.stderr)
        return 0

    # This regex finds the magic pattern @(#) and captures everything after it
    # until it hits one of the terminator characters: ", >, null, or \.
    # The pattern is a bytes pattern (b'...') to search the binary data.
    pattern = re.compile(b'@\(#\)([^">\0\\]*)')

    # re.finditer is an efficient way to find all occurrences in the data.
    for match in pattern.finditer(data):
        # The captured group (group 1) is the version string itself.
        # We decode it from bytes to a string for printing.
        version_string =
