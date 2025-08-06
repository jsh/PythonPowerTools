#!/usr/bin/env python3
"""
Name: seq
Description: print a numeric sequence
Author: Michael Mikonos (Original Perl Author)
License: artistic2
"""

import sys
import os
import math
import re

def get_float(num_str: str, program_name: str) -> float:
    """
    Validates that a string is a valid floating point number and returns it.
    Exits with an error if validation fails.
    """
    # This regex matches an optional sign, digits, and an optional decimal part.
    if not re.match(r'^[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?$', num_str):
        print(f"{program_name}: invalid number '{num_str}'", file=sys.stderr)
        sys.exit(1)
    return float(num_str)

def usage(program_name: str):
    """Prints a usage message to stderr and exits with failure."""
    print(f"usage: {program_name} [-f format] [-s string] [begin [step]] end", file=sys.stderr)
    sys.exit(1)

def main():
    """Parses arguments and prints the numeric sequence."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]

    # --- 1. Set Defaults ---
    format_str = "%g"
    separator = "\n"
    
    # --- 2. Manual Argument Parsing ---
    # This is necessary to distinguish options from negative numbers.
    
    # Parse options
    while args and args[0].startswith('-'):
        opt = args.pop(0)
        if opt == '--':
            break # Stop option processing
        elif opt == '-s':
            if not args: usage(program_name)
            separator = args.pop(0)
        elif opt == '-f':
            if not args: usage(program_name)
            format_str = args.pop(0)
        elif re.match(r'^-?\d', opt):
            # This is not an option, but a negative number. Put it back.
            args.insert(0, opt)
            break
        else:
            print(f"{program_name}: unexpected option: '{opt}'", file=sys.stderr)
            usage(program_name)

    # Parse numeric arguments
    num_args = len(args)
    if num_args == 0 or num_args > 3:
        usage(program_name)
    
    start, step, end = 1.0, 1.0, None
    
    if num_args == 1:
        end = get_float(args[0], program_name)
    elif num_args == 2:
        start = get_float(args[0], program_name)
        end = get_float(args[1], program_name)
    elif num_args == 3:
        start = get_float(args[0], program_name)
        step = get_float(args[1], program_name)
        end = get_float(args[2], program_name)

    # --- 3. Validate Step Value and Direction ---
    if step == 0:
        print(f"{program_name}: illegal step value of zero", file=sys.stderr)
        sys.exit(1)
        
    # If step was not explicitly provided, infer its direction.
    if num_args < 3 and end < start and step > 0:
        step = -1.0
        
    # Validate that the step direction is correct.
    if end < start and step > 0:
        print(f"{program_name}: needs negative decrement", file=sys.stderr)
        sys.exit(1)
    if end > start and step < 0:
        print(f"{program_name}: needs positive increment", file=sys.stderr)
        sys.exit(1)
        
    # --- 4. Generate and Print the Sequence ---
    try:
        # Calculate the number of items to print upfront to avoid
        # floating-point accumulation errors.
        if step == 0 or (end > start and step < 0) or (end < start and step > 0):
             num_items = 0
        else:
             num_items = math.floor((end - start) / step) + 1
        
        for i in range(num_items):
            if i > 0:
                print(separator, end='')
            
            current_num = start + i * step
            # Use the % operator for printf-style formatting.
            print(format_str % current_num, end='')
            
        # Always print a final newline, as is standard for `seq`.
        print()
    except (TypeError, ValueError):
         # This can happen if the format string is invalid for the number type.
         print(f"{program_name}: invalid format string '{format_str}' for result", file=sys.stderr)
         sys.exit(1)
    except (IOError, KeyboardInterrupt):
        sys.stderr.close() # Silence errors on broken pipe or Ctrl+C
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
