#!/usr/bin/env python3
"""
Name: unshar
Description: extract files from a shell archive
Author: Larry Wall, larry@wall.org (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import shlex
import base64
import binascii

class Unsharer:
    """
    A class to safely parse and extract files from a shell archive.
    """
    def __init__(self, args):
        self.args = args
        self.if_stack = [] # To handle if/else/fi logic
        self.env = os.environ.copy()

    def unshar_stream(self, stream):
        """Processes an entire input stream line by line."""
        # Skip header lines until a command is found
        for line in stream:
            if not line.startswith(('#', ':')):
                self._process_line(line, stream)
                break
        
        # Process the rest of the stream
        for line in stream:
            self._process_line(line, stream)

    def _process_line(self, line, stream):
        """Parses and executes a single line from the shar archive."""
        line = line.strip()
        if not line or line.startswith(('#', ':')):
            return

        # Handle if/else/fi control flow
        if line.startswith('if '):
            # This is a highly simplified 'if' that only handles `test -f`
            match = re.search(r'test\s+-f\s+(\S+)', line)
            if match:
                # If the file exists, the condition is true.
                self.if_stack.append(os.path.exists(self._sanitize_path(match.group(1))))
            else:
                self.if_stack.append(False) # Unsupported 'if' condition
            return
        elif line == 'else':
            if self.if_stack:
                self.if_stack[-1] = not self.if_stack[-1]
            return
        elif line == 'fi':
            if self.if_stack:
                self.if_stack.pop()
            return

        # If we are inside a false 'if' block, skip this line
        if self.if_stack and not self.if_stack[-1]:
            return

        # --- Command Dispatcher ---
        if line.startswith('echo '):
            if not self.args.quiet:
                print(line[5:], file=sys.stderr)
        elif line.startswith('mkdir '):
            self._handle_mkdir(line)
        elif '<<' in line:
            self._handle_heredoc(line, stream)
        # Add other simple command handlers here if needed

    def _sanitize_path(self, path):
        """
        Sanitizes a path to prevent directory traversal and absolute paths.
        Raises a ValueError if the path is insecure.
        """
        # Unquote the path
        path = shlex.split(path)[0]
        if '..' in path.split(os.pathsep) or os.path.isabs(path):
            raise ValueError(f"Insecure path detected: '{path}'")
        return path

    def _handle_mkdir(self, line):
        """Handles a 'mkdir' command."""
        try:
            # shlex.split handles quotes and options like -p
            parts = shlex.split(line)
            path_to_create = self._sanitize_path(parts[-1])
            # os.makedirs is equivalent to 'mkdir -p'
            os.makedirs(path_to_create, exist_ok=True)
        except (ValueError, IndexError, OSError) as e:
            if not self.args.quiet:
                print(f"Failed to process mkdir: {e}", file=sys.stderr)

    def _handle_heredoc(self, line, stream):
        """Handles commands with here-documents, like cat and sed."""
        parts = shlex.split(line)
        
        # Find the here-doc marker (e.g., 'EOF')
        try:
            heredoc_index = parts.index('<<')
            end_marker = parts[heredoc_index + 1]
        except (ValueError, IndexError):
            return

        # --- Handle uudecode ---
        if 'uudecode' in parts:
            # Read the here-document content
            content_lines = []
            for doc_line in stream:
                if doc_line.strip() == end_marker:
                    break
                content_lines.append(doc_line)
            
            uudecode_content = "".join(content_lines)
            # Find the 'begin <mode> <filename>' header
            header_match = re.search(r'begin\s+\d+\s+(\S+)', uudecode_content)
            if header_match:
                filename = self._sanitize_path(header_match.group(1))
                try:
                    decoded_data = binascii.a2b_uu(uudecode_content)
                    if not self.args.quiet:
                        print(f"uudecoding to '{filename}'")
                    with open(filename, 'wb') as f:
                        f.write(decoded_data)
                except (binascii.Error, IOError, ValueError) as e:
                    if not self.args.quiet:
                        print(f"uudecode failed: {e}", file=sys.stderr)
            return

        # --- Handle cat and sed ---
        try:
            # Find the output filename
            redirect_index = parts.index('>')
            filename = self._sanitize_path(parts[redirect_index + 1])
        except (ValueError, IndexError):
            return

        # Check for -c (overwrite) option
        if os.path.exists(filename) and not self.args.overwrite:
            if not self.args.quiet:
                print(f"Skipping existing file: '{filename}'", file=sys.stderr)
            # Consume the here-document from the stream without writing
            for doc_line in stream:
                if doc_line.strip() == end_marker: break
            return
            
        # Parse sed 's/find/replace/' command if present
        sed_pattern = None
        if 'sed' in parts:
            sed_match = re.search(r"s/([^/]*)/([^/]*)/", line)
            if sed_match:
                sed_pattern = sed_match.groups()

        # Write the here-document content to the file
        try:
            with open(filename, 'w') as f:
                for doc_line in stream:
                    if doc_line.strip() == end_marker:
                        break
                    if sed_pattern:
                        doc_line = doc_line.replace(sed_pattern[0], sed_pattern[1])
                    f.write(doc_line)
        except (IOError, ValueError) as e:
            if not self.args.quiet:
                print(f"Failed to write file '{filename}': {e}", file=sys.stderr)

def main():
    """Parses arguments and runs the unshar process."""
    parser = argparse.ArgumentParser(
        description="Extract files from a shell archive.",
        usage="%(prog)s [-d dir] [-cfq] file ..."
    )
    parser.add_argument('-c', '-f', dest='overwrite', action='store_true',
                        help='Overwrite existing files.')
    parser.add_argument('-d', '--directory',
                        help='Change to DIR before extracting files.')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Quiet mode; suppress informational messages.')
    parser.add_argument('files', nargs='+', help='One or more shar files to process.')
    
    args = parser.parse_args()

    # Change directory if -d is specified
    if args.directory:
        try:
            os.makedirs(args.directory, exist_ok=True)
            os.chdir(args.directory)
        except OSError as e:
            print(f"Error: Can't chdir to '{args.directory}': {e}", file=sys.stderr)
            sys.exit(1)
            
    unsharper = Unsharer(args)
    for filepath in args.files:
        try:
            with open(filepath, 'r') as f:
                unsharper.unshar_stream(f)
        except FileNotFoundError:
            if not args.quiet:
                print(f"Error: File not found '{filepath}'", file=sys.stderr)
        except Exception as e:
             if not args.quiet:
                print(f"An error occurred with '{filepath}': {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
