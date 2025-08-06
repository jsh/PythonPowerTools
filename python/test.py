#!/usr/bin/env python3

"""
Name: test
Description: condition evaluation utility
Author: Brad Appleton
License: perl
"""

import sys
import os
import stat
import time
from collections import deque

# Global variables for error handling and debugging
ERRORS = 0
DEBUG = os.environ.get('DEBUG_PPT_TEST', 0)

def dbval(value):
    """Debug utility to format a value for printing."""
    if value is None:
        return '<undef>'
    if isinstance(value, (int, float)):
        return "true" if value else "false"
    if isinstance(value, str):
        return f"'{value}'"
    return str(value)

def bad_arg(message):
    """Warn about an invalid argument."""
    global ERRORS
    sys.stderr.write(f"test: invalid argument {message}\n")
    ERRORS += 1

def number(arg):
    """Checks if an argument is a numeric value."""
    try:
        return int(arg)
    except (ValueError, TypeError):
        bad_arg(f"'{arg}' - expecting a number")
        return None

# Map test operators to Python functions.
# The `apply_op` function will handle calling these with the correct number of arguments.
TEST_OPS = {
    # Logical/grouping operators
    '(': '(',
    ')': ')',
    '!': 'not',
    '-a': 'and',
    '-o': 'or',

    # File test operators
    '-b': lambda f: stat.S_ISBLK(os.stat(f).st_mode) if os.path.exists(f) else False,
    '-c': lambda f: stat.S_ISCHR(os.stat(f).st_mode) if os.path.exists(f) else False,
    '-d': lambda f: os.path.isdir(f),
    '-e': lambda f: os.path.exists(f),
    '-f': lambda f: os.path.isfile(f),
    '-g': lambda f: (os.stat(f).st_mode & stat.S_ISGID) > 0 if os.path.exists(f) else False,
    '-h': lambda f: os.path.islink(f),
    '-k': lambda f: (os.stat(f).st_mode & stat.S_ISVTX) > 0 if os.path.exists(f) else False,
    '-l': lambda f: os.path.islink(f),
    '-p': lambda f: stat.S_ISFIFO(os.stat(f).st_mode) if os.path.exists(f) else False,
    '-r': lambda f: os.access(f, os.R_OK),
    '-s': lambda f: os.path.getsize(f) > 0 if os.path.exists(f) else False,
    '-t': lambda f: os.isatty(f),
    '-u': lambda f: (os.stat(f).st_mode & stat.S_ISUID) > 0 if os.path.exists(f) else False,
    '-w': lambda f: os.access(f, os.W_OK),
    '-x': lambda f: os.access(f, os.X_OK),
    '-B': lambda f: False, # Not directly supported in Python, as it is a heuristic.
    '-L': lambda f: os.path.islink(f),
    '-O': lambda f: os.stat(f).st_uid == os.geteuid() if os.path.exists(f) else False,
    '-G': lambda f: bad_arg("'-G' - operator not supported"),
    '-R': lambda f: os.access(f, os.R_OK),
    '-S': lambda f: stat.S_ISSOCK(os.stat(f).st_mode) if os.path.exists(f) else False,
    '-T': lambda f: False, # Not directly supported in Python, as it is a heuristic.
    '-W': lambda f: os.access(f, os.W_OK),
    '-X': lambda f: os.access(f, os.X_OK),

    # String comparisons
    '-n': lambda s: len(s) > 0,
    '-z': lambda s: len(s) == 0,
    '=': lambda s1, s2: s1 == s2,
    '!=': lambda s1, s2: s1 != s2,
    '<': lambda s1, s2: s1 < s2,
    '>': lambda s1, s2: s1 > s2,

    # Numeric comparisons
    '-eq': lambda n1, n2: number(n1) == number(n2),
    '-ne': lambda n1, n2: number(n1) != number(n2),
    '-lt': lambda n1, n2: number(n1) < number(n2),
    '-le': lambda n1, n2: number(n1) <= number(n2),
    '-gt': lambda n1, n2: number(n1) > number(n2),
    '-ge': lambda n1, n2: number(n1) >= number(n2),

    # File comparisons
    '-nt': lambda f1, f2: os.path.exists(f1) and os.path.exists(f2) and os.path.getmtime(f1) > os.path.getmtime(f2),
    '-ot': lambda f1, f2: os.path.exists(f1) and os.path.exists(f2) and os.path.getmtime(f1) < os.path.getmtime(f2),
    '-ef': lambda f1, f2: bad_arg("'-ef' - operator not supported"),
}

