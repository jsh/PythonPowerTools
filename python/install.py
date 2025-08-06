#!/usr/bin/env python3

"""
Name: install
Description: install files and directories
Author: Greg Bacon, gbacon@itsc.uah.edu
License: perl
"""

import sys
import os
import re
import shutil
import stat
import pwd
import grp
import subprocess
from pathlib import Path

# Constants
VERSION = '1.7'
program_name = os.path.basename(sys.argv[0])

# Global variables for options and state
Unix = os.name == 'posix'
Debug = 0
Errors = 0
opt = {}

def usage():
    """Prints usage message and exits with an error."""
    sys.stderr.write(f"""Usage: {program_name} [-bCcDps] [-g group] [-m mode] [-o owner] file1 file2
       {program_name} [-bCcDps] [-g group] [-m mode] [-o owner] file ... directory
       {program_name} -d [-g group] [-m mode] [-o owner] directory ...
""")
    sys.exit(1)

def version_message():
    """Prints version message and exits."""
    print(f"{program_name} version {VERSION}")
    sys.exit(0)

def modify_file(path, mode, src_stat=None):
    """Applies mode, owner, group, and times to a file."""
    global Errors
    
    try:
        if mode is not None:
            os.chmod(path, mode)
    except OSError as e:
        sys.stderr.write(f"{program_name}: chmod {oct(mode)} {path}: {e}\n")
        Errors += 1

    if opt.get('o') is not None or opt.get('g') is not None:
        try:
            current_stat = os.stat(path)
            uid = opt.get('o', current_stat.st_uid)
            gid = opt.get('g', current_stat.st_gid)
            os.chown(path, uid, gid)
        except OSError as e:
            sys.stderr.write(f"{program_name}: chown {uid}.{gid} {path}: {e}\n")
            Errors += 1

    if opt.get('p') and src_stat:
        try:
            os.utime(path, (src_stat.st_atime, src_stat.st_mtime))
        except OSError as e:
            sys.stderr.write(f"{program_name}: utime {path}: {e}\n")
            Errors += 1

    if opt.get('s') and Path(path).is_file():
        try:
            subprocess.run(["strip", path], check=True, capture_output=True)
        except FileNotFoundError:
            sys.stderr.write(f"{program_name}: strip not found\n")
            Errors += 1
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"{program_name}: strip {path} exited with code {e.returncode}\n")
            Errors += 1

def copy_one(src, dst):
    """Copies a file, handling backups if needed."""
    global Debug
    
    if opt.get('b') and Path(dst).exists():
        backup_path = Path(dst).with_suffix('.old')
        if Debug:
            sys.stderr.write(f"{program_name}: creating backup file '{backup_path}'\n")
        
        try:
            shutil.copy2(dst, backup_path)
            os.remove(dst)
        except OSError as e:
            sys.stderr.write(f"{program_name}: rename/copy failed for '{dst}': {e}\n")
            return False
            
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as e:
        sys.stderr.write(f"{program_name}: copy failed: {src} -> {dst}: {e}\n")
        return False

def install_dirs():
    """Creates directories with specified permissions."""
    global Errors
    
    mode_str = opt.get('m', '755')
    
    # Logic to create intermediate directories (like mkdir -p)
    all_dirs = []
    for d in sys.argv[1:]:
        p = Path(d)
        all_dirs.extend(list(p.parents))
        all_dirs.append(p)
    
    unique_dirs = sorted(list(set(all_dirs)), key=lambda p: (len(p.parts), str(p)))
    
    for d in unique_dirs:
        if d.is_dir():
            continue
        try:
            os.mkdir(d, 0o755)
        except FileExistsError:
            pass # A race condition might create it between checking and creating
        except OSError as e:
            sys.stderr.write(f"{program_name}: mkdir {d}: {e}\n")
            Errors += 1
            
    # Apply permissions to explicitly requested directories
    for d in sys.argv[1:]:
        mode = None
        if not Unix:
            continue
        
        if re.fullmatch(r'[0-7]{1,4}', mode_str):
            mode = int(mode_str, 8)
        else:
            # Symbolic mode parsing is complex; using a simpler helper
            # or a library is needed here. For this port, we'll
            # hardcode an example. A full implementation would need a
            # more robust symbolic mode parser.
            try:
                mode = symbolic_mode_to_octal(mode_str, d)
            except ValueError as e:
                sys.stderr.write(f"{program_name}: invalid mode: {e}\n")
                sys.exit(1)

        modify_file(d, mode)

