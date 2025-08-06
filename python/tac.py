#!/usr/bin/env python3

"""
Name: tac
Description: concatenate and print files in reverse
Author: Tim Gim Yee, tim.gim.yee@gmail.com
License: perl
"""

import sys
import os
import re
from collections import deque
import argparse

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
VERSION = '0.19'

class IOTac:
    """
    A class that emulates Perl's TIEHANDLE for reading files in reverse.
    """
    def __init__(self, **opts):
        self.opts = {k.lower(): v for k, v in opts.items()}
        self.lines = deque()
        self.scrap = b''
        self.eof = False
        self.files = []
        self.current_file_idx = -1
        self.error = False
        
        # Determine the record separator and chunk size
        self.separator = self.opts.get('separator', b'\n')
        self.regex = self.opts.get('regex', False)
        self.size = int(self.opts.get('size', 8192))
        self.binary = self.opts.get('binary', False)
        self.before = self.opts.get('before', False)
        
        # Paragraph mode if separator is an empty string
        self.paragraph = self.separator == b''
        if self.paragraph:
            self.separator = b'\n\n+' if self.regex else b'\n\n'
            
        if self.regex:
            try:
                self.re_sep = re.compile(self.separator, re.DOTALL)
                self.re_capture = re.compile(b'(' + self.separator + b')', re.DOTALL)
            except re.error:
                sys.stderr.write(f"tac: invalid regular expression: {self.separator}\n")
                sys.exit(EX_FAILURE)
        else:
            self.re_sep = re.escape(self.separator)
            self.re_capture = re.escape(b'(' + self.separator + b')')

        # Open files
        files_to_open = self.opts.get('files', [])
        if not files_to_open and not sys.stdin.isatty():
            self.files.append(('-', sys.stdin.buffer))
        else:
            if not files_to_open:
                sys.stderr.write("tac: missing file operands\n")
                sys.exit(EX_FAILURE)
                
            for file_name in files_to_open:
                if file_name == '-':
                    self.files.append(('-', sys.stdin.buffer))
                    continue
                
                if os.path.isdir(file_name):
                    sys.stderr.write(f"tac: '{file_name}' is a directory\n")
                    self.error = True
                    continue
                
                try:
                    fh = open(file_name, 'rb')
                    fh.seek(0, 2)
                    self.files.append((file_name, fh))
                except IOError as e:
                    sys.stderr.write(f"tac: failed to open '{file_name}': {e}\n")
                    self.error = True
        
        self.current_file_idx = len(self.files) - 1

    def __iter__(self):
        return self

    def __next__(self):
        """Reads and returns the next line in reverse."""
        if not self.lines:
            self._get_lines()
        
        if not self.lines:
            self.close()
            raise StopIteration
            
        return self.lines.pop()

    def _get_lines(self):
        """Reads a chunk of the current file and populates the lines deque."""
        if self.current_file_idx < 0:
            self.lines.clear()
            return

        file_name, fh = self.files[self.current_file_idx]
        
        if file_name == '-':
            # Reading from stdin is a special case (no seeking)
            self.lines.clear()
            data = fh.read()
            if not data:
                self.current_file_idx -= 1
                return
            
            # Record mode
            if not self.regex and self.size:
                start = len(data) - self.size
                while start >= 0:
                    self.lines.appendleft(data[start:start + self.size])
                    start -= self.size
                if start < 0 and len(data) % self.size != 0:
                     self.lines.appendleft(data[:len(data) % self.size])
                
            # Line mode
            else:
                chunks = re.split(self.re_sep, data, flags=re.DOTALL)
                for i, chunk in enumerate(chunks):
                    if not self.before and not self.paragraph and i < len(chunks) - 1:
                        self.lines.appendleft(chunk + self.separator)
                    elif self.before and not self.paragraph and i > 0:
                         self.lines.appendleft(self.separator + chunk)
                    else:
                        self.lines.appendleft(chunk)
            
            self.current_file_idx -= 1
            return
            
        tell = fh.tell()
        
        if tell <= 0:
            self.current_file_idx -= 1
            return
            
        chunk_size = self.size
        
        # Logic to ensure chunks don't break records
        while True:
            read_pos = max(0, tell - chunk_size)
            fh.seek(read_pos, 0)
            chunk = fh.read(tell - read_pos)
            
            if self.regex:
                # Check for a broken separator at the beginning of the chunk
                # and if a separator exists at all
                is_broken = self.re_sep.search(chunk[:len(self.separator)]) if self.separator else False
                has_separator = self.re_sep.search(chunk)
            else:
                is_broken = chunk.startswith(self.separator) if self.separator else False
                has_separator = self.separator in chunk
            
            if is_broken or (not has_separator and read_pos > 0):
                chunk_size += self.size
            else:
                break
        
        fh.seek(read_pos, 0)
        
        # Read the chunk
        data = fh.read(tell - read_pos)
        
        # Prepend leftover data from the previous chunk
        data += self.scrap
        self.scrap = b''
        
        if not self.regex:
            if self.before:
                # Attach separator to the beginning of the record
                lines = data.split(self.separator)
                if lines[0]:
                    self.scrap = lines.pop(0)
                
                # Re-add separators to the front of lines
                reversed_lines = []
                for line in reversed(lines):
                    reversed_lines.append(self.separator + line)
                self.lines.extend(reversed_lines)
            else:
                # Attach separator to the end of the record
                lines = data.split(self.separator)
                if lines[-1]:
                    self.scrap = lines.pop()
                    
                # Re-add separators to the end of lines
                reversed_lines = []
                for line in reversed(lines):
                    reversed_lines.append(line + self.separator)
                self.lines.extend(reversed_lines)
                
            
        else: # Regular expression mode
            lines = re.split(self.re_sep, data)
            
            if self.before:
                if lines and lines[0]:
                    self.scrap = lines.pop(0)
                
                separators = re.findall(self.re_sep, data)
                
                if lines and separators:
                    for i in range(len(lines)):
                        self.lines.appendleft(separators[i] + lines[i])
            else: # After
                separators = re.findall(self.re_sep, data)
                
                if lines and lines[-1]:
                    self.scrap = lines.pop()
                    
                if lines and separators:
                    for i in range(len(lines)):
                        self.lines.appendleft(lines[i] + separators[i])

        # Move to next file if finished
        if fh.tell() == 0:
            self.current_file_idx -= 1
        
    def close(self):
        """Closes all file handles."""
        for name, fh in self.files:
            if fh not in (sys.stdin.buffer, sys.stdout.buffer, sys.stderr.buffer):
                fh.close()

