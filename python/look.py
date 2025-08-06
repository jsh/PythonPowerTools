#!/usr/bin/env python3
"""
Name: look
Description: find lines in a sorted list
Author: Tom Christiansen, tchrist@perl.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re

# Define exit codes for clarity
EX_FOUND = 0
EX_NOTFOUND = 1
EX_FAILURE = 2

def squish(text: str, fold_case: bool, dict_order: bool) -> str:
    """
    Applies transformations to a string for comparison, based on the -f and -d flags.
    """
    if fold_case:
        text = text.lower()
    if dict_order:
        # 'Dictionary' order ignores anything that isn't a letter, number, or whitespace.
        text = re.sub(r'[^\w\s]', '', text)
    return text

def binary_search_prefix(lines: list, search_key: str, key_func) -> int:
    """
    Performs a binary search on a list of lines to find the first line
    that starts with the given search_key, after transformation by key_func.
    
    Returns the index of the first match, or -1 if no match is found.
    """
    low, high = 0, len(lines) - 1
    found_index = -1

    while low <= high:
        mid = (low + high) // 2
        # Apply the same transformation to the line from the file
        mid_key = key_func(lines[mid])

        if mid_key.startswith(search_key):
            # We found a match, but it might not be the *first* one.
            # Store it and continue searching in the lower half of the list.
            found_index = mid
            high = mid - 1
        elif mid_key < search_key:
            low = mid + 1
        else: # mid_key > search_key
            high = mid - 1
            
    return found_index

def main():
    """Parses arguments and orchestrates the dictionary search."""
    parser = argparse.ArgumentParser(
        description="Display lines beginning with a given string in a sorted file.",
        usage="%(prog)s [-df] string [file]"
    )
    parser.add_argument(
        '-d', dest='dict_order', action='store_true',
        help="Dictionary order: ignore non-alphanumeric characters."
    )
    parser.add_argument(
        '-f', dest='fold_case', action='store_true',
        help="Fold case: compare letters case-insensitively."
    )
    parser.add_argument('search_string', help="The string to search for.")
    parser.add_argument('file', nargs='?', help="The file to search. Uses system dictionary if not specified.")

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- Determine which file to use and set options ---
    filepath = args.file
    if not filepath:
        # If no file is specified, use the system dictionary and force -d and -f flags.
        args.dict_order = True
        args.fold_case = True
        default_dicts = ["/usr/share/dict/words", "/usr/dict/words"]
        for d in default_dicts:
            if os.path.isfile(d) and os.access(d, os.R_OK):
                filepath = d
                break
        if not filepath:
            print(f"{program_name}: No default dictionaries available in {default_dicts}", file=sys.stderr)
            sys.exit(EX_FAILURE)

    # --- Read file and perform search ---
    try:
        with open(filepath, 'r', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{program_name}: can't open '{filepath}': No such file or directory", file=sys.stderr)
        sys.exit(EX_FAILURE)
    except IsADirectoryError:
        print(f"{program_name}: '{filepath}' is a directory", file=sys.stderr)
        sys.exit(EX_FAILURE)

    # Prepare the search key by applying the same transformations.
    search_key = squish(args.search_string, args.fold_case, args.dict_order)
    
    # The key function to be used for all comparisons.
    key_func = lambda line: squish(line, args.fold_case, args.dict_order)

    start_index = binary_search_prefix(lines, search_key, key_func)
    
    if start_index == -1:
        sys.exit(EX_NOTFOUND)

    # --- Print all matching lines ---
    match_found = False
    for i in range(start_index, len(lines)):
        line = lines[i]
        line_key = key_func(line)
        
        if line_key.startswith(search_key):
            # Print the original, untransformed line.
            print(line, end='')
            match_found = True
        else:
            # Since the file is sorted, we can stop as soon as we find a non-match.
            break
            
    sys.exit(EX_FOUND if match_found else EX_NOTFOUND)

if __name__ == "__main__":
    main()
