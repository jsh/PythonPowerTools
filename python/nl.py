#!/usr/bin/env python3
"""
Name: nl
Description: line numbering filter
Author: jul, kaldor@cpan.org (Original Perl Author)
License: artistic2
"""

import sys
import os
import argparse
import re
import fileinput
from enum import Enum

class Section(Enum):
    HEADER = 0
    BODY = 1
    FOOTER = 2

class NumberingStyle:
    """A class to parse and hold numbering style options like 't' or 'pa-z'."""
    def __init__(self, style_str):
        self.style = style_str[0]
        self.pattern = None
        if self.style in ('p', 'e'):
            self.pattern = re.compile(style_str[1:])
            
        if self.style not in ('a', 't', 'n', 'p', 'e'):
            raise argparse.ArgumentTypeError(f"invalid numbering style: '{self.style}'")

class NLProcessor:
    """Encapsulates the state and logic for the nl command."""
    def __init__(self, args):
        self.args = args
        self.line_number = args.start_num
        self.section = Section.BODY
        
        # Determine the printf-style format string for the number
        if args.format == 'ln': # left-justified
            self.num_format = f"%-{args.width}d"
        elif args.format == 'rz': # right-justified, zero-padded
            self.num_format = f"%0{args.width}d"
        else: # 'rn', right-justified (default)
            self.num_format = f"%{args.width}d"
            
        # Compile delimiter regex
        self.delim1 = re.escape(args.delimiters[0])
        self.delim2 = re.escape(args.delimiters[1]) if len(args.delimiters) > 1 else self.delim1
        self.delim_pattern = re.compile(f"^({self.delim1})({self.delim2})?({self.delim2})?$")
        
    def process_stream(self, stream):
        """Processes an entire input stream line by line."""
        for line in stream:
            self._process_line(line)

    def _process_line(self, line):
        """Processes a single line of input."""
        match = self.delim_pattern.match(line.rstrip('\n'))

        # Check if the line is a section delimiter
        if match:
            d1, d2, d3 = match.groups()
            new_section = self.section
            if d3: # Three delimiters starts a header
                new_section = Section.HEADER
            elif d2: # Two delimiters starts a body
                new_section = Section.BODY
            elif d1: # One delimiter starts a footer
                new_section = Section.FOOTER

            # Reset line number for a new page if not in -p (no_restart) mode
            if not self.args.no_restart and new_section.value <= self.section.value:
                self.line_number = self.args.start_num
            
            self.section = new_section
            # Don't print the delimiter lines themselves
            return

        # --- This is a regular line, apply numbering rules ---
        
        # Get the numbering style for the current section
        if self.section == Section.HEADER: style_obj = self.args.header_style
        elif self.section == Section.FOOTER: style_obj = self.args.footer_style
        else: style_obj = self.args.body_style

        line_should_be_numbered = False
        if style_obj.style == 'a': # all lines
            line_should_be_numbered = True
        elif style_obj.style == 't': # non-empty lines
            line_should_be_numbered = bool(line.strip())
        elif style_obj.style == 'p': # lines matching pattern
            line_should_be_numbered = bool(style_obj.pattern.search(line))
        elif style_obj.style == 'e': # lines NOT matching pattern
            line_should_be_numbered = not bool(style_obj.pattern.search(line))
        # 'n' (none) is the default if no other condition is met

        if line_should_be_numbered:
            number_str = self.num_format % self.line_number
            self.line_number += self.args.increment
        else:
            number_str = ' ' * self.args.width
            
        print(f"{number_str}{self.args.separator}{line}", end='')

def main():
    """Parses arguments and orchestrates the line numbering process."""
    parser = argparse.ArgumentParser(
        description="A line numbering filter.", add_help=False
    )
    # Use a custom help flag to avoid conflicts with -h option
    parser.add_argument('-h', '--help', action='help', help='Show this help message and exit.')
    
    parser.add_argument('-b', dest='body_style', type=NumberingStyle, default=NumberingStyle('t'),
                        help="Numbering style for body sections ('a', 't', 'n', 'pexpr'). Default is 't'.")
    parser.add_argument('-d', dest='delimiters', default='\\:',
                        help="Delimiters for logical page sections (default: '\\:').")
    parser.add_argument('-f', dest='footer_style', type=NumberingStyle, default=NumberingStyle('n'),
                        help="Numbering style for footer sections. Default is 'n'.")
    parser.add_argument('--h', dest='header_style', type=NumberingStyle, default=NumberingStyle('n'),
                        help="Numbering style for header sections. Default is 'n'.")
    parser.add_argument('-i', dest='increment', type=int, default=1, help="Line number increment (default: 1).")
    parser.add_argument('-n', dest='format', choices=['ln', 'rn', 'rz'], default='rn',
                        help="Number format: ln(left), rn(right), rz(right-zero) (default: 'rn').")
    parser.add_argument('-p', dest='no_restart', action='store_true', help="Do not restart numbering at logical pages.")
    parser.add_argument('-s', dest='separator', default='\t', help="Separator between number and text (default: TAB).")
    parser.add_argument('-v', dest='start_num', type=int, default=1, help="Starting line number (default: 1).")
    parser.add_argument('-w', dest='width', type=int, default=6, help="Width of the number field (default: 6).")
    
    parser.add_argument('file', nargs='?', help="Input file (reads from stdin if not provided).")
    
    args = parser.parse_args()

    # --- Argument Validation ---
    if len(args.delimiters) > 2:
        parser.error("delimiter string may not be more than 2 characters long.")
    if args.width <= 0:
        parser.error("invalid line number field width.")

    # --- Process Input ---
    try:
        processor = NLProcessor(args)
        # Use fileinput to handle reading from a file or stdin
        processor.process_stream(fileinput.input(files=[args.file] if args.file else ('-',)))
    except FileNotFoundError as e:
        print(f"{os.path.basename(sys.argv[0])}: '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    except re.error as e:
        print(f"{os.path.basename(sys.argv[0])}: invalid regular expression: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
