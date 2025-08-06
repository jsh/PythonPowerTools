#!/usr/bin/env python3
"""
Name: base64
Description: encode and decode base64 data
Author: Michael Mikonos (Original Perl Author)
License: artistic2
"""

import sys
import os
import argparse
import base64
import binascii

__version__ = "1.0"

def encode_stream(input_stream, output_stream):
    """
    Reads from an input stream, base64-encodes it, and writes to an output stream.
    """
    # base64.encodebytes automatically wraps lines at 76 characters and adds
    # a trailing newline, matching the standard behavior.
    encoded_data = base64.encodebytes(input_stream.read())
    output_stream.write(encoded_data)

def decode_stream(input_stream, output_stream):
    """
    Reads from an input stream, base64-decodes it, and writes to an output stream.
    """
    try:
        # base64.b64decode is robust and handles whitespace automatically.
        decoded_data = base64.b64decode(input_stream.read())
        output_stream.write(decoded_data)
    except binascii.Error:
        # This error is raised if the input contains non-base64 characters.
        print(f"{sys.argv[0]}: bad input", file=sys.stderr)
        sys.exit(1)

def main():
    """Parses arguments and orchestrates the encoding/decoding process."""
    parser = argparse.ArgumentParser(
        description="Encode or decode base64 data to standard output.",
        usage="%(prog)s [-dv] [-o FILE] [FILE]"
    )
    parser.add_argument(
        '-d', '--decode',
        action='store_true',
        help='decode data'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='write output to the specified FILE'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        'input_file',
        nargs='?', # Makes the input file optional
        default='-',
        help="Input file to process. Reads from stdin if not specified or if FILE is '-'."
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- Setup Input and Output Streams ---
    # All I/O must be done in binary mode.
    
    input_stream = None
    output_stream = None
    
    try:
        # Open input stream
        if args.input_file == '-':
            input_stream = sys.stdin.buffer
        else:
            if os.path.isdir(args.input_file):
                print(f"{program_name}: '{args.input_file}' is a directory", file=sys.stderr)
                sys.exit(1)
            input_stream = open(args.input_file, 'rb')

        # Open output stream
        if args.output_file:
            output_stream = open(args.output_file, 'wb')
        else:
            output_stream = sys.stdout.buffer

        # --- Perform Action ---
        with input_stream, output_stream:
            if args.decode:
                decode_stream(input_stream, output_stream)
            else:
                encode_stream(input_stream, output_stream)

    except IOError as e:
        print(f"{program_name}: cannot open '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
