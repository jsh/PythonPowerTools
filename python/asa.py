#!/usr/bin/env python3
"""
Name: asa
Description: interpret ASA/FORTRAN carriage-controls
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl
"""

import sys
import os
import fileinput

def main():
    """
    Parses arguments and processes files to interpret ASA carriage controls.
    """
    program_name = os.path.basename(sys.argv[0])
    exit_status = 0

    # The original script does not accept any options, only file arguments.
    if any(arg.startswith('-') for arg in sys.argv[1:]):
        print(f"usage: {program_name} [file ...]", file=sys.stderr)
        sys.exit(2) # Exit with 2 for bad arguments, as per original's docs

    # This dictionary maps the ASA control characters to their output prefixes.
    prefix_map = {
        '1': "\f",      # Formfeed
        '+': "\r",      # Overprint (carriage return without line feed)
        '0': "\n\n",    # Double space
        '-': "\n\n\n",  # Triple space (IBM extension)
    }

    try:
        # The fileinput module handles reading from files in sys.argv[1:]
        # or from standard input if no files are provided.
        with fileinput.input(files=sys.argv[1:] or ('-',)) as f:
            for line in f:
                # On the first line of each new file, check if it's a directory.
                if f.isfirstline() and fileinput.filename() != '<stdin>':
                    if os.path.isdir(fileinput.filename()):
                        # The original script skips directories, so we do the same.
                        f.nextfile()
                        continue
                
                # Remove the trailing newline for processing, like Perl's chomp.
                line = line.rstrip('\n')
                
                # An empty line is treated as a single newline.
                if not line:
                    print("\n", end='')
                    continue
                
                control_char = line[0]
                content = line[1:]
                
                # Get the prefix from the map. A space or any other character
                # defaults to a single newline, which advances to the next line.
                prefix = prefix_map.get(control_char, "\n")
                
                # Print the prefix and the content without an additional newline.
                print(prefix + content, end='')

    except FileNotFoundError as e:
        print(f"{program_name}:
