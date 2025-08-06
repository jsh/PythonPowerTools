#!/usr/bin/env python3

"""
Name: expr
Description: evaluate expression
Author: Michael Robinson, smrf@sans.vuw.ac.nz
Author: Michael Mikonos
License: artistic2
"""

import sys
import re
from collections import deque

# Constants for exit codes
EX_TRUE = 0
EX_FALSE = 1
EX_ERROR = 2

# Token types
T_OR = 1
T_AND = 2
T_EQ = 3
T_LT = 4
T_GT = 5
T_ADD = 6
T_SUB = 7
T_MUL = 8
T_DIV = 9
T_MOD = 10
T_MATCH = 11
T_LP = 12
T_RP = 13
T_NE = 14
T_LE = 15
T_GE = 16
T_OPERAND = 17
T_EOI = 18

# Operator to token type mapping
TOK_MAP = {
    '|': T_OR,
    '&': T_AND,
    '=': T_EQ,
    '<': T_LT,
    '>': T_GT,
    '+': T_ADD,
    '-': T_SUB,
    '*': T_MUL,
    '/': T_DIV,
    '%': T_MOD,
    ':': T_MATCH,
    '(': T_LP,
    ')': T_RP,
    '!=': T_NE,
    '<=': T_LE,
    '>=': T_GE,
}

# Global state for the parser
token = None
tokval = None
args_queue = deque()

def error():
    """Prints a syntax error message and exits."""
    sys.stderr.write("expr: syntax error\n")
    sys.exit(EX_ERROR)

def make_val(value, type_str):
    """Creates a dictionary representing a typed value."""
    return {'type': type_str, 'val': value}

def make_int(i):
    """Creates a dictionary for an integer value."""
    return make_val(i, 'i')

def make_str(s):
    """Creates a dictionary for a string value."""
    return make_val(s, 's')

def is_int(val_dict):
    """Checks if a value is an integer or can be converted to one."""
    if val_dict['type'] == 'i':
        return True, val_dict['val']
    
    val = str(val_dict['val'])
    if re.fullmatch(r'[\+\-]?[0-9]+', val):
        return True, int(val)
    
    return False, 0

def to_int(val_dict):
    """Tries to convert a value to an integer in-place."""
    if val_dict['type'] == 'i':
        return True
    
    is_num, num_val = is_int(val_dict)
    if is_num:
        val_dict['type'] = 'i'
        val_dict['val'] = num_val
        return True
    
    return False

def to_str(val_dict):
    """Converts a value to a string in-place."""
    if val_dict['type'] == 's':
        return
    val_dict['type'] = 's'
    val_dict['val'] = str(val_dict['val'])

def is_zero_or_null(val_dict):
    """Checks if a value is zero (integer) or an empty string."""
    if val_dict['type'] == 'i':
        return val_dict['val'] == 0
    
    if len(str(val_dict['val'])) == 0:
        return True
    
    is_num, num_val = is_int(val_dict)
    if is_num and num_val == 0:
        return True
    
    return False

def get_tok(pat_mode):
    """
    Gets the next token from the arguments queue.
    pat_mode=0 for normal operators, pat_mode=1 for regular expression.
    """
    global token, tokval
    
    if not args_queue:
        token = T_EOI
        return
    
    p = args_queue.popleft()
    
    if pat_mode == 0 and p in TOK_MAP:
        token = TOK_MAP[p]
    else:
        tokval = make_str(p)
        token = T_OPERAND

def eval_expr(level_func, current_level_ops):
    """Generic function for evaluating expressions at a specific precedence level."""
    left = level_func()
    
    while token in current_level_ops:
        op = token
        get_tok(0)
        right = level_func()
        
        # Binary operation logic goes here
        # This function would be more complex in a full implementation,
        # but for this specific port, we'll keep the separate functions.
        pass

    return left

# Each evalX function handles a specific precedence level of operators
# eval6: Parentheses and operands
def eval6():
    """Handles operands and parentheses."""
    if token == T_OPERAND:
        val = tokval
        get_tok(0)
        return val
    elif token == T_LP:
        get_tok(0)
        v = eval0()
        if token != T_RP:
            error()
        get_tok(0)
        return v
    else:
        error()

