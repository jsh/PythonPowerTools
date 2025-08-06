#!/usr/bin/env python3
"""
Name: hexdump
Description: print input as hexadecimal
Author: Michael Mikonos (Original Perl Author)
License: artistic2
"""

import sys
import os
import argparse
import struct
import string

class HexdumpProcessor:
    """
    Encapsulates the state and logic for processing and displaying a hexdump.
    """
    def __init__(self, args):
        self.args = args
        self.address = 0
        self.previous_chunk = None
        self.is_duplicate = False

        # Prepare C-style escape characters for -c mode
        self.c_escapes = {
            0: r' \0', 7: r' \a', 8: r' \b', 9: r' \t',
            10: r' \n', 11: r' \v', 12: r' \f', 13: r' \r'
        }

    def run(self, stream):
        """Processes an entire input stream."""
        # Handle skip offset
        if self.args.skip > 0:
            if stream.seekable():
                stream.seek(self.args.skip)
                self.address = self.args.skip
            else:
                stream.read(self.args.skip)
                self.address = self.args.skip

        bytes_to_read = self.args.length if self.args.length else -1
        
        while bytes_to_read != 0:
            read_len = min(16, bytes_to_read) if bytes_to_read > 0 else 16
            chunk = stream.read(read_len)
            if not chunk:
                break
            
            if bytes_to_read > 0:
                bytes_to_read -= len(chunk)

            # Handle duplicate line suppression
            if not self.args.verbose and chunk == self.previous_chunk:
                if not self.is_duplicate:
                    print("*")
                    self.is_duplicate = True
                self.address += len(chunk)
                continue
            
            self.is_duplicate = False
            self.previous_chunk = chunk
            
            # Dispatch to the correct display function
            self.args.display_func(self, chunk)
            self.address += len(chunk)
            
        # Print the final address offset
        print(self.args.addr_format % self.address)

    # --- Display Functions ---
    def display_hex1(self, chunk): # -C mode
        addr_str = self.args.addr_format % self.address
        
        hex_parts = [f"{b:02x}" for b in chunk]
        # Add a space in the middle
        if len(hex_parts) > 8:
            hex_parts.insert(8, '')
        hex_str = ' '.join(hex_parts).ljust(49) # 16*3 + 1 space

        # Create the printable character representation
        ascii_str = "".join(chr(b) if chr(b) in string.printable and not chr(b).isspace() else '.' for b in chunk)
        
        print(f"{addr_str} {hex_str}|{ascii_str}|")

    def display_hex2(self, chunk): # -x mode (default)
        addr_str = self.args.addr_format % self.address
        # Unpack bytes into 2-byte words (shorts)
        words = struct.unpack(f'<{len(chunk)//2}H', chunk[:len(chunk)//2*2])
        hex_words = [f"{w:04x}" for w in words]
        print(f"{addr_str} {'  '.join(hex_words)}")
        
    def display_char(self, chunk): # -c mode
        addr_str = self.args.addr_format % self.address
        char_reps = []
        for b in chunk:
            if chr(b) in string.printable and not chr(b).isspace():
                char_reps.append(f"  {chr(b)}")
            elif b in self.c_escapes:
                char_reps.append(self.c_escapes[b])
            else:
                char_reps.append(f"{b:03o}")
        print(f"{addr_str} {''.join(char_reps)}")

def revert_hexdump(stream):
    """Reads a canonical hexdump from a stream and writes binary data to stdout."""
    for line in stream:
        line = line.strip()
        if not line or line == '*': continue
        
        # Isolate the hex part of the line
        parts = line.split('|')
        hex_part = parts[0].split(None, 1)[-1]
        
        try:
            # Remove all whitespace and convert hex string to bytes
            binary_data = bytes.fromhex("".join(hex_part.split()))
            sys.stdout.buffer.write(binary_data)
        except ValueError:
            print(f"hexdump: bad hex input: '{hex_part}'", file=sys.stderr)
            sys.exit(1)

def main():
    """Parses arguments and runs the hexdump or revert logic."""
    parser = argparse.ArgumentParser(
        description="Display file contents in hexadecimal and other formats.",
        usage="%(prog)s [-bCcdorvx] [-n length] [-s skip] [file ...]"
    )
    # Display modes are mutually exclusive
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-b', dest='display_func', action='store_const', const=HexdumpProcessor.display_char, help='One-byte character display.')
    mode_group.add_argument('-C', dest='display_func', action='store_const', const=HexdumpProcessor.display_hex1, help='Canonical hex+ASCII display.')
    mode_group.add_argument('-c', dest='display_func', action='store_const', const=HexdumpProcessor.display_char, help='One-byte character display.')
    mode_group.add_argument('-d', dest='display_func', action='store_const', const=None, help='Two-byte decimal display (not implemented).')
    mode_group.add_argument('-o', dest='display_func', action='store_const', const=None, help='Two-byte octal display (not implemented).')
    mode_group.add_argument('-x', dest='display_func', action='store_const', const=HexdumpProcessor.display_hex2, help='Two-byte hexadecimal display.')
    
    parser.add_argument('-n', dest='length', type=int, help='Interpret only LENGTH bytes of input.')
    parser.add_argument('-r', '--revert', action='store_true', help='Perform a reverse operation.')
    parser.add_argument('-s', dest='skip', type=int, default=0, help='Skip OFFSET bytes from the beginning.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display all data; do not use `*` for duplicate lines.')
    
    parser.add_argument('files', nargs='*', help='Input files. Reads from stdin if none are given.')
    
    args = parser.parse_args()

    # Set default display function if none was chosen
    args.display_func = args.display_func or HexdumpProcessor.display_hex2
    
    # Set address format based on display function
    args.addr_format = '%07x' if args.display_func == HexdumpProcessor.display_char else '%08x'

    # --- Run Revert or Hexdump Mode ---
    if args.revert:
        if args.files:
            for filepath in args.files:
                with open(filepath, 'r') as f:
                    revert_hexdump(f)
        else:
            revert_hexdump(sys.stdin)
    else:
        processor = HexdumpProcessor(args)
        if args.files:
            for filepath in args.files:
                with open(filepath, 'rb') as f:
                    processor.run(f)
        else:
            processor.run(sys.stdin.buffer)

if __name__ == "__main__":
    main()
