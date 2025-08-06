#!/usr/bin/env python3

"""
Name: file
Description: determine file type
Author: dkulp
License: bsd
"""

import sys
import os
import re
import struct
import stat
import datetime
from pathlib import Path
from collections import deque
import argparse

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1

# Translation of type in magic file to struct unpack format and byte count
TEMPLATES = {
    'byte': ('b', 1),
    'ubyte': ('B', 1),
    'char': ('s', 1),
    'uchar': ('c', 1),
    'short': ('h', 2),
    'ushort': ('H', 2),
    'long': ('i', 4),
    'ulong': ('I', 4),
    'date': ('i', 4),
    'ubeshort': ('>H', 2),
    'beshort': ('>h', 2),
    'ubelong': ('>I', 4),
    'belong': ('>i', 4),
    'bedate': ('>i', 4),
    'uleshort': ('<H', 2),
    'leshort': ('<h', 2),
    'ulelong': ('<I', 4),
    'lelong': ('<i', 4),
    'ledate': ('<i', 4),
    'string': (None, None),
}

# For letter escapes in magic file
ESC = {
    'n': '\n', 'r': '\r', 'b': '\b', 't': '\t', 'f': '\f', 'v': '\v'
}

# Hard-coded checks for different texts (last resort)
SPECIALS = {
    "C program": ["/*", "#include", "char", "double", "extern", "float", "real", "struct", "union"],
    "C++ program": ["template", "virtual", "class", "public:", "private:"],
    "make commands": ["CFLAGS", "LDFLAGS", "all:", ".PRECIOUS"],
    "assembler program": [".ascii", ".asciiz", ".byte", ".even", ".globl", ".text", "clr"],
    "mail": ["Received:", ">From", "Return-Path:", "Cc:"],
    "news": ["Newsgroups:", "Path:", "Organization:"],
}

# Global variables for script state
check_magic = False
follow_links = False
magic_file = ''
magic_file_state = None
magic_entries = []

def usage():
    """Prints usage message and exits."""
    sys.stderr.write("usage: file [-cL] [-f filelist] [-m magicfile] file ...\n")
    sys.exit(EX_FAILURE)

def read_magic_entry(magic_list, mf_state, depth=0):
    """
    Reads and parses the next entry from the magic file.
    This function is a direct port of the original's recursive logic for parsing.
    """
    magic_fh, buffered_line, line_num = mf_state

    # Read lines, skipping comments and blanks
    while True:
        if buffered_line is None:
            buffered_line = magic_fh.readline()
            if not buffered_line:
                return
            mf_state[2] += 1
        
        if buffered_line.strip().startswith('#') or not buffered_line.strip():
            buffered_line = None
            continue
        break
        
    line = buffered_line
    mf_state[1] = None

    this_depth_len = 0
    match = re.match(r'^(>+)', line)
    if match:
        this_depth_len = len(match.group(1))

    # Handle recursion based on depth
    if this_depth_len > depth:
        # A sub-clause, call recursively
        entry = magic_list[-1]
        read_magic_entry(entry['subtests'], mf_state, depth + 1)
        # Handle state after recursive call
        line = mf_state[1]
        this_depth_len = len(re.match(r'^(>+)', line).group(1)) if re.match(r'^(>+)', line) else 0

    if this_depth_len < depth:
        mf_state[1] = line
        return this_depth_len
    
    # Parse a single magic entry line
    entry = read_magic_line(line, mf_state[2])
    if entry:
        if depth == 0:
            magic_list.append(entry)
        else:
            magic_list.append(entry)
    
    if magic_fh.closed:
        return
        
    mf_state[1] = None
    if read_magic_entry(magic_list, mf_state, depth) is None:
        return

