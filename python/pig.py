#!/usr/bin/env python3
"""
Name: pig
Description: reformat input as Pig Latin
Author: Jonathan Feinberg, jdf@pobox.com (Original Perl Author)
License: perl
"""

import sys
import re
import argparse

__version__ = "1.0"
VOWELS = "aeiou"

def translate_word_to_pig_latin(word: str) -> str:
    """
    Translates a single English word into Pig Latin, preserving its case.
    """
    if not word:
        return ""

    # 1. Remember the original case of the word
    is_init_caps = word[0].isupper() and word[1:].islower()
    is_all_caps = word.isupper()
    
    # 2. Find the position of the first vowel
    first_vowel_pos = -1
    for i, char in enumerate(word):
        if char.lower() in VOWELS:
            first_vowel_pos = i
            break
            
    # 3. Apply the appropriate Pig Latin rule
    if first_vowel_pos == 0:
        # Rule for words starting with a vowel: add "way"
        pig_latin_word = word + 'way'
    elif first_vowel_pos > 0:
        # Rule for words starting with consonants: move consonants to the end and add "ay"
        initial_consonants = word[:first_vowel_pos]
        rest_of_word = word[first_vowel_pos:]
        pig_latin_word = rest_of_word + initial_consonants + 'ay'
    else:
        # Rule for words with no vowels (e.g., "rhythm"): just add "ay"
        pig_latin_word = word + 'ay'

    # 4. Restore the original capitalization
    if is_all_caps:
        return pig_latin_word.upper()
    elif is_init_caps:
        return pig_latin_word.capitalize()
    else:
        return pig_latin_word.lower()

def replacer_function(match: re.Match) -> str:
    """
    A wrapper function designed to be passed to re.sub. It takes a regex
    match object and returns the translated version of the matched word.
    """
    original_word = match.group(0)
    return translate_word_to_pig_latin(original_word)

def main():
    """Parses arguments and runs the Pig Latin translation on standard input."""
    parser = argparse.ArgumentParser(
        description="Reads from stdin and writes it out in Pig Latin.",
        usage="%(prog)s" # This program reads from stdin and takes no arguments
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    # This will cause an error if any positional arguments are given.
    args = parser.parse_args()

    try:
        # Process standard input line by line
        for line in sys.stdin:
            # For each line, find all "words" (sequences of letters) and
            # replace them using our translation function. Using a function as
            # the replacement argument is the direct Python equivalent of
            # Perl's s/.../.../e (evaluate) substitution modifier.
            processed_line = re.sub(r'[a-zA-Z]+', replacer_function, line)
            
            # Print with autoflushing and without adding an extra newline
            # (since the original line already has one).
            print(processed_line, end='', flush=True)
            
    except KeyboardInterrupt:
        # Exit cleanly if the user presses Ctrl+C
        sys.exit(1)

if __name__ == "__main__":
    main()
