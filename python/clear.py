#!/usr/bin/env python3
"""
Name: clear
Description: clear the screen
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl

A Python port of the 'clear' utility.

This script clears the terminal screen by sending the appropriate
control sequence for the user's terminal. It determines the sequence
by querying the system's terminal database.
"""

import os
import sys
import platform

def main():
    """Clears the terminal screen in a cross-platform way."""
    # Determine the operating system.
    current_os = platform.system()

    # --- Windows ---
    if current_os == "Windows":
        os.system('cls')
    
    # --- Linux, macOS, and other Unix-like systems ---
    else:
        try:
            # The 'curses' library is Python's interface to the terminfo
            # database, which is the modern equivalent of termcap.
            import curses
            curses.setupterm()
            
            # We get the byte sequence for the 'clear' capability.
            clear_sequence = curses.tigetstr('clear')
            
            # Write the sequence directly to the standard output stream.
            # This is more efficient than calling an external command.
            if clear_sequence:
                # We decode the byte sequence using the terminal's encoding.
                sys.stdout.write(clear_sequence.decode(sys.stdout.encoding))
            else:
                # If 'clear' isn't in the db, use a common ANSI escape code.
                # '\033[H' moves cursor to home, '\033[J' clears the screen.
                sys.stdout.write('\033[H\033[J')

        except (ImportError, curses.error):
            # If the curses library isn't available or fails (e.g., not in
            # a real terminal), fall back to calling the 'clear' command.
            os.system('clear')

if __name__ == "__main__":
    main()
