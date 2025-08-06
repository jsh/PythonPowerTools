#!/usr/bin/env python3

"""
Name: tail
Description: display the last part of a file
Author: Thierry Bezecourt, thbzcrt@worldnet.fr
License: perl
"""

import sys
import os
import re
import time
from collections import deque
import argparse
import signal
from pathlib import Path

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
BLOCK_SIZE = 512

# Global state for signal handling in -f mode
file_info = {}
file_list = []
dir_list = []

def usage(message=None):
    """Prints a usage message and exits."""
    if message:
        sys.stderr.write(f"tail: {message}\n")
    sys.stderr.write("""Usage:
    tail [-f | -r] [-b number | -c number | -n number | [-+]number]
         [file ...]
    xtail file ...
""")
    sys.exit(EX_FAILURE)

def check_number(value_str):
    """Parses a number from a string, handling +/- prefixes."""
    try:
        if value_str.startswith('+'):
            return int(value_str[1:])
        return int(value_str)
    except (ValueError, IndexError):
        usage(f"invalid number '{value_str}'")

def new_argv(argv):
    """
    Translates historical command-line syntax (e.g., `-10`) to modern flags.
    """
    new_args = []
    end_of_options = False
    
    for arg in argv:
        if arg == '--' or not arg.startswith(('-', '+')):
            new_args.append(arg)
            end_of_options = True
            continue
        
        if not end_of_options and re.match(r'^[+-]\d+$', arg):
            new_args.append(f'-n{arg}')
        else:
            new_args.append(arg)
            
    return new_args

def parse_args():
    """Parses command-line arguments using argparse for robust handling."""
    me = os.path.basename(sys.argv[0])
    
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('files', nargs='*')
    
    if me == 'xtail':
        # xtail has no options, it's just `tail -f`
        options = parser.parse_args(sys.argv[1:])
        return (10, 'n', options.files, True, False)

    parser.add_argument('-b', type=str, help='Location is NUMBER 512-byte blocks.')
    parser.add_argument('-c', type=str, help='Location is NUMBER bytes.')
    parser.add_argument('-f', action='store_true', help='Follow file growth.')
    parser.add_argument('-n', type=str, default='-10', help='Location is NUMBER lines.')
    parser.add_argument('-r', action='store_true', help='Reverse the order of output.')
    
    parsed_args = parser.parse_args(new_argv(sys.argv[1:]))
    
    if parsed_args.f and parsed_args.r:
        usage('-f and -r cannot be used together')
        
    point = -10
    type_ = 'n'
    
    if parsed_args.b:
        if parsed_args.c or parsed_args.n != '-10':
            usage()
        point = check_number(parsed_args.b)
        type_ = 'b'
    elif parsed_args.c:
        if parsed_args.b or parsed_args.n != '-10':
            usage()
        point = check_number(parsed_args.c)
        type_ = 'c'
    elif parsed_args.n:
        if parsed_args.b or parsed_args.c:
            usage()
        point = check_number(parsed_args.n)
        type_ = 'n'

    if point == 0:
        usage('The number cannot be zero')
        
    return (point, type_, parsed_args.files, parsed_args.f, parsed_args.r)

def print_tail(fh, point, type_):
    """
    Prints the tail of a file based on the given point and type.
    """
    if type_ == 'n':
        if point > 0:  # From the beginning
            # Skip lines
            for _ in range(point - 1):
                fh.readline()
            # Print remaining
            for line in fh:
                print(line, end='')
        else:  # From the end
            lines = deque(fh, maxlen=-point)
            for line in lines:
                print(line, end='')
    
    elif type_ == 'c':
        if point > 0:  # From the beginning
            fh.seek(point - 1)
            sys.stdout.write(fh.read())
        else:  # From the end
            fh.seek(point, os.SEEK_END)
            sys.stdout.write(fh.read())
            
    elif type_ == 'b':
        if point > 0:  # From the beginning
            fh.seek((point - 1) * BLOCK_SIZE)
            sys.stdout.buffer.write(fh.read().encode('utf-8'))
        else:  # From the end
            fh.seek(point * BLOCK_SIZE, os.SEEK_END)
            sys.stdout.buffer.write(fh.read().encode('utf-8'))

def print_tail_r(fh, point, type_):
    """
    Prints the tail of a file in reverse order.
    """
    if type_ == 'n':
        lines = fh.readlines()
        if point > 0:
            lines = lines[:point]
        for line in reversed(lines):
            print(line, end='')
    elif type_ == 'c':
        # The original Perl script's logic for -rc and -rb is complex and potentially buggy.
        # This implementation simplifies it by reading the whole file into memory
        # to ensure correctness, as the character/block reverse logic is tricky.
        content = fh.read()
        if point > 0:
            content = content[:point]
        for char in reversed(content):
            print(char, end='')
    elif type_ == 'b':
        content = fh.read()
        if point > 0:
            content = content[:point * BLOCK_SIZE]
        chunks = [content[i:i + BLOCK_SIZE] for i in range(0, len(content), BLOCK_SIZE)]
        for chunk in reversed(chunks):
            sys.stdout.write(chunk)

