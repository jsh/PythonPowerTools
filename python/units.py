#!/usr/bin/env python3

"""
Name: units
Description: conversion program
Author: Mark-Jason Dominus, mjd-perl-units@plover.com
License: gpl
"""

import sys
import os
import re
import argparse
from functools import partial
from math import log10, floor
from collections import deque

# Global state for definitions
unittab = {}
PREF = {}
PARSE_ERROR = None
VERSION = '1.02'

def debug_print(level, message, indent=0):
    """Simple debugging function based on environment variables."""
    debug_env = os.environ.get('UNITS_DEBUG')
    if debug_env is not None and level in debug_env:
        print(' ' * indent + f"{level}>>> {message}", file=sys.stderr)

# Metric prefixes. Must be powers of ten.
PREF = {
    'yotta': 24, 'zetta': 21, 'atto': -18, 'femto': -15, 'pico': -12, 'nano': -9,
    'micro': -6, 'milli': -3, 'centi': -2, 'deci': -1, 'deca': 1, 'deka': 1,
    'hecto': 2, 'hect': 2, 'kilo': 3, 'myria': 4, 'mega': 6, 'giga': 9, 'tera': 12,
    'zepto': -21, 'yocto': -24,
}
PREF_RE = '|'.join(re.escape(p) for p in sorted(PREF.keys(), key=lambda p: PREF[p]))

def usage():
    """Prints usage message and exits."""
    sys.stderr.write("usage: units [-f unittab] [have_unit want_unit]\n")
    sys.exit(2)

def is_Zero(unit_dict):
    """Checks if a unit dictionary represents a zero value."""
    if 'Temperature' in unit_dict and unit_dict['Temperature']:
        return False
    return unit_dict['_'] == 0

def unit_lookup(name):
    """Looks up a unit name, handling plurals and prefixes."""
    global PARSE_ERROR
    
    debug_print('l', f"Looking up unit '{name}'")
    
    if name in unittab:
        return unittab[name]

    if name.endswith('s') and name[:-1] in unittab:
        return unittab[name[:-1]]
    
    match = re.match(f'({PREF_RE})(.*)', name)
    if match:
        prefix, rest = match.groups()
        base_unit = unit_lookup(rest)
        if not is_Zero(base_unit):
            return con_multiply(base_unit, 10**PREF[prefix])

    PARSE_ERROR = f"Unknown unit '{name}'"
    return {'_': 0}

def unit_multiply(u1, u2):
    """Multiplies two unit dictionaries."""
    debug_print('o', f"Multiplying {u1} by {u2}")
    result = u1.copy()
    result['_'] *= u2['_']
    for key, val in u2.items():
        if key != '_':
            result[key] = result.get(key, 0) + val
    debug_print('o', f"\tResult: {result}")
    return result

def unit_divide(u1, u2):
    """Divides two unit dictionaries."""
    debug_print('o', f"Dividing {u1} by {u2}")
    if u2['_'] == 0:
        raise ValueError("Division by zero error")
    result = u1.copy()
    result['_'] /= u2['_']
    for key, val in u2.items():
        if key != '_':
            result[key] = result.get(key, 0) - val
    debug_print('o', f"\tResult: {result}")
    return result

def unit_power(base_unit, power):
    """Raises a unit to a power."""
    debug_print('o', f"Raising unit {base_unit} to power {power}")
    if not isinstance(power, int):
        raise ValueError(f"Nonintegral power {power}")
    result = base_unit.copy()
    result['_'] **= power
    for key in list(result.keys()):
        if key != '_':
            result[key] *= power
    debug_print('o', f"\tResult: {result}")
    return result

def unit_dimensionless(value):
    """Creates a dimensionless unit from a constant."""
    debug_print('o', f"Turning {value} into a dimensionless unit.")
    return {'_': value}

def con_multiply(unit_dict, constant):
    """Multiplies a unit dictionary by a constant."""
    debug_print('o', f"Multiplying unit {unit_dict} by constant {constant}.")
    result = unit_dict.copy()
    result['_'] *= constant
    debug_print('o', f"\tResult: {result}")
    return result

