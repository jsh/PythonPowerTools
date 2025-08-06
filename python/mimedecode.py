#!/usr/bin/env python3
"""
Name: mimedecode
Description: extract MIME attachments in a uudecode-like manner
Author: Nick Ing-Simmons, nick@ni-s.u-net.com (Original Perl Author)
License: perl
"""

import email
import os
import sys
import argparse
import fileinput
from email.message import Message

def extract_attachments(msg: Message, output_dir: str):
    """
    Walks through a message object and saves any parts that are
    identified as file attachments.
    """
    found_attachment = False
    for part in msg.walk():
        # A multipart container is not an attachment itself
        if part.is_multipart():
            continue

        # The get_filename() method is a convenient way to identify
        # parts that are meant to be saved as files.
        filename = part.get_filename()

        # If a filename is found, we treat it as an attachment.
        if filename:
            found_attachment = True
            
            # Sanitize the filename to prevent directory traversal attacks
            # e.g., a filename like '../../etc/passwd' becomes 'passwd'
            filename = os.path.basename(filename)
            if not filename:
                continue

            filepath = os.path.join(output_dir, filename)
            
            # get_payload(decode=True) automatically handles Base64 or
            # Quoted-Printable decoding.
            payload = part.get_payload(decode=True)

            if payload:
                print(f"Saving attachment: {filepath}", file=sys.stderr)
                try:
                    with open(filepath, 'wb') as f:
                        f.write(payload)
                except IOError as e:
                    print(f"Error: Could not write file {filepath}: {e}", file=sys.stderr)
    
    if not found_attachment:
        print("No file attachments found in the message.", file=sys.stderr)


def main():
    """Parses command-line arguments and processes the email input."""
    parser = argparse.ArgumentParser(
        description="Extract MIME attachments from one or more email files.",
        usage="%(prog)s [-d directory] [file...]"
    )
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='Directory to save attachments to (default: current directory).'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Email files to process. Reads from standard input
