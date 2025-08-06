#!/usr/bin/env python3
"""
Name: deroff
Description: strip troff, eqn and tbl sequences from text
Author: Nathan Scott Thompson (Original Perl Author)
License: gpl
"""

import sys
import os
import argparse
import re
import fileinput

def clean_troff_line(line: str) -> str:
    """
    Applies a series of regex substitutions to strip troff commands from a line.
    """
    # This sequence of substitutions is a direct translation of the original script.
    
    # Strip macro lines (simple ones)
    line = re.sub(r"^[.']\s*[A-Z]\w*\s*", '', line)
    # Ditch all other control requests that remain
    if re.match(r"^[.']", line):
        return ""

    line = re.sub(r'\\".*', '', line)             # strip comments
    line = re.sub(r'\\\((f[ifl])', r'\1', line)   # replace fi, ff, fl ligatures
    line = re.sub(r'\\\(F([il])', r'ff\1', line)  # replace ffi, ffl ligatures
    line = re.sub(r'\\0', ' ', line)              # replace \0 with space
    line = re.sub(r'\\\((hy|mi|em)', '-', line)   # replace \(hy, \(mi, \(em with dash
    line = re.sub(r'\\\.\.', ' ', line)           # replace all others with space

    line = re.sub(r'\\[*fgns][+-]?\(..', '', line)  # remove \f(xx etc.
    line = re.sub(r'\\[*fgn][+-]?.', '', line)      # remove \fx etc.
    line = re.sub(r'\\s[+-]?\d+', '', line)         # remove \sN
    line = re.sub(r"\\[bCDhHlLNoSvwxX]'[^']*'", '', line) # remove those with quoted arguments
    line = re.sub(r"\\[e'`|^&%acdprtu{}]", '', line) # remove one character escapes
    line = re.sub(r'\\[$kz].', '', line)            # remove \$x, \kx, \zx
    line = re.sub(r'\\$', '', line)                 # remove line continuation

    line = re.sub(r'\\(.)', r'\1', line)            # save all other escaped characters
    
    return line

def process_stream(files_to_process, words_only_mode):
    """
    Reads from a stream (files or stdin), processes each line, and prints the result.
    """
    in_tbl_block = False
    in_eqn_block = False
    
    try:
        # fileinput handles reading from files in the list or from stdin if the list is empty.
        with fileinput.input(files=files_to_process or ('-',)) as f:
            for line in f:
                # --- Block Skipping Logic ---
                if re.match(r"^[.']\s*TS", line): in_tbl_block = True
                if re.match(r"^[.']\s*TE", line): in_tbl_block = False; continue
                if in_tbl_block: continue

                if re.match(r"^[.']\s*EQ", line): in_eqn_block = True
                if re.match(r"^[.']\s*EN", line): in_eqn_block = False; continue
                if in_eqn_block: continue

                # --- Line Cleaning Logic ---
                cleaned_line = clean_troff_line(line)
                
                # --- Output Logic ---
                if words_only_mode:
                    # Find all words and print them one per line.
                    words = re.findall(r"\b[A-Za-z][A-Za-z\d']*[A-Za-z\d]\b", cleaned_line)
                    for word in words:
                        print(word)
                else:
                    # Print the full, cleaned line.
                    print(cleaned_line, end='')

    except FileNotFoundError as e:
        print(f"{sys.argv[0]}: Can't open '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Parses command-line arguments and orchestrates the deroffing process."""
    parser = argparse.ArgumentParser(
        description="Strip troff, eqn, and tbl sequences from text.",
        usage="%(prog)s [-w] [file]..."
    )
    parser.add_argument(
        '-w', '--words',
        action='store_true',
        help='Output only words, one per line.'
    )
    parser.add_argument(
        'files',
        nargs='*', # Zero or more file arguments.
        help='Files to process. Reads from stdin if none are given.'
    )

    args = parser.parse_args()
    
    # Filter out any arguments that are directories
    files_to_process = [f for f in args.files if not os.path.isdir(f)]

    process_stream(files_to_process, args.words)
    sys.exit(0)

if __name__ == "__main__":
    main()