def is_dimensionless(unit_dict):
    """Checks if a unit dictionary is dimensionless."""
    for key, val in unit_dict.items():
        if key != '_' and val != 0:
            return False
    return True

def text_unit(unit_dict):
    """Converts a unit dictionary to a human-readable string."""
    pos, neg = [], []
    const = unit_dict['_']
    
    for k, v in unit_dict.items():
        if k != '_' and k != 'hof' and v > 0:
            pos.append((k, v))
        elif k != '_' and k != 'hof' and v < 0:
            neg.append((k, -v))
            
    pos_str = []
    for k, v in pos:
        pos_str.append(k + (f"^{v}" if v > 1 else ""))
    neg_str = []
    for k, v in neg:
        neg_str.append(k + (f"^{v}" if v > 1 else ""))
    
    output = f"{const:.6g} " if const != 1 else ""
    output += ' '.join(pos_str)
    
    if neg_str:
        output += " per "
        output += ' '.join(neg_str)
        
    return output.strip()

# The parser is a port of a state machine in the original Perl script.
def parse_unit(s):
    """Lexes and parses a unit string."""
    s = s.strip()
    
    if not s:
        return {'_': 0}
        
    tokens = lex(s)
    
    stack = []
    
    def reduce(rule, op=None):
        nonlocal tokens
        
        args = stack[-rule:]
        stack[:] = stack[:-rule]
        
        if op:
            if op == unit_lookup:
                val = op(args[0][1])
            elif op == unit_dimensionless:
                val = op(args[0][1])
            elif op == con_multiply:
                val = op(args[0][1], args[1][1])
            elif op == unit_multiply:
                val = op(args[0][1], args[1][1])
            elif op == unit_divide:
                val = op(args[0][1], args[1][1])
            elif op == unit_power:
                val = op(args[0][1], args[1][1])
            else:
                val = args[0][1]
        else:
            val = args[0][1]

        stack.append((rule, val))

    while tokens:
        token = tokens.pop(0)
        
        if token in ['*', '-']:
            reduce(1, con_multiply)
            stack.append((1, token))
        elif token in ['/']:
            reduce(1, unit_divide)
            stack.append((1, token))
        elif token in ['^']:
            reduce(1, unit_power)
            stack.append((1, token))
        else:
            val = token
            stack.append((0, val))

    if len(stack) > 1:
        if stack[-1][0] == 0:
            reduce(1, unit_dimensionless)
        if stack[-2][1] == '*':
            reduce(3, unit_multiply)
        elif stack[-2][1] == '/':
            reduce(3, unit_divide)
        elif stack[-2][1] == '^':
            reduce(3, unit_power)
            
    return stack[0][1]

def lex(s):
    """Tokenizes the input string."""
    tokens = re.split(r'(\s*[/()*-]\s*|\s*per\s*|\b[a-zA-Z_]+\b|\d+\.\d+(?:[eE][+-]?\d+)?|\d+)', s)
    tokens = [t.strip() for t in tokens if t and t.strip()]
    return tokens