# eval5: Match operator
def eval5():
    """Handles the match (:) operator."""
    left = eval6()
    while token == T_MATCH:
        get_tok(1)
        right = eval6()
        
        to_str(left)
        to_str(right)
        
        match_result = re.match(f'^{right["val"]}', left["val"])
        
        if match_result:
            if match_result.groups():
                v = make_str(match_result.group(1))
            else:
                v = make_int(len(match_result.group(0)))
        else:
            if re.search(r'\(.*\)', right['val']):
                v = make_str('')
            else:
                v = make_int(0)
        left = v
    return left

# eval4: Multiplication, division, and modulus
def eval4():
    """Handles multiplication, division, and modulus operators."""
    left = eval5()
    while token in (T_MUL, T_DIV, T_MOD):
        op = token
        get_tok(0)
        right = eval5()
        
        if not to_int(left):
            sys.stderr.write(f"expr: not a number: {left['val']}\n")
            sys.exit(EX_ERROR)
        if not to_int(right):
            sys.stderr.write(f"expr: not a number: {right['val']}\n")
            sys.exit(EX_ERROR)
            
        if op == T_MUL:
            try:
                left['val'] *= right['val']
            except OverflowError:
                sys.stderr.write("expr: overflow\n")
                sys.exit(EX_ERROR)
        else:
            if right['val'] == 0:
                sys.stderr.write("expr: division by zero\n")
                sys.exit(EX_ERROR)
            if op == T_DIV:
                left['val'] //= right['val'] # integer division
            else:
                left['val'] %= right['val']
    return left

# eval3: Addition and subtraction
def eval3():
    """Handles addition and subtraction operators."""
    left = eval4()
    while token in (T_ADD, T_SUB):
        op = token
        get_tok(0)
        right = eval4()
        
        if not to_int(left):
            sys.stderr.write(f"expr: not a number: {left['val']}\n")
            sys.exit(EX_ERROR)
        if not to_int(right):
            sys.stderr.write(f"expr: not a number: {right['val']}\n")
            sys.exit(EX_ERROR)
            
        if op == T_ADD:
            left['val'] += right['val']
        else:
            left['val'] -= right['val']
    return left

# eval2: Comparison operators
def eval2():
    """Handles comparison operators."""
    left = eval3()
    while token in (T_EQ, T_NE, T_LT, T_GT, T_LE, T_GE):
        op = token
        get_tok(0)
        right = eval3()
        
        is_int_l, li = is_int(left)
        is_int_r, ri = is_int(right)
        v = 0
        
        if is_int_l and is_int_r:
            if op == T_GT: v = li > ri
            elif op == T_GE: v = li >= ri
            elif op == T_LT: v = li < ri
            elif op == T_LE: v = li <= ri
            elif op == T_EQ: v = li == ri
            elif op == T_NE: v = li != ri
        else:
            to_str(left)
            to_str(right)
            ls = left['val']
            rs = right['val']
            
            if op == T_GT: v = ls > rs
            elif op == T_GE: v = ls >= rs
            elif op == T_LT: v = ls < rs
            elif op == T_LE: v = ls <= rs
            elif op == T_EQ: v = ls == rs
            elif op == T_NE: v = ls != rs
        
        left = make_int(int(v))
    return left

# eval1: Logical AND
def eval1():
    """Handles the logical AND (&) operator."""
    left = eval2()
    while token == T_AND:
        get_tok(0)
        right = eval2()
        
        if is_zero_or_null(left) or is_zero_or_null(right):
            left = make_int(0)
    return left

# eval0: Logical OR (lowest precedence)
def eval0():
    """Handles the logical OR (|) operator."""
    left = eval1()
    while token == T_OR:
        get_tok(0)
        right = eval1()
        
        if is_zero_or_null(left):
            left = right
    return left

def main():
    """Main function to parse and evaluate the expression."""
    global args_queue, token, tokval
    
    # Handle '--' to separate options from arguments, if any
    if len(sys.argv) > 1 and sys.argv[1] == '--':
        args_queue.extend(sys.argv[2:])
    else:
        args_queue.extend(sys.argv[1:])

    get_tok(0)
    
    try:
        result = eval0()
        if token != T_EOI:
            error()
        
        print(result['val'])
        
        sys.exit(EX_FALSE if is_zero_or_null(result) else EX_TRUE)
        
    except Exception as e:
        sys.stderr.write(f"expr: {e}\n")
        sys.exit(EX_ERROR)

if __name__ == "__main__":
    main()
