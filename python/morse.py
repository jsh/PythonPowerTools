#!/usr/bin/env python3
"""
Name: morse
Description: read morse and translate it to text
Author: Abigail, Michael Mikonos (Original Perl Authors)
License: perl
"""

import sys
import argparse
import fileinput
import re

# --- Morse Code Mappings ---
CHAR_TO_MORSE = {
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.', 'f': '..-.',
    'g': '--.', 'h': '....', 'i': '..', 'j': '.---', 'k': '-.-', 'l': '.-..',
    'm': '--', 'n': '-.', 'o': '---', 'p': '.--.', 'q': '--.-', 'r': '.-.',
    's': '...', 't': '-', 'u': '..-', 'v': '...-', 'w': '.--', 'x': '-..-',
    'y': '-.--', 'z': '--..', '.': '.-.-.-', ',': '--..--', ':': '---...',
    '?': '..--..', "'": '.----.', '-': '-....-', '/': '-..-.', '(': '-.--.',
    ')': '-.--.-', '"': '.-..-.', '=': '-...-', ';': '-.-.-.', '+': '.-.-.',
    '@': '.--.-.', '_': '..--.-'
}
# Create the reverse mapping for decoding automatically.
MORSE_TO_CHAR = {v: k for k, v in CHAR_TO_MORSE.items()}

DIT_DAW_MAP = {'dit': '.', 'daw': '-'}
MORSE_TO_DIT_DAW_MAP = {'.': 'dit', '-': 'daw'}

# --- Core Translation Functions ---

def encode_dot_dash(text: str):
    """Encodes a string of text into dot/dash Morse code."""
    for char in text.lower():
        if char in (' ', '\n'):
            print()
        elif char in CHAR_TO_MORSE:
            print(CHAR_TO_MORSE[char])

def decode_dot_dash(morse: str):
    """Decodes a string of dot/dash Morse code into text."""
    output = []
    for word in morse.split():
        if word not in MORSE_TO_CHAR:
            raise ValueError(f"'{word}' is not a valid morse code token")
        output.append(MORSE_TO_CHAR[word])
    print("".join(output))

def encode_dit_daw(text: str):
    """Encodes a string of text into dit/daw Morse code."""
    for char in text.lower():
        if char in (' ', '\n'):
            print()
        elif char in CHAR_TO_MORSE:
            morse_code = CHAR_TO_MORSE[char]
            dit_daw_words = [MORSE_TO_DIT_DAW_MAP[c] for c in morse_code]
            print(" ".join(dit_daw_words))

def decode_dit_daw(morse: str):
    """Decodes a string of dit/daw Morse code into text."""
    output = []
    # Split by commas or newlines to separate characters
    for char_group in re.split(r'[,\n]', morse):
        morse_code = ""
        # Split by whitespace to separate dits and daws
        for token in char_group.strip().split():
            if token not in DIT_DAW_MAP:
                raise ValueError(f"'{token}' is not a valid morse code token")
            morse_code += DIT_DAW_MAP[token]
        
        if morse_code:
            if morse_code not in MORSE_TO_CHAR:
                raise ValueError(f"'{morse_code}' is not a valid morse code sequence")
            output.append(MORSE_TO_CHAR[morse_code])
    print("".join(output))

def main():
    """Parses arguments and dispatches to the correct translator."""
    parser = argparse.ArgumentParser(
        description="Translate text to/from Morse code.",
        usage="%(prog)s [-frs] [text... or file...]"
    )
    parser.add_argument('-f', '--files', action='store_true',
                        help='Treat arguments as files instead of strings.')
    parser.add_argument('-r', '--reverse', action='store_true',
                        help='Decode Morse to text instead of encoding.')
    parser.add_argument('-s', '--short', action='store_true',
                        help='Use short-form Morse (dots/dashes).')
    parser.add_argument('data', nargs='*', help="The string or files to process.")

    args = parser.parse_args()

    # --- 1. Gather Input ---
    # The input is either from files/stdin or from command-line arguments.
    if args.files:
        # Use fileinput to handle reading from files or stdin seamlessly.
        input_text = "".join(fileinput.input(files=args.data or ('-',)))
    else:
        input_text = " ".join(args.data)
        
    # --- 2. Dispatch to the Correct Function ---
    try:
        if args.reverse: # Decoding
            if args.short:
                decode_dot_dash(input_text)
            else:
                decode_dit_daw(input_text)
        else: # Encoding
            if args.short:
                encode_dot_dash(input_text)
            else:
                encode_dit_daw(input_text)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
