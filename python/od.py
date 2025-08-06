#!/usr/bin/env python3

"""
Name: od
Description: dump files in octal and other formats
Author: Mark Kahn, mkahn@vbe.com
Author: Michael Mikonos
License: perl
"""

import sys
import os
import re
from functools import partial
import struct
from collections import deque

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
LINESZ = 16
PRINTMAX = 126
VERSION = '1.4'

# Character escape mappings
CHAR_ESCAPES = {
    0: ' \\0', 7: ' \\a', 8: ' \\b', 9: ' \\t', 10: ' \\n', 11: ' \\v',
    12: ' \\f', 13: ' \\r', 92: ' \\\\'
}

# Character names for 7-bit ASCII dump
CHAR_NAMES = {
    0: 'nul', 1: 'soh', 2: 'stx', 3: 'etx', 4: 'eot', 5: 'enq', 6: 'ack', 7: 'bel',
    8: ' bs', 9: ' ht', 10: ' nl', 11: ' vt', 12: ' ff', 13: ' cr', 14: ' so',
    15: ' si', 16: 'dle', 17: 'dc1', 18: 'dc2', 19: 'dc3', 20: 'dc4', 21: 'nak',
    22: 'syn', 23: 'etb', 24: 'can', 25: ' em', 26: 'sub', 27: 'esc', 28: ' fs',
    29: ' gs', 30: ' rs', 31: ' us', 32: ' sp', 127: 'del'
}

# Global variables for script state
offset1 = 0
last_line = b''
lim = None
nread = 0
rc = EX_SUCCESS
program_name = os.path.basename(sys.argv[0])

# Function to handle different output formats
def format_data(data, fmt_str, size):
    """Unpacks binary data and formats it for printing."""
    # Pad the data to a multiple of size
    padding = b'\x00' * (size - (len(data) % size)) if len(data) % size != 0 else b''
    padded_data = data + padding
    
    unpacked_data = struct.unpack(fmt_str, padded_data)
    
    # Custom formatting for different types
    if fmt_str.startswith('<f') or fmt_str.startswith('<d'):
        return [f'{x:15.7e}' for x in unpacked_data]
    elif fmt_str.endswith('f') or fmt_str.endswith('d'):
        return [f'{x:24.16e}' for x in unpacked_data]
    else:
        return unpacked_data

# The original Perl script uses a series of subroutines to set the
# format string and unpack specifier. In Python, a dictionary of
# unpack formats and a list of arguments to pass to `struct.unpack`
# is a more direct port. The following functions act as a lookup table.

def octal1(data):
    unpacked = struct.unpack(f'<{len(data)}B', data)
    return ' '.join([f'{x:03o}' for x in unpacked])

def decimal1(data):
    unpacked = struct.unpack(f'<{len(data)}b', data)
    return ' '.join([f'{x:4d}' for x in unpacked])

def udecimal1(data):
    unpacked = struct.unpack(f'<{len(data)}B', data)
    return ' '.join([f'{x:3u}' for x in unpacked])

def hex1(data):
    unpacked = struct.unpack(f'<{len(data)}B', data)
    return ' '.join([f'{x:02x}' for x in unpacked])

def char1(data):
    unpacked = struct.unpack(f'<{len(data)}B', data)
    output = []
    for val in unpacked:
        if val in CHAR_ESCAPES:
            output.append(CHAR_ESCAPES[val].strip())
        elif val > PRINTMAX or not chr(val).isprintable():
            output.append(f'\\{val:03o}')
        else:
            output.append(f'  {chr(val)} ')
    return ''.join(output)

def char7bit(data):
    unpacked = struct.unpack(f'<{len(data)}B', data)
    output = []
    for val in unpacked:
        n = val & 0x7F
        if n in CHAR_NAMES:
            output.append(CHAR_NAMES[n].rjust(4))
        else:
            output.append(f'   {chr(n)}')
    return ' '.join(output)

def udecimal2(data):
    unpacked = struct.unpack(f'<{len(data)//2}H', data)
    return ' '.join([f'{x:5u}' for x in unpacked])

