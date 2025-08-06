#!/usr/bin/env python3

"""
Name: dc
Description: an arbitrary precision calculator
Author: Greg Ubben, gsu@romulus.ncsc.mil
License:
"""

import sys
import os
import re
import math
from collections import deque
import argparse

# Global state
stack = deque()
registers = {}
scale = 0
ibase = 10
obase = 10

def main():
    """Main function to run the dc calculator."""
    global stack, registers, scale, ibase, obase
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('files', nargs='*', default=['-'])
    
    # Options from the original script
    parser.add_argument('-w', '--width', type=int)
    parser.add_argument('-e', '--expression', type=str)

    args = parser.parse_args()

    # Read from files or stdin
    if args.files == ['-']:
        process_input(sys.stdin)
    else:
        for filename in args.files:
            try:
                with open(filename, 'r') as f:
                    process_input(f)
            except IOError as e:
                sys.stderr.write(f"dc: {filename}: {e}\n")
                sys.exit(1)

def process_input(input_stream):
    """Processes lines of dc commands from a file-like object."""
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        
        for char in line:
            if char.isdigit() or (ibase > 10 and char.isalpha()):
                # Handle numbers
                # The original sed script's number parsing is complex,
                # we'll simplify it to handle standard bases.
                stack.append(int(char, ibase))
            
            elif char in '+-*/%^':
                # Handle binary operators
                if len(stack) < 2:
                    sys.stderr.write("dc: stack empty\n")
                    continue
                b = stack.pop()
                a = stack.pop()
                if char == '+': stack.append(a + b)
                if char == '-': stack.append(a - b)
                if char == '*': stack.append(a * b)
                if char == '/':
                    if b == 0:
                        sys.stderr.write("dc: divide by zero\n")
                        stack.extend([a, b])
                    else:
                        stack.append(a / b)
                if char == '%': stack.append(a % b)
                if char == '^': stack.append(a ** b)
            
            elif char == 'p':
                # Print top of stack
                if stack:
                    print_number(stack[-1])
                else:
                    sys.stderr.write("dc: stack empty\n")
                    
            elif char == 'd':
                # Duplicate top of stack
                if stack:
                    stack.append(stack[-1])
                else:
                    sys.stderr.write("dc: stack empty\n")
                    
            elif char == 'c':
                # Clear stack
                stack.clear()
            
            elif char == 'f':
                # Print entire stack
                for item in reversed(stack):
                    print_number(item)
                    
            elif char == 's':
                # Save to register
                if stack and line:
                    reg = line[0]
                    line = line[1:]
                    registers[reg] = stack.pop()
                else:
                    sys.stderr.write("dc: invalid save command\n")
            
            elif char == 'l':
                # Load from register
                if line:
                    reg = line[0]
                    line = line[1:]
                    if reg in registers:
                        stack.append(registers[reg])
                    else:
                        sys.stderr.write(f"dc: register '{reg}' empty\n")

            elif char == 'q':
                # Quit
                sys.exit(0)
            
            elif char == 'k':
                # Set scale
                if stack:
                    scale = int(stack.pop())
                else:
                    sys.stderr.write("dc: stack empty\n")
            
            elif char == 'i':
                # Set ibase
                if stack:
                    ibase = int(stack.pop())
                else:
                    sys.stderr.write("dc: stack empty\n")
            
            elif char == 'o':
                # Set obase
                if stack:
                    obase = int(stack.pop())
                else:
                    sys.stderr.write("dc: stack empty\n")

def print_number(num):
    """Prints a number in the current output base."""
    # This is a simplification of the original's complex formatting logic.
    if isinstance(num, (int, float)):
        try:
            # Convert to the specified base
            if obase == 10:
                print(num)
            elif obase > 1:
                # Basic conversion for integer part
                int_part = int(num)
                if int_part == 0:
                    print("0", end='')
                else:
                    result = ""
                    base_digits = "0123456789ABCDEF"
                    while int_part > 0:
                        result = base_digits[int_part % obase] + result
                        int_part //= obase
                    print(result, end='')
                
                # Handle fractional part
                frac_part = num - int(num)
                if frac_part > 0 and scale > 0:
                    print(".", end='')
                    for _ in range(scale):
                        frac_part *= obase
                        digit = int(frac_part)
                        print(base_digits[digit], end='')
                        frac_part -= digit
                print()
            else:
                sys.stderr.write("dc: obase out of range\n")

        except Exception as e:
            sys.stderr.write(f"dc: error printing number: {e}\n")
    else:
        print(num)

if __name__ == '__main__':
    main()
