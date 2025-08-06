#!/usr/bin/env python3
"""
Name: env
Description: run a program in a modified environment
Author: Matthew Bafford, dragons@scescape.net (Original Perl Author)
License: perl
"""

import sys
import os
import argparse

def main():
    """Parses arguments, modifies the environment, and executes a command."""
    
    args = sys.argv[1:]
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Process Options (-i, -u) ---
    while args and args[0].startswith('-'):
        arg = args.pop(0)

        if arg == '-i':
            # Clear the entire environment.
            os.environ.clear()
        
        elif arg == '-u':
            if not args:
                print(f"{program_name}: option requires an argument -- 'u'", file=sys.stderr)
                sys.exit(2)
            var_to_unset = args.pop(0)
            # Unset the specified environment variable.
            os.environ.pop(var_to_unset, None)

        elif arg.startswith('-u'):
             # Handles the case where the variable is attached, e.g., -uVAR
             var_to_unset = arg[2:]
             os.environ.pop(var_to_unset, None)
             
        elif arg == '--':
            # Stop processing options.
            break
        
        else:
            print(f"usage: {program_name} [-i] [-u name]... [name=value]... [command [args]...]", file=sys.stderr)
            sys.exit(2)

    # --- 2. Process NAME=VALUE assignments ---
    while args and '=' in args[0]:
        assignment = args.pop(0)
        try:
            name, value = assignment.split('=', 1)
            os.environ[name] = value
        except ValueError:
            # This case is unlikely given the '=' check, but safe to have.
            print(f"{program_name}: invalid assignment '{assignment}'", file=sys.stderr)
            sys.exit(2)

    # --- 3. Execute Command or Print Environment ---
    if not args:
        # If no command is left, print the (modified) environment.
