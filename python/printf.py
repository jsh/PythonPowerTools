#!/usr/bin/env python3
"""
Name: printf
Description: format and print data
Author: Tom Christiansen, tchrist@perl.com (Original Perl Author)
License: perl
"""

import sys
import os
import re
import codecs

def unescape_string(s: str) -> str:
    """
    Processes backslash escapes in a string (e.g., \\n, \\t, \\xHH, \\0NNN).
    """
    # 'unicode_escape' is the codec for handling Python-style string literals.
    return codecs.decode(s, 'unicode_escape')

def parse_format_string(format_str: str) -> list:
    """
    Parses a printf-style format string into a list of parts.
    Each part is a tuple of ('type', 'value').
    """
    # This regex captures:
    # 1. %% (a literal percent)
    # 2. %[flags][width][.precision]specifier (a format specifier)
    # 3. Any sequence of characters not containing a %
    pattern = re.compile(r'(%%|%[-+ 0#]?\d*\.?\d*[b-gijosuxX]|[^%]+)')
    parts = []
    
    for part in pattern.findall(format_str):
        if part == '%%':
            parts.append(('str', '%'))
        elif part.startswith('%'):
            specifier = part[-1]
            if specifier in 's':
                parts.append(('sfmt', part)) # String format
            elif specifier in 'b-gijouxX': # Integer/float formats
                parts.append(('nfmt', part)) # Numeric format
            else:
                parts.append(('str', part)) # Unsupported, treat as literal
        else:
            parts.append(('str', part))
            
    return parts

def main():
    """Main function to parse args and run the printf logic."""
    program_name = os.path.basename(sys.argv[0])
    
    if len(sys.argv) < 2:
        print(f"usage: {program_name} format [argument ...]", file=sys.stderr)
        sys.exit(1)

    format_string = sys.argv[1]
    args = sys.argv[2:]

    # --- Core Logic ---
    try:
        parsed_format = parse_format_string(format_string)
        
        # This loop structure emulates the 'do...while' from the Perl script,
        # which allows the format string to be reused.
        while True:
            # Keep track if we consume any arguments in this pass.
            consumed_arg = False
            
            for part_type, value in parsed_format:
                if part_type == 'str':
                    print(unescape_string(value), end='')
                
                elif part_type in ('sfmt', 'nfmt'):
                    if not args:
                        # If out of args, use a default value.
                        arg = '' if part_type == 'sfmt' else 0
                    else:
                        consumed_arg = True
                        arg = args.pop(0)

                    # Apply the format specifier to the argument.
                    if part_type == 'sfmt':
                        print(value % arg, end='')
                    else: # nfmt
                        try:
                            # Attempt to interpret the argument as a number.
                            # Handles int('0xff', 0) and int('0o77', 0)
                            if isinstance(arg, str) and arg.startswith(('0x', '0o')):
                                numeric_arg = int(arg, 0)
                            else:
                                # Try float first, then int for robustness.
                                numeric_arg = float(arg) if '.' in str(arg) else int(arg)
                            print(value % numeric_arg, end='')
                        except (ValueError, TypeError):
                            # If conversion fails, use 0, as per standard printf behavior.
                            print(value % 0, end='')
            
            # If there are no more arguments to consume, we are done.
            if not args or not consumed_arg:
                break
                
    except Exception as e:
        print(f"{program_name}: an error occurred: {e}", file=sys.stderr)
        sys.exit(1)
        
    sys.exit(0)

if __name__ == "__main__":
    main()