def read_unittab(filename=None):
    """Reads definitions from the units file or internal data."""
    global unittab
    
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                read_defs(f)
        except IOError as e:
            sys.stderr.write(f"Could not open <{filename}>: {e}\n")
            sys.exit(2)
    else:
        # Use internal data
        data_start = sys.stdin.readlines().index('__END__\n')
        with open(sys.argv[0], 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[data_start + 1:]:
                read_defs([line])

def read_defs(lines):
    """Parses unit definitions from an iterable of lines."""
    global unittab, PARSE_ERROR
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        name, rest = re.split(r'\s+', line, 1)
        
        # Handle special temperature definitions
        if rest.startswith('{'):
            try:
                temp_dict = eval(rest)
                if 'to' in temp_dict and 'from' in temp_dict:
                    unittab[name] = {'_': 1, 'hof': temp_dict, 'Temperature': 1}
                else:
                    sys.stderr.write(f"Parse error: malformed temperature definition for {name}\n")
            except (SyntaxError, NameError):
                sys.stderr.write(f"Parse error: malformed temperature definition for {name}\n")
            continue
            
        value = parse_unit(rest)
        
        if is_Zero(value):
            sys.stderr.write(f"Parse error: {PARSE_ERROR}. Skipping line: {line}\n")
        elif '*' in rest: # Fundamental unit
            unittab[name] = {'_': 1, name: 1}
        else:
            unittab[name] = value

def main():
    """Main function to handle interactive or command-line mode."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-f', type=str, help='Use specified definition file.')
    parser.add_argument('units', nargs='*', help='Units to convert.')
    
    args = parser.parse_args()
    
    if args.f:
        read_unittab(args.f)
    else:
        read_unittab()

    if len(args.units) == 2:
        have_str, want_str = args.units
        have_hr = {'have': have_str, 'hu': parse_unit(have_str), 'neg': False, 'quan': bool(re.match(r'^-?[\d.]+', have_str))}
        want_hr = {'want': want_str, 'wu': parse_unit(want_str)}
        
        if is_Zero(have_hr['hu']) or is_Zero(want_hr['wu']):
            sys.stderr.write(f"Error: {PARSE_ERROR}\n")
            sys.exit(2)
            
        result = unit_convert(have_hr, want_hr)
        print_result(result)
        
    elif len(args.units) == 0:
        while True:
            try:
                have_str = input("You have: ")
                if not have_str.strip():
                    break
                
                want_str = input("You want: ")
                if not want_str.strip():
                    break
                    
                have_hr = {'have': have_str, 'hu': parse_unit(have_str), 'neg': False, 'quan': bool(re.match(r'^-?[\d.]+', have_str))}
                want_hr = {'want': want_str, 'wu': parse_unit(want_str)}
                
                if is_Zero(have_hr['hu']) or is_Zero(want_hr['wu']):
                    sys.stderr.write(f"Error: {PARSE_ERROR}\n")
                    continue
                    
                result = unit_convert(have_hr, want_hr)
                print_result(result)
            except (KeyboardInterrupt, EOFError):
                print()
                break
    else:
        usage()
        
    sys.exit(0)

def unit_convert(have_hr, want_hr):
    """Performs the conversion logic."""
    have_str = have_hr['have']
    hu = have_hr['hu']
    is_negative = have_hr['neg']
    is_quantified = have_hr['quan']
    
    want_str = want_hr['want']
    wu = want_hr['wu']
    
    # Handle temperature conversion
    if 'Temperature' in hu and 'Temperature' in wu:
        have_val = 0
        if is_quantified:
            have_val = float(re.match(r'^-?[\d.]+', have_str).group(0))
            if is_negative:
                have_val *= -1
        
        kelvin_val = hu['hof']['to'](have_val)
        converted_val = wu['hof']['from'](kelvin_val)
        
        return {'type': 'temperature', 'v': have_val, 'have': have_str, 't': converted_val, 'want': want_str}
        
    # Handle standard units
    quotient = unit_divide(hu, wu)
    if is_dimensionless(quotient):
        return {'type': 'dimless', 'q': quotient['_'], 'p': 1 / quotient['_']}
    else:
        return {'type': 'error', 'msg': "Conformability (Not the same dimension)\n" +
                                        f"\t{have_str} is {text_unit(hu)}\n" +
                                        f"\t{want_str} is {text_unit(wu)}\n"}

def print_result(result):
    """Formats and prints the conversion result."""
    if result['type'] == 'temperature':
        print(f"\t{result['v']:.6g} {result['have']} is {result['t']:.6g} {result['want']}")
    elif result['type'] == 'dimless':
        print(f"\t* {result['q']:.6g}")
        print(f"\t/ {result['p']:.6g}")
    else:
        print(result['msg'])

if __name__ == '__main__':
    # Initialize the unittab with internal data before running main
    read_unittab()
    main()
