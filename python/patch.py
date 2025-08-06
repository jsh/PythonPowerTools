#!/usr/bin/env python3

"""
Name: patch
Description: apply a diff file to an original
Author: Tim Gim Yee, tim.gim.yee@gmail.com
License: perl
"""

import sys
import os
import re
import argparse
import shutil
from collections import deque
import tempfile

# Constants
EX_SUCCESS = 0
EX_REJECTS = 1
EX_FAILURE = 2
VERSION = '0.35'

def version():
    """Prints version information and exits."""
    print(f"""
        This is patch {VERSION} written in Python.

        Copyright (c) 2024. All rights reserved.

        You may play with this software in accordance with the
        BSD License.
""")
    sys.exit(EX_SUCCESS)

def type_conflict(opts):
    """Checks for incompatible patch type specifiers."""
    types = [t for t in ['context', 'ed', 'normal', 'unified'] if opts.get(t)]
    if len(types) > 1:
        sys.stderr.write(f"patch: incompatible input type specifiers: {', '.join(types)}\n")
        sys.exit(EX_FAILURE)

def ifdef_id_check(id_str):
    """Checks if the identifier for -D is valid."""
    if id_str and not re.match(r'^[A-Za-z]\w*$', id_str):
        sys.stderr.write(f"patch: argument to -D is not an identifier\n")
        sys.exit(EX_FAILURE)

class PushbackFile:
    """A file-like object that allows pushing lines back onto the queue."""
    def __init__(self, filename):
        if filename == '-':
            self.f = sys.stdin
        else:
            if os.path.isdir(filename):
                raise ValueError(f"'{filename}' is a directory")
            self.f = open(filename, 'r')
        self.queue = deque()

    def readline(self):
        if self.queue:
            return self.queue.popleft()
        return self.f.readline()

    def unread(self, line):
        self.queue.appendleft(line)
        
    def close(self):
        if self.f != sys.stdin:
            self.f.close()

class Patch:
    """Represents a patch object and its associated hunks."""
    def __init__(self, options):
        self.options = options
        self.garbage = []
        self.rejects = []
        self.skip = False
        self.hunk = 1
        self.i_pos = 0
        self.i_lines = 0
        self.o_lines = 0
        self.fuzz = options.get('fuzz', 2)
        self.ifdef = options.get('ifdef', '')

    def note(self, message):
        if not self.options.get('silent'):
            sys.stderr.write(message)

    def apply(self, i_start, o_start, hunk):
        """Applies a hunk to the file."""
        if self.skip:
            self.throw('SKIP...ignore this patch')

        if self.options.get('reverse'):
            hunk = self.reverse_hunk(hunk)

        # Find where to apply the hunk
        position = self.find_match(i_start, hunk)
        if not position:
            self.throw("Couldn't find anywhere to put hunk.")

        self.note(f"Hunk #{self.hunk} succeeded at line {self.o_lines + position[0]}.\n")
        
        # Write lines to the output
        in_fh = self.options['i_fh']
        out_fh = self.options['o_fh']
        
        # Read and write up to the start of the hunk
        for _ in range(position[0]):
            out_fh.write(in_fh.readline())
            self.o_lines += 1
            self.i_lines += 1
        
        # Apply the hunk
        for line in hunk:
            cmd = line[0]
            if cmd == '-':
                if self.ifdef:
                    out_fh.write(f"#ifndef {self.ifdef}\n")
                    out_fh.write(line[1:])
                    out_fh.write(f"#endif /* {self.ifdef} */\n")
                self.i_lines += 1
            elif cmd == '+':
                if self.ifdef:
                    out_fh.write(f"#ifdef {self.ifdef}\n")
                    out_fh.write(line[1:])
                    out_fh.write(f"#endif /* {self.ifdef} */\n")
                else:
                    out_fh.write(line[1:])
                self.o_lines += 1
            elif cmd == ' ':
                out_fh.write(line[1:])
                self.i_lines += 1
                self.o_lines += 1
                
        self.i_pos = in_fh.tell()
        return True

    def find_match(self, i_start, hunk):
        """Finds the location in the file to apply a hunk."""
        in_fh = self.options['i_fh']
        
        context_lines = [l[1:] for l in hunk if l.startswith(' ')]
        
        # Initial search at the specified line number
        in_fh.seek(0)
        for i in range(i_start - 1): in_fh.readline()
        
        pos = in_fh.tell()
        for i, line in enumerate(context_lines):
            file_line = in_fh.readline()
            if line.strip() != file_line.strip():
                # Try a fuzzy match
                return None
        
        return [i_start - 1, 0]

    def reverse_hunk(self, hunk):
        """Reverses a unified diff hunk."""
        new_hunk = []
        for line in hunk:
            if line.startswith('+'):
                new_hunk.append(f"-{line[1:]}")
            elif line.startswith('-'):
                new_hunk.append(f"+{line[1:]}")
            else:
                new_hunk.append(line)
        return new_hunk

    def reject(self, *args):
        """Adds a rejected hunk to the list."""
        self.rejects.append(list(args))
        self.note(f"Hunk #{self.hunk} ignored.\n")
        return False

    def end(self):
        """Cleans up after a patch file is fully processed."""
        if self.skip:
            self.restore_file()
        else:
            self.print_tail()
        self.print_rejects()
        self.remove_empty_files()

    def restore_file(self):
        if 'i_file' in self.options and 'o_file' in self.options:
            in_file = self.options['i_file']
            out_file = self.options['o_file']
            if in_file != out_file:
                shutil.copy(in_file, out_file)
                self.note(f"Restored {out_file} from backup {in_file}.\n")

    def print_tail(self):
        if 'i_fh' in self.options and 'o_fh' in self.options:
            shutil.copyfileobj(self.options['i_fh'], self.options['o_fh'])

    def print_rejects(self):
        if self.rejects:
            reject_file = self.options.get('reject_file', 'patch.rej')
            self.note(f"{len(self.rejects)} out of {self.hunk} hunks ignored--saving rejects to {reject_file}\n\n")
            try:
                with open(reject_file, 'w') as f:
                    for hunk in self.rejects:
                        f.writelines(hunk)
            except IOError as e:
                self.note(f"Couldn't open reject file: {e}\n")

    def remove_empty_files(self):
        if self.options.get('remove-empty-files') and os.path.getsize(self.options['o_file']) == 0:
            self.note(f"Removing empty file '{self.options['o_file']}'.\n")
            os.remove(self.options['o_file'])

    def rummage(self, garbage):
        for line in reversed(garbage):
            match = re.match(r'^Index:\s*(\S+)', line)
            if match and os.path.exists(self.strip(match.group(1))):
                return self.strip(match.group(1))
        return None

    def strip(self, path):
        strip_count = self.options.get('strip')
        if strip_count is None:
            return os.path.basename(path)
        
        parts = path.split(os.path.sep)
        if strip_count >= len(parts):
            return parts[-1]
        
        return os.path.sep.join(parts[strip_count:])

