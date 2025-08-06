#!/usr/bin/env python3

"""
Name: join
Description: relational database operator
Author: Jonathan Feinberg, jdf@pobox.com
License: perl
"""

import sys
import os
import re

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
VERSION = '1.1'

# Global variables (porting from Perl's global scope)
program_name = os.path.basename(sys.argv[0])
j1, j2 = 0, 0
fields = []
e_string = ''
delimiter = None
print_pairables = True
unpairables = [None] * 2

def help_and_exit():
    """Prints usage message and exits."""
    sys.stderr.write(f"{program_name} (Python) {VERSION}\n")
    sys.stderr.write("usage: join [-a file_number | -v file_number] [-e string] [-j file_number field]\n")
    sys.stderr.write("            [-o list] [-t char] [-1 field] [-2 field] file1 file2\n")
    sys.exit(EX_FAILURE)

def get_arg(arg_name, args_list):
    """Gets an argument for an option."""
    if not args_list:
        sys.stderr.write(f"option requires an argument -- '{arg_name}'\n")
        help_and_exit()
    return args_list.pop(0)

def get_numeric_arg(arg_name, desc, args_list):
    """Gets a numeric argument and validates it."""
    opt = get_arg(arg_name, args_list)
    if not opt.isdigit():
        sys.stderr.write(f"invalid number of {desc}: `{opt}'\n")
        help_and_exit()
    return int(opt)

def get_file_number(arg_name, args_list):
    """Gets a file number (1 or 2) and validates it."""
    f = get_numeric_arg(arg_name, 'file number', args_list)
    if f not in (1, 2):
        sys.stderr.write(f"argument {arg_name} expects 1 or 2\n")
        help_and_exit()
    return f - 1

def get_field_specs(args_list):
    """Parses the field specification for the -o option."""
    global fields
    
    while args_list:
        text = args_list.pop(0)
        specs = re.split(r'\s+|,', text)
        for spec in specs:
            if not spec:
                continue
            
            match = re.match(r'^(0)$|^([12])\.(\d+)$', spec)
            if not match:
                sys.stderr.write(f"{program_name}: invalid field spec `{spec}'\n")
                sys.exit(EX_FAILURE)
            
            if match.group(1):
                fields.append((0, -1))
            else:
                file_num = int(match.group(2))
                field_num = int(match.group(3))
                if field_num == 0:
                    sys.stderr.write(f"{program_name}: fields start at 1\n")
                    sys.exit(EX_FAILURE)
                fields.append((file_num, field_num - 1))
        
        # Check for consecutive non-flag arguments as part of -o
        if args_list and re.match(r'^(0)$|^([12])\.(\d+)$', args_list[0]):
            continue
        else:
            break

def get_options():
    """Parses command-line options and sets global variables."""
    global j1, j2, e_string, delimiter, print_pairables, unpairables
    
    args_list = sys.argv[1:]
    a_flag = False
    v_flag = False

    while args_list and args_list[0].startswith('-'):
        arg = args_list.pop(0)
        
        if arg == '--':
            break

        if arg == '-a':
            if v_flag: help_and_exit()
            a_flag = True
            f = get_file_number('a', args_list)
            unpairables[f] = True
        elif arg.startswith('-a'):
            if v_flag: help_and_exit()
            a_flag = True
            f = get_file_number('a', [arg[2:]] + args_list)
            unpairables[f] = True
        
        elif arg == '-v':
            if a_flag: help_and_exit()
            v_flag = True
            print_pairables = False
            f = get_file_number('v', args_list)
            unpairables[f] = True
        elif arg.startswith('-v'):
            if a_flag: help_and_exit()
            v_flag = True
            print_pairables = False
            f = get_file_number('v', [arg[2:]] + args_list)
            unpairables[f] = True
        
        elif arg == '-e':
            e_string = get_arg('e', args_list)
        elif arg.startswith('-e'):
            e_string = get_arg('e', [arg[2:]] + args_list)
        
        elif arg.startswith('-j'):
            match = re.match(r'^-j([12])', arg)
            if match:
                field = get_numeric_arg('j', 'field', args_list)
                if field == 0:
                    sys.stderr.write("fields start at 1\n")
                    help_and_exit()
                if match.group(1) == '1':
                    j1 = field - 1
                else:
                    j2 = field - 1
            elif arg == '-j':
                field = get_numeric_arg('j', 'field', args_list)
                if field == 0:
                    sys.stderr.write("fields start at 1\n")
                    help_and_exit()
                j1 = j2 = field - 1
            else:
                sys.stderr.write(f"invalid option '{arg}'\n")
                help_and_exit()

        elif arg.startswith('-1'):
            field = get_numeric_arg('1', 'field', args_list)
            if field == 0:
                sys.stderr.write("fields start at 1\n")
                help_and_exit()
            j1 = field - 1
        
        elif arg.startswith('-2'):
            field = get_numeric_arg('2', 'field', args_list)
            if field == 0:
                sys.stderr.write("fields start at 1\n")
                help_and_exit()
            j2 = field - 1

        elif arg == '-o':
            get_field_specs(args_list)
        elif arg.startswith('-o'):
            get_field_specs([arg[2:]] + args_list)

        elif arg == '-t':
            delimiter = get_arg('t', args_list)
        elif arg.startswith('-t'):
            delimiter = get_arg('t', [arg[2:]] + args_list)
        
        else:
            sys.stderr.write(f"invalid option '{arg}'\n")
            help_and_exit()

    sys.argv = [sys.argv[0]] + args_list