def decimal2(data):
    unpacked = struct.unpack(f'<{len(data)//2}h', data)
    return ' '.join([f'{x:6d}' for x in unpacked])

def long_fmt(data):
    unpacked = struct.unpack(f'<{len(data)//4}l', data)
    return ' '.join([f'{x:10d}' for x in unpacked])

def octal2(data):
    unpacked = struct.unpack(f'<{len(data)//2}H', data)
    return ' '.join([f'{x:06o}' for x in unpacked])

def octal4(data):
    unpacked = struct.unpack(f'<{len(data)//4}L', data)
    return ' '.join([f'{x:011o}' for x in unpacked])

def decimal4(data):
    unpacked = struct.unpack(f'<{len(data)//4}l', data)
    return ' '.join([f'{x:11d}' for x in unpacked])

def udecimal4(data):
    unpacked = struct.unpack(f'<{len(data)//4}L', data)
    return ' '.join([f'{x:11u}' for x in unpacked])

def hex2(data):
    unpacked = struct.unpack(f'<{len(data)//2}H', data)
    return ' '.join([f'{x:04x}' for x in unpacked])

def hex4(data):
    unpacked = struct.unpack(f'<{len(data)//4}L', data)
    return ' '.join([f'{x:08x}' for x in unpacked])

def hex8(data):
    if len(data) % 8 != 0:
        data += b'\x00' * (8 - len(data) % 8)
    unpacked = struct.unpack(f'<{len(data)//8}Q', data)
    return ' '.join([f'{x:016x}' for x in unpacked])

def octal8(data):
    if len(data) % 8 != 0:
        data += b'\x00' * (8 - len(data) % 8)
    unpacked = struct.unpack(f'<{len(data)//8}Q', data)
    return ' '.join([f'{x:022o}' for x in unpacked])

def udecimal8(data):
    if len(data) % 8 != 0:
        data += b'\x00' * (8 - len(data) % 8)
    unpacked = struct.unpack(f'<{len(data)//8}Q', data)
    return ' '.join([f'{x:22d}' for x in unpacked])

def decimal8(data):
    if len(data) % 8 != 0:
        data += b'\x00' * (8 - len(data) % 8)
    unpacked = struct.unpack(f'<{len(data)//8}q', data)
    return ' '.join([f'{x:22d}' for x in unpacked])

def float4(data):
    if len(data) % 4 != 0:
        data += b'\x00' * (4 - len(data) % 4)
    unpacked = struct.unpack(f'<{len(data)//4}f', data)
    return ' '.join([f'{x:15.7e}' for x in unpacked])

def float8(data):
    if len(data) % 8 != 0:
        data += b'\x00' * (8 - len(data) % 8)
    unpacked = struct.unpack(f'<{len(data)//8}d', data)
    return ' '.join([f'{x:24.16e}' for x in unpacked])

def diffdata(current_data):
    """Checks if the current data is the same as the last line's data."""
    global last_line
    if current_data == last_line:
        return False
    last_line = current_data
    return True

def help():
    """Prints usage message and exits."""
    print("usage: od [-aBbcDdeFfHhilOosXxv] [-A radix] [-j skip_bytes] ",
          "[-N limit_bytes] [-t type] [file]...")
    sys.exit(EX_FAILURE)

def dump_line(data, fmt_func, radix, verbose):
    """Dumps a single line of formatted data."""
    global offset1, last_line
    
    if not verbose:
        if not diffdata(data):
            if offset1 > 0:
                print("*")
            offset1 += len(data)
            return
    
    if radix != 'n':
        if radix == 'd':
            print(f'{offset1:08d} ', end='')
        elif radix == 'o':
            print(f'{offset1:08o} ', end='')
        elif radix == 'x':
            print(f'{offset1:08x} ', end='')
    
    print(fmt_func(data))
    offset1 += len(data)

