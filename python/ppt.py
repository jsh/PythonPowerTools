#!/usr/bin/env python3

"""
Name: ppt
Description: reformat input as paper tape
Author: Mark-Jason Dominus, mjd@plover.com
License:
"""

import sys

def main():
    """
    Reads from stdin and reformats the text as a visual paper tape.
    """
    # Print the top of the tape
    print("----------")

    # sys.stdin.read() "slurps" all input at once, which is equivalent
    # to the behavior of the Perl script's `-0777` command-line flag.
    input_data = sys.stdin.read()

    # Process each character from the input stream.
    for char in input_data:
        # 1. Convert the character to its 8-bit binary representation.
        # This is the Python equivalent of Perl's: unpack("B8", $_)
        # For example, 'A' becomes '01000001'.
        bits = format(ord(char), '08b')

        # 2. Reformat the bits into the 7-hole tape format, discarding
        # the first bit and adding a separator.
        # This replaces the Perl regex: s/.(....)(...)/$1.$2/
        # For example, '01000001' becomes '1000.001'.
        tape_section = f"{bits[1:5]}.{bits[5:8]}"

        # 3. Translate the binary '0' and '1' into tape representation.
        # A '1' becomes a hole ('o') and a '0' is blank space (' ').
        # This replaces Perl's transliteration: tr/01/ o/
        punched_tape = tape_section.replace('0', ' ').replace('1', 'o')

        # 4. Print the final formatted row.
        print(f"|{punched_tape}|")

    # Print the bottom of the tape
    print("----------")

if __name__ == "__main__":
    main()
