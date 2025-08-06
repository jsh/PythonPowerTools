#!/usr/bin/env python3

"""
Name: chmod
Description: change permissions of files
Author: Abigail, perlpowertools@abigail.be
License: perl
"""

import sys
import os
import re
import stat
from functools import reduce
from pathlib import Path

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
VERSION = '1.6'

# Global variables
program_name = os.path.basename(sys.argv[0])
rc = EX_SUCCESS
options = {}

def usage():
    """Prints usage message and exits."""
    sys.stderr.write(f"usage: {program_name} [-R [-H | -L | -P]] mode file...\n")
    sys.exit(EX_FAILURE)

def mod(symbolic_mode, file_path):
    """
    Parses a symbolic mode string and applies it to a file's permissions.
    This is a port of the `SymbolicMode.pm` Perl module logic.
    """
    
    # Define permission bits and groups
    ugo = ['u', 'g', 'o']
    bits = {'s': 8, 't': 8, 'r': 4, 'w': 2, 'x': 1}
    
    # Get current permissions
    current_mode = 0
    file_exists = os.path.exists(file_path)
    if file_exists:
        try:
            current_mode = os.stat(file_path).st_mode
        except OSError:
            pass

    current_perms = {}
    for i, c in enumerate(ugo):
        current_perms[c] = (current_mode >> (6 - i * 3)) & 0b111
    
    special_bits = (current_mode >> 9) & 0b111
    current_perms['u'] |= (special_bits & 4) << 1
    current_perms['g'] |= (special_bits & 2) << 2
    current_perms['o'] |= (special_bits & 1) << 3
    
    # Umask bits
    umask_val = os.umask(0)
    os.umask(umask_val)
    umask_perms = {
        'u': (umask_val >> 6) & 0o7,
        'g': (umask_val >> 3) & 0o7,
        'o': umask_val & 0o7,
    }

    # Store original permissions for `+X` logic
    orig_mode = current_mode
    
    # Parse clauses
    for clause in symbolic_mode.split(','):
        match = re.match(r'([augo]*)([+\-=])(.*)', clause)
        if not match:
            return None
        
        who_str, operator, perms_str = match.groups()
        
        who_list = []
        if who_str:
            if 'a' in who_str: who_list = ['u', 'g', 'o']
            else: who_list = [c for c in who_str]
        else:
            who_list = ugo

        for action in re.findall(r'[rstwxXugo]+', perms_str) or ['']:
            perm_val = 0
            for p in action:
                if p in ['r', 'w', 'x']:
                    perm_val |= bits[p]
                elif p in ['u', 'g', 'o']:
                    # This logic is complex in the original, referring to the `orig_mode`
                    # For a basic port, let's assume it means "copy user's/group's/other's permissions"
                    if p == 'u': perm_val |= (orig_mode >> 6) & 0o7
                    if p == 'g': perm_val |= (orig_mode >> 3) & 0o7
                    if p == 'o': perm_val |= orig_mode & 0o7
                elif p == 'X':
                    if operator == '+':
                        if os.path.isdir(file_path) or (orig_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                            perm_val |= bits['x']
                elif p in ['s', 't']:
                    # Special bits need careful handling
                    pass

            for w in who_list:
                if operator == '+':
                    current_perms[w] |= perm_val
                elif operator == '-':
                    current_perms[w] &= ~perm_val
                elif operator == '=':
                    current_perms[w] = perm_val

    # Reassemble to octal
    new_mode = 0
    for i, c in enumerate(ugo):
        new_mode |= (current_perms[c] & 0o7) << (6 - i * 3)
    
    # Re-apply special bits (simplified)
    # The original Perl logic for special bits is quite convoluted and seems tied
    # to historical inconsistencies across different Unix flavors.
    # A standard Python port will often simplify this to the POSIX behavior.
    if 's' in symbolic_mode:
        if 'u' in who_str: new_mode |= stat.S_ISUID
        if 'g' in who_str: new_mode |= stat.S_ISGID
    if 't' in symbolic_mode:
        new_mode |= stat.S_ISVTX
        
    return oct(new_mode)

def modify_file(file_path):
    """Applies the chmod to a single file."""
    global rc, mode, symbolic, options

    try:
        if Path(file_path).is_symlink() and (options.get('L') or (options.get('H') and file_path in sys.argv[1:])):
            # This is a bit simplistic and doesn't handle loops, but follows the original script's logic
            target = os.readlink(file_path)
            modify_file(target)
            return

        if not Path(file_path).exists():
            sys.stderr.write(f"{program_name}: '{file_path}' does not exist\n")
            rc = EX_FAILURE
            return

        real_mode = mode
        if symbolic:
            real_mode = mod(mode, file_path)
            if real_mode is None:
                sys.stderr.write(f"{program_name}: invalid mode: '{mode}'\n")
                sys.exit(EX_FAILURE)
        
        os.chmod(file_path, int(real_mode, 8))
    except OSError as e:
        sys.stderr.write(f"{program_name}: failed to change mode for '{file_path}': {e}\n")
        rc = EX_FAILURE

def main():
    """Main function to parse arguments and drive the process."""
    global mode, symbolic, options, rc

    args = sys.argv[1:]
    
    # Process options, which in the original script were not Getopt-friendly
    # and require manual parsing.
    while args and args[0].startswith('-'):
        arg = args.pop(0)[1:]
        if not arg:
            break
        
        for c in reversed(arg):
            if c not in 'RHLP':
                sys.stderr.write(f"{program_name}: invalid option -- '{c}'\n")
                usage()
            
            if c == 'R':
                options['R'] = True
            elif c == 'H':
                if not options.get('R'): usage()
                options['H'] = True
                options['L'] = options['P'] = False
            elif c == 'L':
                if not options.get('R'): usage()
                options['L'] = True
                options['H'] = options['P'] = False
            elif c == 'P':
                if not options.get('R'): usage()
                options['P'] = True
                options['H'] = options['L'] = False

    if not args:
        usage()
    
    mode = args.pop(0)
    
    if not args:
        usage()

    symbolic = False
    if re.search(r'[^0-7]', mode):
        symbolic = True
    elif not re.fullmatch(r'[0-7]{1,4}', mode):
        sys.stderr.write(f"{program_name}: invalid mode: '{mode}'\n")
        sys.exit(EX_FAILURE)

    files_to_process = args
    
    if options.get('R'):
        # Using os.walk for recursion, with custom logic to handle symlinks
        for root in files_to_process:
            for dirpath, dirnames, filenames in os.walk(root):
                for d in dirnames:
                    path = os.path.join(dirpath, d)
                    modify_file(path)
                for f in filenames:
                    path = os.path.join(dirpath, f)
                    modify_file(path)
                modify_file(dirpath) # Also chmod the root of the recursion
    else:
        for file in files_to_process:
            modify_file(file)

    sys.exit(rc)

if __name__ == '__main__':
    main()
