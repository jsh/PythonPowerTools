#!/usr/bin/env python3
"""
Name: uudecode
Description: decode a binary file
Author: Nick Ing-Simmons, Tom Christiansen, brian d foy (Original Perl Authors)
License: perl
"""

import sys
import os
import argparse
import binascii
import fileinput
import re
from contextlib import contextmanager

def process_stream(stream, args, program_name):
    """
    Scans an input stream for one or more uuencoded blocks and decodes them.
    """
    exit_status = 0
    
    # This outer loop allows for multiple 'begin...end' blocks in one stream.
    while True:
        line = stream.readline()
        if not line:
            break # End of input

        # 1. Find the 'begin' header line
        match = re.match(r'begin\s+(\d+)\s+(\S+)', line)
        if not match:
            continue

        mode_str, header_name = match.groups()
        mode = int(mode_str, 8) # Convert octal string to integer
        
        # 2. Open the output file or stdout
        try:
            with open_output_stream(header_name, mode, args) as f_out:
                # 3. Decode the body until the 'end' line is found
                ended_correctly = decode_body(stream, f_out, args)
                if not ended_correctly:
                    print(f"{program_name}: missing end; '{f_out.name}' may be truncated