def main():
    """Main function to parse arguments and run tac."""
    program_name = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        description="Concatenate and print files in reverse.",
        add_help=False
    )
    
    # Custom flags for this implementation
    parser.add_argument('-b', '--before', action='store_true',
                        help='Attach separator to the beginning of the record.')
    parser.add_argument('-B', '--binary', action='store_true',
                        help='Read files in binary mode.')
    parser.add_argument('-r', '--regex', action='store_true',
                        help='The separator is a regular expression.')
    parser.add_argument('-s', '--separator', type=str,
                        help='Use STRING as record separator.')
    parser.add_argument('-S', '--bytes', type=int,
                        help='Number of bytes to read at a time. Defaults to 8192.')
    parser.add_argument('files', nargs='*', default=['-'],
                        help='Files to process. Use "-" for standard input.')
    parser.add_argument('-h', '--help', action='store_true',
                        help=argparse.SUPPRESS)
    
    # Parse args, but handle custom behavior for -s and -S first
    args = sys.argv[1:]
    if '-s' in args:
        s_idx = args.index('-s')
        if s_idx + 1 < len(args):
            args[s_idx+1] = args[s_idx+1].encode('utf-8')
    if '-S' in args:
        s_idx = args.index('-S')
        if s_idx + 1 < len(args):
            try:
                if int(args[s_idx+1]) <= 0:
                    sys.stderr.write(f"{program_name}: option -S expects a number >= 1\n")
                    sys.exit(EX_FAILURE)
            except (ValueError, IndexError):
                sys.stderr.write(f"{program_name}: option -S expects a number >= 1\n")
                sys.exit(EX_FAILURE)
    
    parsed_args = parser.parse_args(args)
    
    if parsed_args.help:
        parser.print_help()
        sys.exit(EX_SUCCESS)

    if parsed_args.bytes and parsed_args.bytes <= 0:
        sys.stderr.write(f"{program_name}: option -S expects a number >= 1\n")
        sys.exit(EX_FAILURE)
    
    # If no files are given and stdin is not a TTY, read from stdin
    if not parsed_args.files and not sys.stdin.isatty():
        parsed_args.files = ['-']
    
    # Python's argparse handles `parsed_args.files` being a list of strings
    opts = {
        'files': parsed_args.files,
        'before': parsed_args.before,
        'binary': parsed_args.binary,
        'regex': parsed_args.regex,
        'separator': parsed_args.separator.encode('utf-8') if parsed_args.separator else b'\n',
        'size': parsed_args.bytes,
    }
    
    # Create the IOTac object and print lines
    try:
        tac_reader = IOTac(**opts)
        for line in tac_reader:
            sys.stdout.buffer.write(line)
        
        if tac_reader.error:
            sys.exit(EX_FAILURE)
            
    except Exception as e:
        sys.stderr.write(f"tac: an unexpected error occurred: {e}\n")
        sys.exit(EX_FAILURE)
    
    sys.exit(EX_SUCCESS)


if __name__ == "__main__":
    main()
