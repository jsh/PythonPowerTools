#!/usr/bin/env python3

"""
Name: ar
Description: create and maintain library archives
Author: dkulp
License: perl
"""

import sys
import os
import re
import struct
import time
from collections import OrderedDict
from datetime import datetime
import stat
import shutil

# Constants
MAGIC = b"!<arch>\n"
DELIMITER = b"`\n"
EX_SUCCESS = 0
EX_FAILURE = 1

program_name = os.path.basename(sys.argv[0])

def usage():
    """Prints usage message and exits."""
    sys.stderr.write(f"""
usage: ar -d [-v] archive file ...
  ar -m [-v] archive file ...
  ar -m [-abiv] position archive file ...
  ar -p [-v] archive [file ...]
  ar -q [-cv] archive file ...
  ar -r [-cuv] archive file ...
  ar -r [-abciuv] position archive file ...
  ar -t [-v] archive [file ...]
  ar -x [-ouv] archive [file ...]
""")
    sys.exit(EX_FAILURE)

def read_ar(archive_path):
    """
    Reads a library archive and returns its contents.
    Returns a tuple of (archive_members, file_order).
    """
    members = OrderedDict()
    file_order = []
    
    try:
        with open(archive_path, 'rb') as f:
            magic = f.read(len(MAGIC))
            if magic != MAGIC:
                sys.stderr.write(f"{program_name}: {archive_path}: Inappropriate file type or format\n")
                sys.exit(EX_FAILURE)
            
            while True:
                header = f.read(60)
                if not header:
                    break
                if len(header) != 60:
                    sys.stderr.write(f"{program_name}: {archive_path}: Inappropriate file type or format\n")
                    sys.exit(EX_FAILURE)
                    
                name_raw, modt_raw, uid_raw, gid_raw, mode_raw, size_raw, delim_raw = \
                    header[0:16], header[16:28], header[28:34], header[34:40], header[40:48], header[48:58], header[58:60]
                
                if delim_raw != DELIMITER:
                    sys.stderr.write(f"{program_name}: {archive_path}: Inappropriate file type or format\n")
                    sys.exit(EX_FAILURE)
                
                name = name_raw.decode('ascii').strip()
                modt = int(modt_raw.decode('ascii').strip())
                uid = int(uid_raw.decode('ascii').strip())
                gid = int(gid_raw.decode('ascii').strip())
                mode = int(mode_raw.decode('ascii').strip(), 8)
                size = int(size_raw.decode('ascii').strip())
                
                data = f.read(size)
                if len(data) != size:
                    sys.stderr.write(f"{program_name}: {archive_path}: Inappropriate file type or format\n")
                    sys.exit(EX_FAILURE)

                if size % 2 == 1:
                    f.seek(1, 1)

                if name.startswith('#1/'):
                    name_len = int(name[3:])
                    name = data[:name_len].decode('ascii')
                    data = data[name_len:]
                    size -= name_len
                
                if name not in members:
                    file_order.append(name)
                    members[name] = {
                        'name': name,
                        'modt': modt,
                        'uid': uid,
                        'gid': gid,
                        'mode': mode,
                        'size': size,
                        'data': data
                    }
                else:
                    sys.stderr.write(f"{program_name}: {name}: entry exists more than once in the archive.\n")
                    
    except FileNotFoundError:
        return OrderedDict(), []
    except IOError as e:
        sys.stderr.write(f"{program_name}: failed to open '{archive_path}': {e}\n")
        sys.exit(EX_FAILURE)
    
    return members, file_order