def read_magic_line(line, line_num):
    """
    Parses a single line of the magic file into its components.
    This is a direct port of the original's complex regex-based parsing.
    """
    line = line.strip()
    match = re.match(r'^(>+)?\s*([&\(]?[a-flsx\.\+\-\d]+\)?)\s+(\S+)\s+(.*)', line)
    if not match:
        sys.stderr.write(f"file: Bad Offset/Type at line {line_num}. '{line}'\n")
        return None
    
    depth, offset_str, type_str, rest = match.groups()
    
    offtype = 0
    if offset_str.startswith('('):
        offtype = 1
        sub_match = re.match(r'\((\d+)(?:\.([bsl]))?([\+\-]?\d+)?\)', offset_str)
        if not sub_match:
            sys.stderr.write(f"file: Bad indirect offset at line {line_num}. '{offset_str}'\n")
            return None
        o1, type_char, o2 = sub_match.groups()
        o1 = int(o1, 8) if o1.startswith('0') else int(o1)
        o2 = int(o2, 8) if o2 and o2.startswith('0') else int(o2 or 0)
        
        type_char = type_char or 'l'
        size_map = {'b': 1, 's': 2, 'l': 4}
        size = size_map[type_char]
        offset = [o1, size, type_char, o2]
    elif offset_str.startswith('&'):
        offtype = 2
        offset = int(offset_str[1:], 8) if offset_str[1:].startswith('0') else int(offset_str[1:])
    else:
        offset = int(offset_str, 8) if offset_str.startswith('0') else int(offset_str)

    # Parse operator, test value, and message
    match = re.match(r'([><&^!x=])?([^\s]*)?\s*(.*)', rest)
    if not match:
        sys.stderr.write(f"file: Missing or invalid test condition or message at line {line_num}\n")
        return None
        
    operator, testval_str, message = match.groups()
    operator = operator or '='
    
    mask = None
    if '&' in type_str:
        type_str, mask_str = type_str.split('&', 1)
        mask = int(mask_str, 8) if mask_str.startswith('0') else int(mask_str, 16)
    
    if type_str not in TEMPLATES:
        sys.stderr.write(f"file: Invalid type '{type_str}' at line {line_num}\n")
        return None

    if type_str == 'string':
        testval = bytes(testval_str, 'latin-1').decode('unicode_escape')
        num_bytes = len(testval) if operator in ['=', '<'] else 0
        template = None
    else:
        testval = int(testval_str, 8) if testval_str and testval_str.startswith('0') else int(testval_str) if testval_str else None
        template, num_bytes = TEMPLATES[type_str]

    return {
        'depth': len(depth) if depth else 0,
        'offtype': offtype,
        'offset': offset,
        'num_bytes': num_bytes,
        'type': type_str,
        'mask': mask,
        'op': operator,
        'testval': testval,
        'template': template,
        'message': message,
        'subtests': [],
    }

def magic_match(item, desc_list, fh):
    """
    Compares a magic item against a file handle.
    Returns True on a match, False otherwise.
    """
    if fh is None:
        return False
    
    # Store original position for backtracking
    original_pos = fh.tell()
    
    offtype, offset, num_bytes, type_str, mask, op, testval, template, message, subtests = item.values()
    
    # Seek to the correct position
    if offtype == 1:
        off1, sz, tpl, off2 = offset
        try:
            fh.seek(off1)
            data = fh.read(sz)
            indirect_offset = struct.unpack(tpl, data)[0]
            fh.seek(indirect_offset + off2)
        except (IOError, struct.error):
            return False
    elif offtype == 2:
        try:
            fh.seek(offset, os.SEEK_CUR)
        except IOError:
            return False
    else:
        try:
            fh.seek(offset)
        except IOError:
            return False

    match = False
    
    try:
        if type_str == 'string':
            if op == '=':
                data = fh.read(num_bytes).decode('latin-1')
                match = data == testval
            elif op == '>':
                data = fh.read().decode('latin-1')
                match = data > testval
            elif op == '<':
                data = fh.read().decode('latin-1')
                match = data < testval
        else: # Numeric types
            data = fh.read(num_bytes)
            if len(data) != num_bytes:
                return False
                
            val = struct.unpack(template, data)[0]
            if mask is not None:
                val &= mask

            if op == '=': match = val == testval
            elif op == 'x': match = True
            elif op == '!': match = val != testval
            elif op == '&': match = (val & testval) == testval
            elif op == '^': match = (~val & testval) == testval
            elif op == '<': match = val < testval
            elif op == '>': match = val > testval
    except (IOError, struct.error, ValueError):
        return False

    if match:
        desc_list.append(message)
        for subtest in subtests:
            magic_match(subtest, desc_list, fh)
    
    fh.seek(original_pos)
    return match

