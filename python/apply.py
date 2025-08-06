#!/usr/bin/env python3
"""
Name: apply
Description: run a command many times with different arguments
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import re
import subprocess
import shlex

# This global variable tracks the overall exit status.
exit_status = 0

def run_command(command, is_debug=False):
    """
    Executes a command, either as a list or a shell string.
    Updates the global exit_status if an error occurs.
    """
    global exit_status
    
    if is_debug:
        # For display, safely join list elements into a string.
        if isinstance(command, list):
            print(f"exec: {shlex.join(command)}")
        else:
            print(f"exec: {command}")
        return

    try:
        # If the command is a list, run it directly.
        # If it's a string, it needs to be interpreted by the shell.
        if isinstance(command, list):
            proc = subprocess.run(command)
        else:
            proc = subprocess.run(command, shell=True)
            
        if proc.returncode != 0:
            exit_status = 1

    except Exception as e:
        print(f"{os.path.basename(sys.argv[0])}: command failed: {e}", file=sys.stderr)
        exit_status = 1


def main():
    """Parses arguments and applies the command to the arguments."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]

    # --- 1. Manual Argument Parsing ---
    argc = 1
    is_debug = False
    magic_char = '%'

    while args and args[0].startswith('-'):
        arg = args.pop(0)
        
        if arg == '--':
            break # Stop option processing
        
        elif arg == '-d':
            is_debug = True
            
        elif arg.startswith('-a'):
            magic_char = arg[2:]
            if not magic_char: # Handle '-a c' case
                if not args:
                    print(f"{program_name}: option -a requires an argument", file=sys.stderr)
                    sys.exit(1)
                magic_char = args.pop(0)
            if len(magic_char) != 1:
                print(f"{program_name}: invalid magic specification", file=sys.stderr)
                sys.exit(1)

        elif re.match(r'^-(\d+)$', arg):
            argc = int(arg[1:])
            
        else:
            print(f"{program_name}: invalid option: {arg}", file=sys.stderr)
            sys.exit(1)

    if len(args) < 2:
        print(f"usage: {program_name} [-a c] [-d] [-#] command argument [argument ...]", file=sys.stderr)
        sys.exit(1)
        
    command = args.pop(0)
    
    # --- 2. Mode Detection and Execution ---
    
    # Find all magic placeholders, e.g., %1, %2
    placeholders = [int(n) for n in re.findall(re.escape(magic_char) + r'(\d+)', command)]
    
    if placeholders:
        # --- Substitution Mode ---
        # The number of args to consume is the highest placeholder number.
        num_args_to_consume = max(placeholders)
        
        while len(args) >= num_args_to_consume:
            current_args = args[:num_args_to_consume]
            args = args[num_args_to_consume:]
            
            new_command = command
            # Replace placeholders like %1 with the corresponding argument.
            for i in range(1, num_args_to_consume + 1):
                placeholder = f"{magic_char}{i}"
                # shlex.quote makes the substitution safe for the shell.
                replacement = shlex.quote(current_args[i - 1])
                new_command = new_command.replace(placeholder, replacement)
            
            run_command(new_command, is_debug)

    else:
        # --- Appending Mode ---
        if argc == 0:
            # -0 is a special case: run the command once for each argument, with no args.
            for _ in args:
                run_command([command], is_debug)
            args = [] # All arguments are consumed
        else:
            while len(args) >= argc:
                current_args = args[:argc]
                args = args[argc:]
                
                command_to_run = [command] + current_args
                run_command(command_to_run, is_debug)

    if args:
        print(f"{program_name}: unexpected number of leftover arguments: {' '.join(args)}", file=sys.stderr)
        global exit_status
        exit_status = 1
        
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