def write_ar(archive_path, members, file_order, append):
    """Writes archive members to a file."""
    
    mode = 'ab' if append and os.path.exists(archive_path) else 'wb'
    
    try:
        with open(archive_path, mode) as f:
            if mode == 'wb' or os.path.getsize(archive_path) == 0:
                f.write(MAGIC)
            
            for name in file_order:
                if name in members:
                    member = members[name]
                    
                    if len(name) > 16:
                        name_header = f'#1/{len(name):<13}'.encode('ascii')
                        size_header = f'{member["size"] + len(name):<10}'.encode('ascii')
                        
                        f.write(name_header)
                        f.write(f'{member["modt"]:<12}{member["uid"]:<6}{member["gid"]:<6}{oct(member["mode"]):<8}'.encode('ascii'))
                        f.write(size_header)
                        f.write(DELIMITER)
                        f.write(name.encode('ascii'))
                        f.write(member['data'])
                    else:
                        name_header = f'{name:<16}'.encode('ascii')
                        size_header = f'{member["size"]:<10}'.encode('ascii')
                        
                        f.write(name_header)
                        f.write(f'{member["modt"]:<12}{member["uid"]:<6}{member["gid"]:<6}{oct(member["mode"]):<8}'.encode('ascii'))
                        f.write(size_header)
                        f.write(DELIMITER)
                        f.write(member['data'])
                        
                    if member['size'] % 2 == 1:
                        f.write(b'\n')
    except IOError as e:
        sys.stderr.write(f"{program_name}: failed to open '{archive_path}': {e}\n")
        sys.exit(EX_FAILURE)

