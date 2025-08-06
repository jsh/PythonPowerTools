#!/usr/bin/env python3

"""
Name: spell
Description: scan a file for misspelled words
Author: Greg Snow, snow@biostat.washington.edu
License: perl
"""

import sys
import os
import re
from collections import defaultdict
from itertools import chain

EX_SUCCESS = 0
EX_FAILURE = 1
DICT_FILE = '/usr/dict/words'
MAX_LINES_BEFORE_MORE = 20

def usage():
    """Prints usage message and exits."""
    program_name = os.path.basename(sys.argv[0])
    sys.stderr.write(f"usage: {program_name} [-d dict] [-c|-x] [-v] [-i] [+extra_list] [file ...]\n")
    sys.exit(EX_FAILURE)

def close_matches(word, words_set):
    """
    Finds close matches to a given word in the dictionary.
    A close match is a word in the dictionary that can be obtained by
    a single deletion, addition, change, or transposition of adjacent characters.
    """
    word_len = len(word)
    close_words = set()

    # Deletions
    for i in range(word_len):
        modified_word = word[:i] + word[i+1:]
        if modified_word in words_set:
            close_words.add(modified_word)

    # Additions
    for i in range(word_len + 1):
        for char_code in range(ord('a'), ord('z') + 1):
            char = chr(char_code)
            modified_word = word[:i] + char + word[i:]
            if modified_word in words_set:
                close_words.add(modified_word)

    # Changes
    for i in range(word_len):
        prefix = word[:i]
        suffix = word[i+1:]
        for char_code in range(ord('a'), ord('z') + 1):
            char = chr(char_code)
            modified_word = prefix + char + suffix
            if modified_word in words_set:
                close_words.add(modified_word)

    # Transpositions (swaps)
    for i in range(word_len - 1):
        modified_word = word[:i] + word[i+1] + word[i] + word[i+2:]
        if modified_word in words_set:
            close_words.add(modified_word)

    return sorted(list(close_words))

def check_suffixes(word, words_set):
    """
    Checks if a word is a valid dictionary word with a common suffix removed.
    Returns a formatted string describing the change, or None if no match is found.
    """
    # This logic is based on the Perl script's implementation
    # which is quite specific and handles only a few cases.

    # "'s" suffix
    if word.endswith("'s"):
        base_word = word[:-2]
        if base_word in words_set:
            return f'"{word}" = "{base_word}" + "\'s"'

    # number-word format
    match = re.match(r'^(\d+-?)(\w+)$', word)
    if match and match.group(2) in words_set:
        return f'"{word}" = "{match.group(1)}" + "{match.group(2)}"'

    # word-word format
    match = re.match(r'^(\w+)-(\w+)$', word)
    if match and match.group(1) in words_set and match.group(2) in words_set:
        return f'"{word}" = "{match.group(1)}" + "-" + "{match.group(2)}"'

    return None

def main():
    """Main function to run the spell checker."""
    program_name = os.path.basename(sys.argv[0])
    
    # Process command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Scan a file for misspelled words.')
    parser.add_argument('-d', '--dict', dest='dictionary', help='Use FILE as the dictionary instead of the default.')
    parser.add_argument('-c', '-x', '--close', action='store_true', dest='check_close', help='Check the dictionary for "close" matches.')
    parser.add_argument('-v', '--verbose', action='store_true', dest='show_suffixes', help='Show suffix expansion.')
    parser.add_argument('-i', '--interactive', action='store_true', dest='interactive', help='Use interactively.')
    parser.add_argument('+extra_list', nargs='*', help='Add an extra dictionary file.')
    parser.add_argument('files', nargs='*', default=[sys.stdin], help='Files to check.')
    
    args = parser.parse_args()

    # Load dictionary words
    dict_files = []
    if args.dictionary:
        dict_files.append(args.dictionary)
    else:
        dict_files.append(DICT_FILE)

    if args.extra_list:
        for extra_file in args.extra_list:
            dict_files.append(extra_file)

    words = set()
    for d_file in dict_files:
        try:
            with open(d_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    words.add(line.strip().lower())
        except FileNotFoundError:
            sys.stderr.write(f"{program_name}: could not open dictionary <{d_file}>: No such file or directory\n")
            sys.exit(EX_FAILURE)
        except IOError as e:
            sys.stderr.write(f"{program_name}: could not open dictionary <{d_file}>: {e}\n")
            sys.exit(EX_FAILURE)
    
    if not words:
        sys.stderr.write(f"{program_name}: word list was empty\n")
        sys.exit(EX_FAILURE)

    # Custom pager for interactive mode
    line_counter = 0
    def more(text):
        nonlocal line_counter
        if args.interactive:
            if line_counter >= MAX_LINES_BEFORE_MORE:
                sys.stdout.write("----- MORE -----")
                _ = sys.stdin.readline()
                sys.stdout.write("\b" * 16)
                line_counter = 0
            line_counter += text.count('\n') + 1
        sys.stdout.write(text)

    def check_words(word_list_to_check):
        """Checks words and prints results."""
        word_list_to_check = sorted(list(word_list_to_check))
        
        # Check for misspelled words and suffix matches
        misspelled_words = []
        suffix_matches = []
        for word_to_check in word_list_to_check:
            if word_to_check not in words:
                suffix_match = check_suffixes(word_to_check, words)
                if suffix_match and args.show_suffixes:
                    suffix_matches.append(suffix_match)
                else:
                    misspelled_words.append(word_to_check)

        if args.interactive:
            found_words = [w for w in word_list_to_check if w in words]
            if found_words:
                more(f'Found: {", ".join(found_words)}\n')
            
            if args.show_suffixes and suffix_matches:
                more("\nClose Matches:\n")
                for s in suffix_matches:
                    more(f"  {s}\n")

            if misspelled_words:
                more("\nNot Found:\n\n")
                for word in misspelled_words:
                    more(f"    {word}.\n")
                    if args.check_close:
                        more("-----\n")
                        for close_word in close_matches(word, words):
                            more(f"    {close_word}\n")
                        more("\n")
        else:  # Non-interactive mode
            if args.show_suffixes and suffix_matches:
                for s in suffix_matches:
                    sys.stdout.write(f"{s}\n")
                sys.stdout.write("\n-----\n\n")
            
            if misspelled_words:
                for word in misspelled_words:
                    sys.stdout.write(f"{word}\n")
                    if args.check_close:
                        sys.stdout.write("-----\n")
                        sys.stdout.write("  " + "\n  ".join(close_matches(word, words)) + "\n\n")

    # Main loop for reading and checking words
    if args.interactive:
        print("Word(s): ", end="", flush=True)

    words_to_check = set()
    input_files = args.files if not args.interactive else [sys.stdin]
    
    try:
        for f in input_files:
            if isinstance(f, str):
                file_handle = open(f, 'r', encoding='utf-8', errors='ignore')
            else:
                file_handle = f

            for line in file_handle:
                line = line.strip().lower()
                if args.interactive and not line:
                    break
                
                # Split line into words and strip punctuation
                line_words = re.findall(r'\b[a-z]+\b', line)
                for word in line_words:
                    words_to_check.add(word)

                if args.interactive:
                    check_words(words_to_check)
                    words_to_check.clear()
                    print("Word(s): ", end="", flush=True)
            
            if file_handle != sys.stdin:
                file_handle.close()

    except (KeyboardInterrupt, EOFError):
        pass
    
    if not args.interactive:
        check_words(words_to_check)

    sys.exit(EX_SUCCESS)

if __name__ == "__main__":
    main()
