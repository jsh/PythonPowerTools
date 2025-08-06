#!/usr/bin/env python3
"""
Name: uuencode
Description: encode a binary file
Author: Tom Christiansen, tchrist@perl.com (Original Perl Author)
License: perl
"""

import sys
import os
import binascii
import argparse

# Define constants for exit codes for clarity
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

def encode_stream(input_stream, destination_name, mode):
    """
    Reads from a stream and writes uuencoded data to standard output.

    Args:
        input_stream: A file-like object opened in binary mode.
        destination_name (str): The name to use in the 'begin' header.
        mode (int): The file permission mode to use in the 'begin' header.
    """
    # The 'begin' line includes the file mode (as octal) and the remote filename.
    sys.stdout.write(f"begin {mode:03o} {destination_name}\n")

    # Read the input stream in 45-byte chunks, which is the standard
    # line length for uuencoding.
    while True:
        chunk = input_stream.read(45)
        if not chunk:
            break
        # binascii.b2a_uu handles the encoding, prepends the line-length
        # character, and appends a newline.
        encoded_line = binascii.b2a_uu(chunk)
        # We write to the buffer directly to handle the bytes correctly.
        sys.stdout.buffer.write(encoded_line)

    # A single backtick signifies the end of the encoded data.
    sys.stdout.write("`\n")
    sys.stdout.write("end\n")

def main():
    """Parses command-line arguments and orchestrates the encoding process."""
    parser = argparse.ArgumentParser(
        description="Encode a binary file into the uuencode format.",
        # Provide custom usage to match the original script's two modes.
        usage="%(prog)s [-h] [-p] [file] [name ...]"
    )
    parser.add_argument
