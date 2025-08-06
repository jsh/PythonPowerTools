#!/usr/bin/env python3
"""
Name: bcd
Description: format input as punch cards
Author: Steve Hayman (Original Author), Michael Mikonos (Perl Translator)
License: bsd
"""

import sys
import os
import argparse
import textwrap

# --- Data Tables ---

# This list maps an ASCII ordinal value to a 12-bit integer (bitmask)
# representing the punch pattern for that character. The 12 bits correspond
# to the 12 rows on a standard card (top to bottom: 12, 11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9).
# For our bitmask, bit 11 is row 12, bit 10 is row 11, bit 9 is row 0, ..., bit 0 is row 9.
HOLES = [
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
    0x0, 0x206, 0x20a, 0x042, 0x442, 0x222, 0x800, 0x406,
    0x812, 0x412, 0x422, 0xa00, 0x242, 0x400, 0x842, 0x300,
    0x200, 0x100, 0x080, 0x040, 0x020, 0x010, 0x008, 0x004,
    0x002, 0x001, 0x012, 0x40a, 0x80a, 0x212, 0x00a, 0x006,
    0x022, 0x900, 0x880, 0x840, 0x820, 0x810, 0x808, 0x804,
    0x802, 0x801, 0x500, 0x480, 0x440, 0x420, 0x410, 0x408,
    0x404, 0x402, 0x401, 0x280, 0x240, 0x220, 0x210, 0x208,
    0x204, 0x202, 0x201, 0x082, 0x806, 0x822, 0x600, 0x282,
] * 2 # The table is duplicated for ASCII values 128-255

# Create a reverse-lookup map for efficient decoding.
CODE_TO_CHAR = {code: chr(i) for i, code in enumerate(HOLES) if code != 0}

# The characters printed in each row when there is no punch.
ROW_CHARS = [' ', ' ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

def print_one_card(text: str, cols: int):
    """Prints a single ASCII art punch card for the given text."""
    # Top of card
    print(' ' + '_' * cols)

    # Line of human-readable text
    print('/', end='')
    for char in text.upper():
        # Only print the character if it has a valid punch pattern.
        print(char if HOLES[ord(char)] else ' ', end='')
    print(' ' * (cols - len(text)) + '|')

    # 12 rows of potential holes
    for row_num in range(12):
        print('|', end='')
        for char in text.upper():
            punch_code = HOLES[ord(char)]
            # Check the bit corresponding to the current row.
            if punch_code & (1 << (11 - row_num)):
                print(']', end='') # A "hole"
            else:
                print(ROW_CHARS[row_num], end='')
        # Print the rest of the blank row.
        print(ROW_CHARS[row_num] * (cols - len(text)) + '|')

    # Bottom of card
    print('|' + '_' * cols + '|')

def print_cards(text: str, cols: int):
    """Takes a string and prints it on one or more cards."""
    # Use textwrap to split the input string into chunks of the correct size.
    for chunk in textwrap.wrap(text, width=cols):
        print_one_card(chunk, cols)

def decode_stream(cols: int):
    """Reads punch card format from stdin and prints the decoded text."""
    while True:
        try:
            # Read the 14 lines that make up one card.
            _ = sys.stdin.readline() # Top border
            _ = sys.stdin.readline() # Text line
            data_rows = [sys.stdin.readline() for _ in range(12)]
            bottom = sys.stdin.readline() # Bottom border
            
            # If we hit the end of the file, stop.
            if not bottom:
                break
            
            decoded_chars = []
            for col_idx in range(1, cols + 1):
                punch_code = 0
                # Reconstruct the 12-bit integer for this column.
                for row_idx, row_line in enumerate(data_rows):
                    if col_idx < len(row_line) and row_line[col_idx] == ']':
                        punch_code |= 1 << (11 - row_idx)
                
                # Look up the character for this code, defaulting to space.
                decoded_chars.append(CODE_TO_CHAR.get(punch_code, ' '))
            
            # Print the decoded line, stripping trailing spaces.
            print("".join(decoded_chars).rstrip())
            
        except (IOError, IndexError):
            break

def main():
    """Parses arguments and runs the encoder or decoder."""
    parser = argparse.ArgumentParser(
        description="Format input as punch cards, or decode them.",
        usage="%(prog)s [-dl] [string ...]"
    )
    parser.add_argument(
        '-d', '--decode',
        action='store_true',
        help='Decode punch card data from standard input.'
    )
    parser.add_argument(
        '-l', '--long',
        action='store_true',
        help='Create punch cards with 80 columns (default is 48).'
    )
    parser.add_argument(
        'strings',
        nargs='*', # Zero or more string arguments.
        help='Strings to encode. Reads from stdin if none are given.'
    )
    
    args = parser.parse_args()
    cols = 80 if args.long else 48

    if args.decode:
        decode_stream(cols)
    else:
        # Encode mode
        if args.strings:
            # Join all command-line arguments into one string.
            text_to_encode = " ".join(args.strings)
            print_cards(text_to_encode, cols)
        else:
            # Read from standard input line by line.
            for line in sys.stdin:
                print_cards(line.rstrip('\n'), cols)

if __name__ == "__main__":
    main()
