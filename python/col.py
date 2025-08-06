#!/usr/bin/env python3
"""
Name: col
Description: filter reverse line feeds from input
Author: Ronald J Kimball, rjk-perl@tamias.net (Original Perl Author)
License: perl
"""

import sys
import argparse
import fileinput

class ColumnProcessor:
    """
    A class to simulate a line printer, processing control characters
    and building an in-memory representation of the output.
    """
    def __init__(self, args):
        self.args = args
        self.buffer = [[]] # A 2D grid: list of rows, where each row is a list of columns
        self.row = 0
        self.col = 0
        self.max_row = 0

    def _ensure_row_exists(self, row_idx):
        """Make sure the buffer has enough rows to access the given index."""
        while len(self.buffer) <= row_idx:
            self.buffer.append([])

    def _add_char(self, char):
        """Adds a character to the buffer at the current cursor position."""
        self._ensure_row_exists(self.row)
        
        # Ensure the current row has enough columns
        while len(self.buffer[self.row]) <= self.col:
            self.buffer[self.row].append([])
            
        # -b (no backspacing) means we only store the last character at a position.
        if self.args.b:
            self.buffer[self.row][self.col] = [char]
        else:
            self.buffer[self.row][self.col].append(char)
            
        self.col += 1
        self.max_row = max(self.max_row, self.row)

    def process_stream(self, stream):
        """Phase 1: Read the input stream and build the internal buffer."""
        for line in stream:
            for char in line:
                if char == '\n': # Newline
                    self.col = 0
                    self.row += 1
                elif char == '\t': # Tab
                    self.col += 8 - (self.col % 8)
                elif char == '\b': # Backspace
                    self.col = max(0, self.col - 1)
                elif char == '\r': # Carriage Return
                    self.col = 0
                elif char == '\v': # Vertical Tab (reverse line feed)
                    self.row = max(0, self.row - 1)
                elif char >= ' ': # Printable character
                    self._add_char(char)
                # Other control characters are ignored, as per the original.

    def render_output(self):
        """Phase 2: Iterate through the buffer and print the formatted output."""
        max_cols = 0
        # Find the widest row in the buffer
        if self.max_row > 0:
            max_cols = max(len(r) for r in self.buffer[:self.max_row + 1] if r)

        for r_idx in range(self.max_row + 1):
            output_line = []
            if r_idx >= len(self.buffer):
                # This handles blank lines created by moving the cursor down.
                print()
                continue

            current_row = self.buffer[r_idx]
            for c_idx in range(max_cols):
                if c_idx < len(current_row) and current_row[c_idx]:
                    # Join overstruck characters with backspaces in between.
                    output_line.append('\b'.join(current_row[c_idx]))
                else:
                    output_line.append(' ')
            
            line_str = "".join(output_line).rstrip()
            
            # Intelligently convert runs of spaces back into tabs.
            if not self.args.x:
                # This regex finds runs of 2+ spaces that end on a tab boundary
                # and replaces them with the correct number of tabs and spaces.
                def tab_replacer(match):
                    start_col = match.start()
                    num_spaces = len(match.group(0))
                    num_tabs = 0
                    while start_col + num_tabs * 8 + 8 <= start_col + num_spaces:
                        num_tabs += 1
                    remaining_spaces = num_spaces - (num_tabs * 8)
                    return '\t' * num_tabs + ' ' * remaining_spaces
                
                # A simplified heuristic for tabbing
                line_str = re.sub(r' {2,}', lambda m: '\t' * (len(m.group(0)) // 8) + ' ' * (len(m.group(0)) % 8), line_str)

            print(line_str)

def main():
    """Parses arguments and orchestrates the processing."""
    # Note: Many original flags (-f, -p, -s, -t, -l) relate to obscure
    # terminal features and are simplified or omitted in this modern port.
    parser = argparse.ArgumentParser(
        description="Filter reverse line feeds and format text.",
        usage="%(prog)s [-bx] [file ...]"
    )
    parser.add_argument(
        '-b', action='store_true',
        help='Do not output backspaces; print only the last character at each position.'
    )
    parser.add_argument(
        '-x', action='store_true',
        help='Output multiple spaces instead of tabs.'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to process. Reads from stdin if none are given.'
    )
    
    args = parser.parse_args()

    processor = ColumnProcessor(args)
    
    try:
        # fileinput handles reading from stdin or a list of files seamlessly.
        with fileinput.input(files=args.files or ('-',), openhook=fileinput.hook_encoded("latin-1")) as f:
            processor.process_stream(f)
        
        processor.render_output()

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