def apply_op(op, *args):
    """Applies a test operator to its arguments."""
    try:
        func = TEST_OPS[op]
        return bool(func(*args))
    except KeyError:
        bad_arg(f"invalid operator '{op}'")
        return None
    except (IOError, TypeError):
        return False
    except IndexError:
        bad_arg(f"argument expected after '{op}'")
        return None

def find_next_op(tokens, start_index):
    """Finds the next operator with a given precedence."""
    precedence = {'-a': 2, '-o': 1}
    op = None
    op_index = -1
    current_precedence = 0

    for i in range(start_index, len(tokens)):
        token = tokens[i]
        if token in precedence and precedence[token] > current_precedence:
            op = token
            op_index = i
            current_precedence = precedence[token]
    
    return op, op_index

def evaluate(tokens):
    """
    Evaluates a list of tokens representing a test expression.
    This implementation uses a simple precedence-based approach.
    """
    if not tokens:
        return False

    # Handle single operands
    if len(tokens) == 1:
        if tokens[0] in ['-t', '0']:
            return os.isatty(1)
        elif tokens[0].isdigit():
            return number(tokens[0]) != 0
        else:
            return len(tokens[0]) > 0

    # Handle parentheses
    while '(' in tokens:
        start = tokens.index('(')
        end = -1
        balance = 1
        for i in range(start + 1, len(tokens)):
            if tokens[i] == '(':
                balance += 1
            elif tokens[i] == ')':
                balance -= 1
            if balance == 0:
                end = i
                break
        if end == -1:
            bad_arg("unbalanced parentheses")
            return None
        
        sub_expr = tokens[start + 1:end]
        sub_result = evaluate(sub_expr)
        if sub_result is None:
            return None

        tokens = tokens[:start] + [sub_result] + tokens[end + 1:]

    # Handle negation
    while '!' in tokens:
        idx = tokens.index('!')
        if idx + 1 >= len(tokens):
            bad_arg("argument expected after '!'")
            return None
        
        result = not tokens[idx + 1]
        tokens = tokens[:idx] + [result] + tokens[idx + 2:]
        
    # Find next operator with highest precedence.
    op, op_index = find_next_op(tokens, 0)
    while op:
        left = evaluate(tokens[:op_index])
        right = evaluate(tokens[op_index + 1:])
        
        if left is None or right is None:
            return None
        
        if op == '-a':
            result = left and right
        else:  # op == '-o'
            result = left or right

        # Replace the expression with its result
        tokens = [result]
        op, op_index = find_next_op(tokens, 0)
        
    # No more logical operators, evaluate the simple expression
    if len(tokens) == 3:
        return apply_op(tokens[1], tokens[0], tokens[2])
    elif len(tokens) == 2:
        return apply_op(tokens[0], tokens[1])
    elif len(tokens) == 1:
        return bool(tokens[0])
    
    # Fallback for complex expressions
    return None

def test_main():
    """Main function to run the test utility."""
    global ERRORS
    
    args = deque(sys.argv[1:])

    # Handle '[...]' syntax
    if args and args[0] == '[':
        if args[-1] != ']':
            bad_arg("missing ']'")
            sys.exit(2)
        args.popleft()
        args.pop()
    
    if not args:
        sys.exit(1)
        
    try:
        # A simpler way to handle the tokenization and evaluation
        # is to check for specific argument patterns.
        # This is more robust than a generic expression evaluator.
        
        if len(args) == 1:
            # Lone string check (implicit -n)
            if args[0] == '-t':
                result = apply_op('-t', '1')
            else:
                result = apply_op('-n', args[0])
            sys.exit(0 if result else 1)
        elif len(args) == 2:
            # Unary operator
            op, arg = args
            result = apply_op(op, arg)
            sys.exit(0 if result else 1)
        elif len(args) == 3:
            # Binary operator
            arg1, op, arg2 = args
            result = apply_op(op, arg1, arg2)
            sys.exit(0 if result else 1)
        else:
            # Complex expressions with logical operators and parentheses.
            # This requires a more robust parser. We'll use a simplified
            # version that evaluates from left to right with precedence.
            result = evaluate(list(args))
            if result is None:
                sys.exit(2)
            sys.exit(0 if result else 1)
            
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"test: an unexpected error occurred: {e}\n")
        sys.exit(2)
        
if __name__ == "__main__":
    test_main()
