#!/usr/bin/env python3

"""
Name: ls
Description: list file/directory information
Author: Mark Leighton Fisher, fisherm@tce.com
License: perl
"""

import sys
import os
import re
import stat
import time
from datetime import datetime
import shutil
import getpass
import pwd
import grp
import textwrap
import argparse
from collections import defaultdict
from pathlib import Path

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
SIX_MONTHS_SECONDS = 60 * 60 * 24 * (365 / 2)
PROGRAM = 'ls'

def get_columns():
    """Tries to determine terminal width, falls back to a default."""
    try:
        return shutil.get_terminal_size().columns
    except (shutil.Error, OSError):
        return 80

def format_mode(mode):
    """
    Formats the file mode into a human-readable string (e.g., '-rwxr-xr-x').
    This is a direct port of the original Perl function.
    """
    perms = ['---', '--x', '-w-', '-wx', 'r--', 'r-x', 'rw-', 'rwx']
    ftype_map = {
        stat.S_IFIFO: 'p',
        stat.S_IFCHR: 'c',
        stat.S_IFDIR: 'd',
        stat.S_IFBLK: 'b',
        stat.S_IFREG: '-',
        stat.S_IFLNK: 'l',
        stat.S_IFSOCK: 's',
    }
    
    file_type = ftype_map.get(stat.S_IFMT(mode), '?')
    
    # Handle setuid, setgid, and sticky bits
    perm_str_list = [
        perms[(mode & 0o700) >> 6],
        perms[(mode & 0o070) >> 3],
        perms[mode & 0o007]
    ]

    if (mode & stat.S_ISUID) and (mode & stat.S_IXUSR):
        perm_str_list[0] = perm_str_list[0].replace('x', 's')
    elif (mode & stat.S_ISUID):
        perm_str_list[0] = perm_str_list[0].replace('-', 'S')
    
    if (mode & stat.S_ISGID) and (mode & stat.S_IXGRP):
        perm_str_list[1] = perm_str_list[1].replace('x', 's')
    elif (mode & stat.S_ISGID):
        perm_str_list[1] = perm_str_list[1].replace('-', 'S')
        
    if (mode & stat.S_ISVTX) and (mode & stat.S_IXOTH):
        perm_str_list[2] = perm_str_list[2].replace('x', 't')
    elif (mode & stat.S_ISVTX):
        perm_str_list[2] = perm_str_list[2].replace('-', 'T')

    return file_type + "".join(perm_str_list)

def get_pwuid(uid):
    """Safely get username from uid."""
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)

def get_grgid(gid):
    """Safely get group name from gid."""
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)

def get_dir_entries(path, options):
    """
    Reads directory entries and their attributes. Handles single file paths.
    Returns a tuple of (entry_names, attributes_dict, total_blocks).
    """
    entries = []
    attributes = {}
    total_blocks = 0
    
    is_dir = Path(path).is_dir() and not options.get('d')
    
    if not is_dir:
        try:
            p = Path(path)
            if not p.exists() and not p.is_symlink():
                raise FileNotFoundError
            
            entry_name = p.name if not Path(path).is_absolute() else str(p)
            entries.append(entry_name)
            
            # Use lstat for symbolic links to get info about the link itself
            attributes[entry_name] = p.lstat() if p.is_symlink() else p.stat()
            total_blocks = attributes[entry_name].st_blocks if hasattr(attributes[entry_name], 'st_blocks') else 0
            
        except FileNotFoundError:
            sys.stderr.write(f"ls: cannot access '{path}': No such file or directory\n")
            return None, None, None
        except OSError as e:
            sys.stderr.write(f"ls: cannot access '{path}': {e.strerror}\n")
            return None, None, None
    else:
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if not options.get('a') and entry.name.startswith('.'):
                        continue
                    entries.append(entry.name)
                    attributes[entry.name] = entry.stat()
                    total_blocks += attributes[entry.name].st_blocks if hasattr(attributes[entry.name], 'st_blocks') else 0
        except OSError as e:
            sys.stderr.write(f"ls: failed to open directory '{path}': {e.strerror}\n")
            return None, None, None
            
    return entries, attributes, total_blocks

def order_entries(entries, attributes, options):
    """Sorts entries based on specified options."""
    if options.get('f'):
        return entries
    
    def sort_key(entry):
        entry_stat = attributes.get(entry)
        
        # Sort by modification time
        if options.get('t'):
            return entry_stat.st_mtime if entry_stat else -1
        # Sort by access time
        elif options.get('u'):
            return entry_stat.st_atime if entry_stat else -1
        # Sort by change time (ctime on Unix, creation time on Windows)
        elif options.get('c'):
            return entry_stat.st_ctime if entry_stat else -1
        # Sort by size
        elif options.get('S'):
            return entry_stat.st_size if entry_stat else -1
        # Default sort by name
        else:
            return entry

    sorted_entries = sorted(entries, key=sort_key, reverse=True if options.get('t') or options.get('u') or options.get('S') else False)
    
    if options.get('r'):
        sorted_entries.reverse()

    return sorted_entries