def dump_file(file_handle, fmt_func, radix, skip, limit, verbose):
    """Reads a file chunk by chunk and dumps its contents."""
    global nread, offset1
    
    file_handle.seek(skip)
    offset1 = skip
    
    while True:
        if limit is not None and nread >= limit:
            break
        
        chunk_size = LINESZ
        if limit is not None:
            chunk_size = min(LINESZ, limit - nread)
            
        data = file_handle.read(chunk_size)
        if not data:
            break
        
        nread += len(data)
        dump_line(data, fmt_func, radix, verbose)

def main():
    """Main function to parse arguments and execute od."""
    global offset1, radix, lim, rc, last_line
    
    # Use argparse for robust option parsing
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('files', nargs='*')
    parser.add_argument('-A', type=str, choices=['d', 'o', 'x', 'n'])
    parser.add_argument('-a', action='store_true')
    parser.add_argument('-B', action='store_true')
    parser.add_argument('-b', action='store_true')
    parser.add_argument('-c', action='store_true')
    parser.add_argument('-D', action='store_true')
    parser.add_argument('-d', action='store_true')
    parser.add_argument('-e', action='store_true')
    parser.add_argument('-F', action='store_true')
    parser.add_argument('-f', action='store_true')
    parser.add_argument('-H', action='store_true')
    parser.add_argument('-h', action='store_true')
    parser.add_argument('-i', action='store_true')
    parser.add_argument('-j', type=int)
    parser.add_argument('-l', action='store_true')
    parser.add_argument('-N', type=int)
    parser.add_argument('-O', action='store_true')
    parser.add_argument('-o', action='store_true')
    parser.add_argument('-s', action='store_true')
    parser.add_argument('-t', type=str)
    parser.add_argument('-v', action='store_true')
    parser.add_argument('-X', action='store_true')
    parser.add_argument('-x', action='store_true')
    
    opts = parser.parse_args()

    # Set default radix and format function
    radix = 'o'
    fmt_func = octal2
    
    if opts.A:
        radix = opts.A
    
    format_map = {
        'a': char7bit, 'b': octal1, 'c': char1, 'D': udecimal4, 'd': udecimal2,
        'e': float8, 'F': float8, 'f': float4, 'H': hex4, 'h': hex2, 'i': decimal2,
        'l': long_fmt, 'O': octal4, 'o': octal2, 's': decimal2, 'X': hex4, 'x': hex2,
        'B': octal2
    }
    
    for opt, func in format_map.items():
        if getattr(opts, opt):
            fmt_func = func

    if opts.t:
        t_map = {
            'a': char7bit, 'c': char1,
            'o1': octal1, 'o2': octal2, 'o4': octal4, 'o8': octal8,
            'd1': decimal1, 'd2': decimal2, 'd4': decimal4, 'd8': decimal8,
            'u1': udecimal1, 'u2': udecimal2, 'u4': udecimal4, 'u8': udecimal8,
            'x1': hex1, 'x2': hex2, 'x4': hex4, 'x8': hex8,
            'f4': float4, 'f8': float8
        }
        if opts.t in t_map:
            fmt_func = t_map[opts.t]
        else:
            help()

    lim = opts.N
    skip = opts.j if opts.j else 0
    verbose = opts.v
    
    if not opts.files:
        try:
            dump_file(sys.stdin.buffer, fmt_func, radix, skip, lim, verbose)
        except IOError:
            rc = EX_FAILURE
    else:
        for file in opts.files:
            if os.path.isdir(file):
                sys.stderr.write(f"{program_name}: '{file}' is a directory\n")
                rc = EX_FAILURE
                continue
            try:
                with open(file, 'rb') as fh:
                    dump_file(fh, fmt_func, radix, skip, lim, verbose)
            except IOError as e:
                sys.stderr.write(f"{program_name}: cannot open '{file}': {e}\n")
                rc = EX_FAILURE
    
    if nread > 0:
        if radix != 'n':
            if radix == 'd':
                print(f'{offset1:08d}')
            elif radix == 'o':
                print(f'{offset1:08o}')
            elif radix == 'x':
                print(f'{offset1:08x}')

    sys.exit(rc)


if __name__ == '__main__':
    main()