def get_existing_files(files_to_check, dirs_to_check):
    """Finds all existing files to monitor, including those in directories."""
    all_files = set()
    for f in files_to_check:
        if os.path.exists(f):
            all_files.add(f)
    for d in dirs_to_check:
        if os.path.isdir(d):
            for entry in os.listdir(d):
                path = os.path.join(d, entry)
                if os.path.isfile(path):
                    all_files.add(path)
    return sorted(list(all_files))

def handle_quit_signal(sig, frame):
    """Signal handler for QUIT signal (Ctrl-\)."""
    print("\n*** recently changed files ***")
    
    sorted_files = sorted(file_info.keys(), key=lambda f: file_info[f].st_mtime, reverse=True)
    
    for i, f in enumerate(sorted_files, 1):
        info = file_info[f]
        print(f"{i:3d}  {time.ctime(info.st_mtime):24}  {f}")
        
    existing_files_count = len(get_existing_files(file_list, dir_list))
    unknown_files_count = len([f for f in file_list if not os.path.exists(f)])
    
    print(f"currently watching: {existing_files_count:3d} files {len(dir_list):3d} dirs {unknown_files_count:3d} unknown entries")

def tail_f(files, dirs, point, type_):
    """Monitors files for changes and prints new data as it's written."""
    global file_info, file_list, dir_list
    file_list = files
    dir_list = dirs
    
    signal.signal(signal.SIGQUIT, handle_quit_signal)

    # Initialize file info
    for f in get_existing_files(files, dirs):
        try:
            file_info[f] = os.stat(f)
        except OSError:
            pass

    current_file_id = None

    while True:
        # Check for newly created files
        for f in get_existing_files(files, dirs):
            if f not in file_info:
                print(f"\n*** '{f}' has been created ***")
                try:
                    info = os.stat(f)
                    file_info[f] = info
                    with open(f, 'r') as fh:
                        print_tail(fh, point, type_)
                except OSError:
                    pass

        # Loop on monitored files
        for f in list(file_info.keys()):
            try:
                old_info = file_info[f]
                new_info = os.stat(f)

                if new_info.st_ino != old_info.st_ino or new_info.st_size < old_info.st_size:
                    # File was truncated or replaced
                    print(f"\n*** '{f}' has been truncated or replaced ***")
                    with open(f, 'r') as fh:
                        print(f"\n*** {f} ***")
                        print_tail(fh, point, type_)
                    file_info[f] = new_info
                    current_file_id = f
                elif new_info.st_size > old_info.st_size:
                    # Data has been appended
                    with open(f, 'r') as fh:
                        fh.seek(old_info.st_size)
                        new_data = fh.read()
                        
                        if current_file_id != f:
                            print(f"\n*** {f} ***")
                            current_file_id = f
                        
                        print(new_data, end='')
                    file_info[f] = new_info
            
            except FileNotFoundError:
                print(f"\n*** '{f}' has been deleted ***")
                del file_info[f]
            except OSError as e:
                sys.stderr.write(f"tail: {e}\n")
        
        time.sleep(1)

def handle_args():
    """Main logic to handle arguments and execute the correct tail function."""
    point, type_, files, do_follow, do_reverse = parse_args()
    rc = EX_SUCCESS

    regular_files = []
    dirs = []
    
    # Separate files and directories
    for f in files:
        if os.path.isdir(f):
            if do_follow:
                dirs.append(f)
            else:
                sys.stderr.write(f"tail: '{f}' is a directory\n")
                rc = EX_FAILURE
        else:
            regular_files.append(f)

    if not regular_files and not dirs:
        if do_follow:
            tail_f([], [], point, type_)
        else:
            if do_reverse:
                print_tail_r(sys.stdin, point, type_)
            else:
                print_tail(sys.stdin, point, type_)
    else:
        for i, file_path in enumerate(regular_files):
            if not os.path.exists(file_path) and do_follow:
                continue
                
            try:
                with open(file_path, 'r') as fh:
                    if len(regular_files) > 1:
                        print(f"==> {file_path} <==\n")
                        
                    if do_reverse:
                        print_tail_r(fh, point, type_)
                    else:
                        print_tail(fh, point, type_)
                        
                    if i < len(regular_files) - 1:
                        print()
                        
            except IOError as e:
                sys.stderr.write(f"tail: Couldn't open '{file_path}': {e}\n")
                rc = EX_FAILURE

        if do_follow:
            tail_f(regular_files, dirs, point, type_)
            
    return rc

if __name__ == "__main__":
    exit_code = handle_args()
    sys.exit(exit_code)