def format_entry(entry, path, attributes, options):
    """
    Formats a single directory entry for long listing or inode/size info.
    Returns the formatted string.
    """
    s = attributes[entry]
    
    # Inode and size blocks
    output = ""
    if options.get('i'):
        output += f"{s.st_ino:10d} "
    
    if options.get('s'):
        blocks = s.st_blocks if hasattr(s, 'st_blocks') else (s.st_size + 511) // 512
        output += f"{blocks:4d} "
    
    # Long format
    if options.get('l'):
        mode_str = format_mode(s.st_mode)
        
        # Use numeric UID/GID if -n is specified
        uid = str(s.st_uid) if options.get('n') else get_pwuid(s.st_uid)
        gid = str(s.st_gid) if options.get('n') else get_grgid(s.st_gid)

        mtime = datetime.fromtimestamp(s.st_mtime)
        now = datetime.now()
        six_months_ago = now - timedelta(seconds=SIX_MONTHS_SECONDS)
        
        if mtime > six_months_ago:
            time_str = mtime.strftime('%b %d %H:%M')
        else:
            time_str = mtime.strftime('%b %d  %Y')

        size = s.st_size
        
        # Special case for device files
        if stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):
            major_dev = os.major(s.st_rdev) if hasattr(os, 'major') else 0
            minor_dev = os.minor(s.st_rdev) if hasattr(os, 'minor') else 0
            size_str = f"{major_dev:4d},{minor_dev:4d}"
        else:
            size_str = f"{size:9d}"

        output += f"{mode_str} {s.st_nlink:3d} {uid:<8} {gid:<8} {size_str} {time_str} "
        
    # Append filename, handling symlinks
    filename_str = entry
    if stat.S_ISLNK(s.st_mode):
        try:
            target = os.readlink(os.path.join(path, entry))
            filename_str = f"{entry} -> {target}"
        except OSError:
            pass

    output += filename_str

    return output

def list_files(file_paths, dir_paths, options):
    """Handles the main listing logic for files and directories."""
    
    first_output = True
    
    # Process regular files first
    regular_files_to_list = [f for f in file_paths if os.path.exists(f) and not os.path.isdir(f)]
    if regular_files_to_list:
        file_entries, file_attrs, _ = get_dir_entries('.', options)
        
        # Filter for the specific files passed as arguments
        file_entries = [f for f in file_entries if f in regular_files_to_list]

        if file_entries:
            # Sort files
            sorted_files = order_entries(file_entries, file_attrs, options)
            
            if options.get('l') or options.get('1'):
                for file_entry in sorted_files:
                    print(format_entry(file_entry, '.', file_attrs, options))
            else:
                columns = options.get('w', get_columns())
                print_multi_column(sorted_files, columns)
            
            first_output = False

    # Then process directories
    for path in dir_paths:
        if not first_output:
            print()
        
        dir_entries, dir_attrs, total_blocks = get_dir_entries(path, options)
        
        if dir_entries:
            if len(dir_paths) > 1 or regular_files_to_list:
                print(f"{path}:")
                
            if options.get('l'):
                # In long format, `ls` prepends a 'total' line
                print(f"total {total_blocks // 2}") # Units are 512-byte blocks
                
            sorted_entries = order_entries(dir_entries, dir_attrs, options)

            if options.get('l') or options.get('1'):
                for entry in sorted_entries:
                    print(format_entry(entry, path, dir_attrs, options))
            else:
                columns = options.get('w', get_columns())
                print_multi_column(sorted_entries, columns)
                
            first_output = False
            
    if not regular_files_to_list and not dir_paths:
        # If no files specified, list current directory
        list_files([], ['.'], options)
        
def print_multi_column(entries, columns):
    """Prints a list of entries in multiple columns."""
    if not entries:
        return
        
    max_len = max(len(entry) for entry in entries) + 2
    num_cols = max(1, columns // max_len)
    num_rows = (len(entries) + num_cols - 1) // num_cols
    
    padded_entries = [f'{e:<{max_len}}' for e in entries]
    
    for row in range(num_rows):
        line = ""
        for col in range(num_cols):
            index = row + col * num_rows
            if index < len(padded_entries):
                line += padded_entries[index]
        print(line.rstrip())

def run(args):
    """Main function to process command-line arguments and run the ls command."""
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    
    parser.add_argument('-1', action='store_true', help='List one entry per line.')
    parser.add_argument('-a', action='store_true', help='List all files including dotfiles.')
    parser.add_argument('-c', action='store_true', help='Sort by inode change time.')
    parser.add_argument('-d', action='store_true', help='List directory information, not contents.')
    parser.add_argument('-f', action='store_true', help='Do not sort.')
    parser.add_argument('-i', action='store_true', help='List file inode number.')
    parser.add_argument('-k', action='store_true', help='List size in 1024-byte blocks (with -s).')
    parser.add_argument('-l', action='store_true', help='Use long format.')
    parser.add_argument('-n', action='store_true', help='List numeric UID and GID.')
    parser.add_argument('-r', action='store_true', help='Reverse sort order.')
    parser.add_argument('-s', action='store_true', help='List size in 512-byte blocks.')
    parser.add_argument('-t', action='store_true', help='Sort by modification time.')
    parser.add_argument('-u', action='store_true', help='Sort by access time.')
    parser.add_argument('-w', type=int, help='Set column width.')
    
    options = vars(parser.parse_args(args))
    
    # Handle option overrides and default behaviors
    if options.get('1') or not sys.stdout.isatty():
        options['1'] = True
        options['l'] = False
    if options.get('f'):
        options['a'] = True
    
    # Separate files and directories
    files, dirs = [], []
    if not args:
        dirs.append('.')
    else:
        for arg in args:
            path = Path(arg)
            if path.is_dir() and not options.get('d'):
                dirs.append(arg)
            else:
                files.append(arg)
    
    list_files(files, dirs, options)
    
if __name__ == '__main__':
    run(sys.argv[1:])