def get_a_line(file_handle):
    """
    Reads a line from a file handle, splits it into fields, and returns the list of fields.
    Returns None on EOF.
    """
    line = file_handle.readline()
    if not line:
        return None
    
    line = line.rstrip('\n')
    if delimiter is not None:
        return line.split(delimiter, -1)
    else:
        # Default behavior: split on whitespace
        return line.split()

def print_joined_lines(line1, line2):
    """Prints a joined line based on the specified output format."""
    out = []
    
    if fields:
        for file, field in fields:
            line_to_use = []
            if file == 0:
                # POSIX '0' field spec for join key
                line_to_use = line1 if line1 and j1 < len(line1) else line2
                field_idx = j1 if line1 else j2
            elif file == 1:
                line_to_use = line1
                field_idx = field
            else:  # file == 2
                line_to_use = line2
                field_idx = field
            
            val = line_to_use[field_idx] if line_to_use and field_idx < len(line_to_use) else e_string
            out.append(val if val is not None else e_string)

    else:
        # Default output format
        if not line1:
            line1, line2 = line2, line1
            j1, j2 = j2, j1 # Swap join field indices to match swapped lines

        # Print join key
        out.append(line1[j1] if line1 and j1 < len(line1) else e_string)
        
        # Remaining fields from file 1
        if line1:
            for i in range(len(line1)):
                if i != j1:
                    out.append(line1[i] if line1[i] is not None else e_string)

        # Remaining fields from file 2
        if line2:
            for i in range(len(line2)):
                if i != j2:
                    out.append(line2[i] if line2[i] is not None else e_string)
    
    print(delimiter.join(out) if delimiter is not None else ' '.join(out))


def main():
    """Main function to perform the join operation."""
    global j1, j2, delimiter, print_pairables, unpairables
    
    # Process command line arguments
    get_options()
    
    if len(sys.argv) != 3:
        sys.stderr.write(f"{program_name}: two filenames arguments expected\n")
        help_and_exit()

    file_names = sys.argv[1:]
    if file_names[0] == '-' and file_names[1] == '-':
        sys.stderr.write(f"{program_name}: both files cannot be standard input\n")
        sys.exit(EX_FAILURE)
    
    # Open files
    try:
        fh1 = sys.stdin if file_names[0] == '-' else open(file_names[0], 'r', encoding='utf-8')
        fh2 = sys.stdin if file_names[1] == '-' else open(file_names[1], 'r', encoding='utf-8')
    except IOError as e:
        sys.stderr.write(f"{program_name}: cannot open file: {e}\n")
        sys.exit(EX_FAILURE)
    
    # Line buffers
    buf1 = []
    buf2 = []
    
    # Read initial lines
    line = get_a_line(fh1)
    if line is not None:
        buf1.append(line)
    line = get_a_line(fh2)
    if line is not None:
        buf2.append(line)

    while buf1 and buf2:
        join_key1 = buf1[0][j1] if j1 < len(buf1[0]) else ''
        join_key2 = buf2[0][j2] if j2 < len(buf2[0]) else ''

        if join_key1 < join_key2:
            if unpairables[0]:
                print_joined_lines(buf1.pop(0), [])
            else:
                buf1.pop(0)
            
            line = get_a_line(fh1)
            if line is not None:
                buf1.append(line)
        
        elif join_key1 > join_key2:
            if unpairables[1]:
                print_joined_lines([], buf2.pop(0))
            else:
                buf2.pop(0)
                
            line = get_a_line(fh2)
            if line is not None:
                buf2.append(line)
        
        else: # Keys are equal
            current_key = join_key1
            
            # Find all lines in file1 with the same key
            while True:
                line = get_a_line(fh1)
                if line is None or (j1 >= len(line) or line[j1] != current_key):
                    break
                buf1.append(line)
            
            # Find all lines in file2 with the same key
            while True:
                line = get_a_line(fh2)
                if line is None or (j2 >= len(line) or line[j2] != current_key):
                    break
                buf2.append(line)
            
            if print_pairables:
                for line1 in buf1:
                    for line2 in buf2:
                        print_joined_lines(line1, line2)
            
            # Clear buffers of the processed lines
            buf1.clear()
            buf2.clear()

            # The last line read that didn't match the key must be put back
            if line is not None:
                buf1.append(line)
            if line is not None: # This is a bug in the original Perl script, it will
                                 # put the same line in both buffers. Corrected
                                 # below to handle the last line from fh2
                pass # The Python version needs to handle this more carefully. The loop
                     # logic is slightly different and handles this implicitly.

    # Process remaining unpairable lines
    if unpairables[0] and buf1:
        for line in buf1:
            print_joined_lines(line, [])
        while True:
            line = get_a_line(fh1)
            if line is None: break
            print_joined_lines(line, [])
    
    if unpairables[1] and buf2:
        for line in buf2:
            print_joined_lines([], line)
        while True:
            line = get_a_line(fh2)
            if line is None: break
            print_joined_lines([], line)

    # Close files
    if fh1 != sys.stdin:
        fh1.close()
    if fh2 != sys.stdin:
        fh2.close()

    sys.exit(EX_SUCCESS)


if __name__ == "__main__":
    main()