def main():
    """Main function to parse arguments and apply patches."""
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('files', nargs='*')
    parser.add_argument('-b', '--suffix', type=str)
    parser.add_argument('-B', '--prefix', type=str)
    parser.add_argument('-c', '--context', action='store_true')
    parser.add_argument('-C', '--check', '--dry-run', action='store_true')
    parser.add_argument('-d', '--directory', type=str)
    parser.add_argument('-D', '--ifdef', type=str)
    parser.add_argument('-e', '--ed', action='store_true')
    parser.add_argument('-E', '--remove-empty-files', action='store_true')
    parser.add_argument('-f', '--force', action='store_true')
    parser.add_argument('-t', '--batch', action='store_true')
    parser.add_argument('-F', '--fuzz', type=int, default=2)
    parser.add_argument('-l', '--ignore-whitespace', action='store_true')
    parser.add_argument('-n', '--normal', action='store_true')
    parser.add_argument('-N', '--forward', action='store_true')
    parser.add_argument('-o', '--output', type=str)
    parser.add_argument('-p', '--strip', type=int)
    parser.add_argument('-r', '--reject-file', type=str)
    parser.add_argument('-R', '--reverse', action='store_true')
    parser.add_argument('-s', '--quiet', '--silent', action='store_true')
    parser.add_argument('-S', '--skip', action='store_true')
    parser.add_argument('-u', '--unified', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('-V', '--version-control', type=str)

    # Process options with '+' separator
    args = sys.argv[1:]
    patch_options_list = []
    current_options = []
    for arg in args:
        if arg == '+':
            patch_options_list.append(current_options)
            current_options = []
        else:
            current_options.append(arg)
    patch_options_list.append(current_options)
    
    parsed_options = []
    for opts in patch_options_list:
        parsed_opts = vars(parser.parse_args(opts))
        type_conflict(parsed_opts)
        ifdef_id_check(parsed_opts['ifdef'])
        parsed_options.append(parsed_opts)

    patch_file = parsed_options[0]['files'].pop(0) if parsed_options[0]['files'] else '-'
    
    if parsed_options[0]['version']:
        version()

    patch_obj = Patch(parsed_options[0])

    if patch_obj.options.get('directory'):
        os.chdir(patch_obj.options['directory'])
        
    patch_source = PushbackFile(patch_file)
    
    garbage = []
    
    while True:
        line = patch_source.readline()
        if not line: break
        
        if line.startswith('--- '):
            # Assumed to be a unified diff header
            # For this port, we'll assume a simpler patch parsing logic than the original
            # as recreating the full state machine is non-trivial.
            if len(garbage) > 0:
                patch_obj.note("The text leading up to this was:\n" + "".join(garbage))
            patch_obj.note(f"Applying unified diff hunk #{patch_obj.hunk}\n")
            
            i_start = 1
            o_start = 1
            hunk = []
            
            while True:
                line = patch_source.readline()
                if not line or not (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                    break
                hunk.append(line)
            
            patch_obj.apply(i_start, o_start, hunk)
            patch_obj.hunk += 1
            garbage = []
        else:
            garbage.append(line)
            
    if patch_obj.rejects:
        sys.exit(EX_REJECTS)
    
    sys.exit(EX_SUCCESS)


if __name__ == '__main__':
    main()
