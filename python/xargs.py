#!/usr/bin/env python3
"""
Name: xargs
Description: construct argument list(s) and execute utility
Author: Gurusamy Sarathy, gsar@umich.edu (Original Perl Author)
License: perl
"""

import sys
import os
import subprocess
import shlex

def execute_command(command, trace=False):
    """
    Executes a command and handles errors, returning the process exit code.
    """
    if trace:
        # shlex.join is the safe way to format a command for display.
        print(f"exec: {shlex.join(command)}", file=sys.stderr)
    
    try:
        # subprocess.run executes the command and waits for it to complete.
        proc = subprocess.run(command)
        
        # Check for the special exit status 255 mentioned in the original script.
        if proc.returncode == 255:
            print(f"{sys.argv[0]}: {command[0]}: exited with status 255", file=sys.stderr)
            sys.exit(1)
            
        return proc.returncode

    except FileNotFoundError:
        print(f"{sys.argv[0]}: {command[0]}: No such file or directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{sys.argv[0]}: {command[0]}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main function to parse args and run the xargs logic."""
    args = sys.argv[1:]
    program_name = os.path.basename(sys.argv[0])
    
    # --- 1. Manual Argument Parsing ---
    opts = {'n': None, 'L': None, 's': None, 'I': None, '0': False, 't': False}
    
    while args and args[0].startswith('-'):
        arg = args.pop(0)
        if arg == '-0': opts['0'] = True
        elif arg == '-t': opts['t'] = True
        elif arg in ('-n', '-L', '-s', '-I'):
            if not args:
                print(f"{program_name}: option requires an argument -- '{arg[1]}'", file=sys.stderr)
                sys.exit(1)
            try:
                # -I takes a string, the others take an int
                value = args.pop(0)
                opts[arg[1]] = int(value) if arg != '-I' else value
                if arg != '-I' and opts[arg[1]] <= 0:
                     print(f"{program_name}: option {arg}: number must be > 0", file=sys.stderr)
                     sys.exit(1)
            except ValueError:
                print(f"{program_name}: option {arg}: invalid number '{value}'", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Usage: {program_name} [-0t] [-n num] [-L num] [-s size] [-I repl] [prog [args ...]]", file=sys.stderr)
            sys.exit(1)

    # The base command is whatever is left in args.
    base_command = args if args else ['echo']
    
    # -I implies -L 1
    if opts['I'] is not None:
        opts['L'] = 1

    # --- 2. -I (Replace String) Mode ---
    if opts['I'] is not None:
        repl_str = opts['I']
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            
            # Create a new command by replacing the placeholder.
            command_to_run = [arg.replace(repl_str, line) for arg in base_command]
            execute_command(command_to_run, opts['t'])
        sys.exit(0)

    # --- 3. Standard Argument-Building Mode ---
    separator = '\0' if opts['0'] else None # None makes split() use whitespace
    input_args = sys.stdin.read().split(separator)
    input_args = [arg for arg in input_args if arg] # Remove empty strings

    while input_args:
        args_for_this_run = []
        
        # Determine the slice of args to take based on the -n option.
        if opts['n']:
            num_to_take = min(opts['n'], len(input_args))
            args_for_this_run = input_args[:num_to_take]
            input_args = input_args[num_to_take:]
        else:
            # If -n is not set, use all remaining args for this one run.
            args_for_this_run = input_args
            input_args = []
            
        if not args_for_this_run:
            break
            
        command_to_run = base_command + args_for_this_run
        execute_command(command_to_run, opts['t'])

if __name__ == "__main__":
    main()