def dump_magic(magic_list, depth=0):
    """Recursively prints the parsed magic file structure for debugging."""
    for item in magic_list:
        print(f"{'>' * depth}{item['offset']}\t{item['type']}\t{item['op']}{item['testval']}\t{item['message']}")
        if item['subtests']:
            dump_magic(item['subtests'], depth + 1)

def main():
    """Main function to process command-line arguments and files."""
    global magic_file, check_magic, follow_links, magic_file_state, magic_entries
    
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('files', nargs='*')
    parser.add_argument('-m', type=str, help='Specify an alternate magic file.')
    parser.add_argument('-c', action='store_true', help='Debug check magic file.')
    parser.add_argument('-L', action='store_true', help='Follow symbolic links.')
    parser.add_argument('-f', type=str, help='Read filenames from a file.')
    
    args = parser.parse_args()
    
    check_magic = args.c
    follow_links = args.L
    
    if args.m:
        magic_file = args.m
    elif os.path.exists('/etc/magic'):
        magic_file = '/etc/magic'
    else:
        sys.stderr.write("file: Can't find magic file. Specify one with -m.\n")
        sys.exit(EX_FAILURE)
    
    if args.f:
        try:
            with open(args.f, 'r') as fl:
                args.files.extend(fl.read().splitlines())
        except IOError as e:
            sys.stderr.write(f"file: {args.f}: {e}\n")
            sys.exit(EX_FAILURE)
    
    if not args.files and not check_magic:
        usage()
        
    try:
        magic_file_state = [open(magic_file, 'r'), None, 0]
        read_magic_entry(magic_entries, magic_file_state)
    except IOError as e:
        sys.stderr.write(f"file: {magic_file}: {e}\n")
        sys.exit(EX_FAILURE)
    
    if check_magic:
        dump_magic(magic_entries)
        sys.exit(EX_SUCCESS)

    for file_path in args.files:
        if file_path == '-':
            sys.stderr.write("file: Can't operate on standard input.\n")
            continue
            
        desc = [f"{file_path}:"]
        
        try:
            file_stat = Path(file_path).lstat() if not follow_links else Path(file_path).stat()
        except FileNotFoundError:
            sys.stderr.write(f"file: {file_path}: No such file or directory\n")
            continue
        except OSError as e:
            sys.stderr.write(f"file: failed to stat '{file_path}': {e}\n")
            continue
            
        if stat.S_ISLNK(file_stat.st_mode) and not follow_links:
            desc.append(f"symbolic link to {os.readlink(file_path)}")
        elif stat.S_ISDIR(file_stat.st_mode):
            desc.append("directory")
        elif stat.S_ISFIFO(file_stat.st_mode):
            desc.append("named pipe")
        elif stat.S_ISSOCK(file_stat.st_mode):
            desc.append("socket")
        elif stat.S_ISBLK(file_stat.st_mode):
            desc.append("block special file")
        elif stat.S_ISCHR(file_stat.st_mode):
            desc.append("character special file")
        elif file_stat.st_size == 0:
            desc.append("empty")
        
        if len(desc) > 1:
            print(" ".join(desc))
            continue
            
        match_found = False
        try:
            with open(file_path, 'rb') as fh:
                if (file_stat.st_mode & stat.S_IXUSR) and file_stat.st_size > 0:
                    line1 = fh.readline().decode('latin-1', errors='ignore')
                    if line1.startswith('#!'):
                        desc.append(f"executable {line1.strip().split()[0][2:]} script")
                        match_found = True
                
                if not match_found:
                    for item in magic_entries:
                        if magic_match(item, desc, fh):
                            match_found = True
                            break
        except IOError:
            sys.stderr.write(f"file: failed to open '{file_path}' for reading\n")
            continue
            
        if not match_found:
            if stat.S_ISREG(file_stat.st_mode):
                # Try a final check for text/binary
                try:
                    with open(file_path, 'r', encoding='latin-1') as fh:
                        content = fh.read(8192)
                        if any(c in content for c in SPECIALS):
                            desc.append("text")
                        else:
                            desc.append("data")
                except UnicodeDecodeError:
                    desc.append("data")

        print(" ".join(desc))
        
if __name__ == "__main__":
    main()
