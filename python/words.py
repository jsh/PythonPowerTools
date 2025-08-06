#!/usr/bin/env python3
"""
Name: words
Description: find words which can be made from a string of letters
Author: Ronald J Kimball, rjk-perl@tamias.net (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
from collections import Counter

def main():
    """Parses arguments and finds all possible words from a letter set."""
    parser = argparse.ArgumentParser(
        description="Find all words in a wordlist that can be made from a string of letters.",
        usage="%(prog)s [-w <word-file>] [-m <min-length>] <letters>"
    )
    parser.add_argument(
        '-w', '--wordlist',
        help="Path to an alternate word list file."
    )
    parser.add_argument(
        '-m', '--min-length',
        type=int,
        default=0,
        help="The minimum length of words to find."
    )
    parser.add_argument(
        'letters',
        help="The string of available letters."
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Determine Wordlist Path ---
    wordlist_path = args.wordlist
    if not wordlist_path:
        # Default to 'wordlist.txt' in the same directory as the script.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        wordlist_path = os.path.join(script_dir, "wordlist.txt")

    # --- 2. Prepare Letter Counts ---
    # Sanitize the input letters: make lowercase and keep only a-z.
    sanitized_letters = "".join(filter(str.isalpha, args.letters.lower()))
    # Use collections.Counter for efficient letter frequency counting.
    available_letters = Counter(sanitized_letters)

    # --- 3. Process the Wordlist ---
    try:
        if os.path.isdir(wordlist_path):
            print(f"{program_name}: '{wordlist_path}' is a directory", file=sys.stderr)
            sys.exit(1)
            
        with open(wordlist_path, 'r') as f:
            for word in f:
                word = word.strip().lower()
                
                # --- Check if the word is a candidate ---
                
                # 1. Check minimum length.
                if len(word) < args.min_length:
                    continue
                
                # 2. Count letters in the candidate word.
                word_counts = Counter(word)
                
                # 3. Check if the word can be formed from the available letters.
                # This is the core logic: for every letter in the word, check that
                -                # the count of that letter is less than or equal to the count
                # available from the input string.
                can_form_word = True
                for char, count in word_counts.items():
                    if available_letters[char] < count:
                        can_form_word = False
                        break
                
                if can_form_word:
                    # The original word from the file (with original case)
                    # should be printed, not the lowercased version.
                    print(word.strip())

    except FileNotFoundError:
        print(f"{program_name}: unable to open '{wordlist_path}': No such file or directory", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"{program_name}: failed to read '{wordlist_path}': {e.strerror}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
