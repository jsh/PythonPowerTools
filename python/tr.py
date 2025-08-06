#!/usr/bin/env python3
"""
Name: tr
Description: translate or delete characters
Author: Tom Christiansen, tchrist@perl.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import codecs

def expand_char_set(s: str) -> str:
    """
    Expands a tr-style string with ranges (a-z) and backslash escapes.
    """
    # First, handle backslash escapes like \n, \t, \012, \x0a
    # The 'unicode_escape' codec is perfect for this.
    try:
        expanded = codecs.decode(s, 'unicode_escape')
    except UnicodeDecodeError as e:
        print(f"Error: Invalid escape sequence in string '{s}': {e}", file=sys.stderr)
        sys.exit(1)

    # Second, handle a-z style ranges
    # A regex finds all valid ranges (e.g., a-z, 0-9, A-C)
    def replacer(match):
        start, end = ord(match.group(1)), ord(match.group(2))
        if start > end: # Invalid range like z-a, return original
            return match.group(0)
        return "".join(chr(i) for i in range(start, end + 1))
    
    # Repeatedly apply until no more ranges are found.
    # This handles overlapping cases like 'a-d-g' -> 'abcd-g' -> 'abcdefg'
    while re.search(r'(.)-(.)', expanded):
         expanded = re.sub(r'(.)-(.)', replacer, expanded)
            
    return expanded

def main():
    """Main function to parse args and run the tr logic."""
    parser = argparse.ArgumentParser(
        description="Translate, squeeze, and/or delete characters from standard input.",
        usage="%(prog)s [-Ccds] string1 [string2]"
    )
    parser.add_argument('-C', '-c', dest='complement', action='store_true',
                        help='Complement the set of characters in string1.')
    parser.add_argument('-d', '--delete', action='store_true',
                        help='Delete characters in string1 instead of translating.')
    parser.add_argument('-s', '--squeeze-repeats', action='store_true',
                        help='Squeeze repeated output characters.')
    parser.add_argument('strings', nargs='*')

    args = parser.parse_args()
    
    # --- 1. Argument Validation ---
    if not (1 <= len(args.strings) <= 2):
        parser.error("missing or extra operand.")
    if args.delete and not args.squeeze_repeats and len(args.strings) != 1:
        parser.error("extra operand for -d only.")
        
    str1_raw = args.strings[0]
    str2_raw = args.strings[1] if len(args.strings) > 1 else ''

    # --- 2. Expand Character Sets ---
    from_set = expand_char_set(str1_raw)
    to_set = expand_char_set(str2_raw)

    # --- 3. Handle Options ---
    # Handle -c (complement)
    if args.complement:
        universe = {chr(i) for i in range(256)}
        from_set_chars = set(from_set)
        from_set = "".join(sorted([c for c in universe if c not in from_set_chars]))

    # Handle string2 padding (if not in pure delete mode)
    if not args.delete:
        if not to_set:
            to_set = from_set # Replicate from_set for counting/squeezing
        if len(to_set) < len(from_set):
            to_set += to_set[-1] * (len(from_set) - len(to_set))

    # --- 4. Build Translation and Deletion Tables ---
    delete_chars = ""
    if args.delete:
        # Delete any character in from_set that does not have a
        # corresponding character in to_set.
        unmapped_len = len(from_set) - len(to_set)
        if unmapped_len > 0:
            delete_chars = from_set[-unmapped_len:]
    
    # Create the translation table for str.translate()
    translation_table = str.maketrans(from_set, to_set, delete_chars)
    
    # --- 5. Process Input ---
    try:
        for line in sys.stdin:
            # Step 1: Translate and/or delete characters
            translated_line = line.translate(translation_table)

            # Step 2: Squeeze repeated characters if -s is enabled
            if args.squeeze_repeats:
                # We only squeeze characters that are in the output set
                chars_to_squeeze = set(to_set)
                if not chars_to_squeeze: continue

                squeezed = []
                last_char = None
                for char in translated_line:
                    if char in chars_to_squeeze and char == last_char:
                        continue
                    squeezed.append(char)
                    last_char = char
                print("".join(squeezed), end='')
            else:
                print(translated_line, end='')

    except (IOError, KeyboardInterrupt):
        sys.stderr.close() # Silence errors on broken pipe or Ctrl+C
    
    sys.exit(0)

if __name__ == "__main__":
    main()