def read_file(file_path):
    """Reads a file and returns its attributes and data."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        file_stat = os.stat(file_path)
        
        return {
            'name': os.path.basename(file_path),
            'modt': int(file_stat.st_mtime),
            'uid': file_stat.st_uid,
            'gid': file_stat.st_gid,
            'mode': file_stat.st_mode,
            'size': len(data),
            'data': data
        }
    except IOError as e:
        sys.stderr.write(f"{program_name}: failed to open '{file_path}': {e}\n")
        sys.exit(EX_FAILURE)

def print_member(name, members, verbose):
    """Prints the contents of an archive member."""
    if name in members:
        if verbose:
            print(f"\n<{name}>\n")
        sys.stdout.buffer.write(members[name]['data'])
    else:
        sys.stderr.write(f"{program_name}: entry not found in archive: '{name}'\n")

def print_list(name, members, verbose):
    """Prints a listing of an archive member."""
    if name in members:
        member = members[name]
        if verbose:
            mode_str = stat.filemode(member['mode'])
            mod_time = datetime.fromtimestamp(member['modt']).strftime("%b %e %H:%M %Y")
            print(f"{mode_str} {member['uid']}/{member['gid']} {member['size']} {mod_time} {name}")
        else:
            print(name)
    else:
        sys.stderr.write(f"{program_name}: entry not found in archive: '{name}'\n")

def extract_member(name, members, verbose, set_time, update):
    """Extracts a member from the archive to the file system."""
    if name not in members:
        sys.stderr.write(f"{program_name}: {name}: not found in archive\n")
        return
        
    member = members[name]
    
    if update and os.path.exists(name):
        if os.stat(name).st_mtime >= member['modt']:
            return

    try:
        with open(name, 'wb') as f:
            f.write(member['data'])
            
        os.chmod(name, member['mode'])
        shutil.chown(name, user=member['uid'], group=member['gid'])
        if set_time:
            os.utime(name, (member['modt'], member['modt']))

        if verbose:
            print(f"x - {name}")
            
    except IOError as e:
        sys.stderr.write(f"{program_name}: {name}: {e}\n")

def main():
    """Main function to parse arguments and execute the ar command."""
    
    # Simple argument parsing to match the Perl script's behavior
    args = sys.argv[1:]
    if args and not args[0].startswith('-'):
        args[0] = '-' + args[0]
    
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    
    parser.add_argument('-d', action='store_true', help='Delete files from archive.')
    parser.add_argument('-m', action='store_true', help='Move files within archive.')
    parser.add_argument('-p', action='store_true', help='Print contents of files.')
    parser.add_argument('-q', action='store_true', help='Quick append files.')
    parser.add_argument('-r', action='store_true', help='Replace or add files.')
    parser.add_argument('-t', action='store_true', help='List files in archive.')
    parser.add_argument('-x', action='store_true', help='Extract files from archive.')
    
    parser.add_argument('-a', action='store_true', help='Position files after a member.')
    parser.add_argument('-b', action='store_true', help='Position files before a member.')
    parser.add_argument('-i', action='store_true', help='Synonym for -b.')
    parser.add_argument('-c', action='store_true', help='Create archive silently.')
    parser.add_argument('-o', action='store_true', help='Set extracted file times.')
    parser.add_argument('-u', action='store_true', help='Update files if newer.')
    parser.add_argument('-v', action='store_true', help='Verbose output.')
    
    parsed_args, extra_args = parser.parse_known_args(args)
    
    major_opts = [parsed_args.d, parsed_args.m, parsed_args.p, parsed_args.q, parsed_args.r, parsed_args.t, parsed_args.x]
    if sum(major_opts) != 1:
        usage()
        
    position = None
    if parsed_args.a or parsed_args.b or parsed_args.i:
        if not extra_args:
            usage()
        position = extra_args.pop(0)

    if not extra_args:
        sys.stderr.write(f"{program_name}: archive file required\n")
        usage()
    
    archive_path = extra_args.pop(0)
    archive_members, file_order = read_ar(archive_path)

    position_idx = None
    if position:
        if position in archive_members:
            position_idx = file_order.index(position)
            if parsed_args.b or parsed_args.i:
                pass # Already correct as we're inserting at this index
            elif parsed_args.a:
                position_idx += 1
        else:
            sys.stderr.write(f"{program_name}: {position}: archive member not found.\n")
            sys.exit(EX_FAILURE)
    
    files_to_process = extra_args
    if not files_to_process:
        if parsed_args.p or parsed_args.t or parsed_args.x:
            for name in file_order:
                if parsed_args.p:
                    print_member(name, archive_members, parsed_args.v)
                elif parsed_args.t:
                    print_list(name, archive_members, parsed_args.v)
                elif parsed_args.x:
                    extract_member(name, archive_members, parsed_args.v, parsed_args.o, parsed_args.u)
        else:
            sys.stderr.write(f"{program_name}: no archive members specified\n")
            usage()
    else:
        for file in files_to_process:
            if parsed_args.d:
                if file in archive_members:
                    del archive_members[file]
                    file_order.remove(file)
                    if parsed_args.v: print(f"d - {file}")
                else:
                    sys.stderr.write(f"{program_name}: {file}: not found in archive\n")
            
            elif parsed_args.m:
                if file in archive_members:
                    file_order.remove(file)
                    if position_idx is None:
                        file_order.append(file)
                    else:
                        file_order.insert(position_idx, file)
                    if parsed_args.v: print(f"m - {file}")
                else:
                    sys.stderr.write(f"{program_name}: {file}: not found in archive\n")

            elif parsed_args.p:
                print_member(file, archive_members, parsed_args.v)
            
            elif parsed_args.q:
                new_member = read_file(file)
                if new_member:
                    archive_members[file] = new_member
                    file_order.append(file)
                    if not parsed_args.c and parsed_args.v: print(f"a - {file}")
                
            elif parsed_args.r:
                if file in archive_members:
                    if parsed_args.u and os.path.exists(file) and os.stat(file).st_mtime <= archive_members[file]['modt']:
                        continue
                    new_member = read_file(file)
                    if new_member:
                        archive_members[file] = new_member
                        if parsed_args.v: print(f"r - {file}")
                else:
                    new_member = read_file(file)
                    if new_member:
                        if position_idx is None:
                            file_order.append(file)
                        else:
                            file_order.insert(position_idx, file)
                        archive_members[file] = new_member
                        if not parsed_args.c and parsed_args.v: print(f"a - {file}")
            
            elif parsed_args.t:
                print_list(file, archive_members, parsed_args.v)

            elif parsed_args.x:
                extract_member(file, archive_members, parsed_args.v, parsed_args.o, parsed_args.u)

    if parsed_args.d or parsed_args.m or parsed_args.q or parsed_args.r:
        if not parsed_args.c:
            sys.stderr.write(f"ar: creating {archive_path}\n")
        write_ar(archive_path, archive_members, file_order, parsed_args.q)

if __name__ == '__main__':
    main()