def symbolic_mode_to_octal(mode_str, file_path):
    """
    A simplified symbolic mode parser. This is a placeholder and not a
    complete implementation of the original Perl module's logic.
    """
    current_mode = os.stat(file_path).st_mode if Path(file_path).exists() else 0
    new_mode = current_mode

    parts = mode_str.split(',')
    for part in parts:
        match = re.match(r'([augo]*)([+\-=])([rstwxXugo]*)', part)
        if not match:
            raise ValueError(f"'{part}' is not a valid symbolic mode clause.")
            
        who, op, perms = match.groups()
        who_mask = 0
        
        if 'a' in who or not who: who_mask |= (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        if 'u' in who: who_mask |= stat.S_IRWXU
        if 'g' in who: who_mask |= stat.S_IRWXG
        if 'o' in who: who_mask |= stat.S_IRWXO

        perm_bits = 0
        if 'r' in perms: perm_bits |= stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
        if 'w' in perms: perm_bits |= stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        if 'x' in perms: perm_bits |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        
        if op == '+':
            new_mode |= perm_bits & who_mask
        elif op == '-':
            new_mode &= ~perm_bits & who_mask
        elif op == '=':
            new_mode = (new_mode & ~who_mask) | (perm_bits & who_mask)
            
    return new_mode

def install_files():
    """Installs files to a destination."""
    global Errors, Debug
    
    files_to_install = sys.argv[1:-1]
    destination = sys.argv[-1]
    
    dest_is_dir = Path(destination).is_dir()
    
    if len(files_to_install) > 1 and not dest_is_dir:
        sys.stderr.write(f"{program_name}: '{destination}' is not a directory\n")
        usage()
    if len(files_to_install) == 0:
        sys.stderr.write(f"{program_name}: missing destination file operand after '{destination}'\n")
        usage()
        
    mode_str = opt.get('m', '755')
    
    for src_file in files_to_install:
        src_path = Path(src_file)
        dst_path = Path(destination)
        
        if src_path.is_dir():
            sys.stderr.write(f"{program_name}: ignoring directory '{src_file}'\n")
            Errors += 1
            continue
            
        if dest_is_dir:
            dst_path /= src_path.name

        if opt.get('C') and dst_path.exists():
            try:
                if file_cmp(src_path, dst_path):
                    if Debug:
                        sys.stderr.write(f"{program_name}: {src_file} not copied to {dst_path}\n")
                    continue
            except OSError as e:
                sys.stderr.write(f"{program_name}: cmp failed: {e}\n")
                Errors += 1

        if Debug:
            sys.stderr.write(f"{program_name}: copy {src_file} {dst_path}\n")
            
        if not copy_one(src_path, dst_path):
            Errors += 1
            continue
            
        if Unix:
            mode = None
            if re.fullmatch(r'[0-7]{1,4}', mode_str):
                mode = int(mode_str, 8)
            else:
                try:
                    mode = symbolic_mode_to_octal(mode_str, dst_path)
                except ValueError as e:
                    sys.stderr.write(f"{program_name}: invalid mode: {e}\n")
                    sys.exit(1)
            
            src_stat = os.stat(src_path) if opt.get('p') else None
            modify_file(dst_path, mode, src_stat)

def file_cmp(file1, file2):
    """Compares two files for content equality."""
    try:
        stat1 = os.stat(file1)
        stat2 = os.stat(file2)
        if stat1.st_size != stat2.st_size:
            return False
            
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                chunk1 = f1.read(4096)
                chunk2 = f2.read(4096)
                if chunk1 != chunk2:
                    return False
                if not chunk1:
                    return True
    except OSError:
        return False

def main():
    """Main entry point for the script."""
    global opt, Debug, Errors
    
    # Process options
    try:
        from argparse import ArgumentParser
        parser = ArgumentParser(add_help=False)
        parser.add_argument('-b', action='store_true')
        parser.add_argument('-C', action='store_true')
        parser.add_argument('-c', action='store_true')
        parser.add_argument('-D', action='store_true')
        parser.add_argument('-d', action='store_true')
        parser.add_argument('-f', type=str)
        parser.add_argument('-g', type=str)
        parser.add_argument('-m', type=str)
        parser.add_argument('-o', type=str)
        parser.add_argument('-p', action='store_true')
        parser.add_argument('-s', action='store_true')
        
        parsed_args, remaining_args = parser.parse_known_args()
        
        opt = vars(parsed_args)
        
        if opt['p']:
            opt['C'] = True
        if opt['D']:
            Debug = 1
            
        if len(remaining_args) == 0:
            usage()
            
        if opt['d'] and any(opt.get(f, False) for f in ['C', 'c', 'p']):
            sys.stderr.write(f"{program_name}: -d not allowed with -[CcDp]\n")
            usage()
            
        if Unix:
            if opt['g'] and not re.match(r'^\d+$', opt['g']):
                try:
                    opt['g'] = grp.getgrnam(opt['g']).gr_gid
                except KeyError:
                    sys.stderr.write(f"{program_name}: unknown group '{opt['g']}'\n")
                    sys.exit(1)
            if opt['o'] and not re.match(r'^\d+$', opt['o']):
                try:
                    opt['o'] = pwd.getpwnam(opt['o']).pw_uid
                except KeyError:
                    sys.stderr.write(f"{program_name}: unknown user '{opt['o']}'\n")
                    sys.exit(1)
        
        sys.argv = [sys.argv[0]] + remaining_args

    except (SystemExit, ValueError) as e:
        if isinstance(e, SystemExit) and e.code == 0:
            sys.exit(0)
        usage()

    if opt['d']:
        install_dirs()
    else:
        install_files()

    sys.exit(0 if Errors == 0 else 1)

if __name__ == '__main__':
    main()
