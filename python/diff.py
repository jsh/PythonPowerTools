#!/usr/bin/env python3

"""
Name: diff
Description: compute 'intelligent' differences between two files
Author: Mark-Jason Dominus, mjd-perl-diff@plover.com
Author: Christian Murphy, cpm@muc.de
Author: Amir D. Karger, karger@bead.aecom.yu.edu
License: perl
"""

import sys
import os
import re
import argparse
from datetime import datetime
from functools import reduce
from collections import deque

# Constants
EX_SUCCESS = 0
EX_DIFFERENT = 1
EX_FAILURE = 2

# Globals
file_length_difference = 0
program_name = os.path.basename(sys.argv[0])
ed_hunks = deque()

class Block:
    """Represents a single block of changes (additions, deletions, or modifications)."""
    
    def __init__(self, chunk):
        self.changes = [{'sign': c[0], 'item_no': c[1]} for c in chunk]
        self.length_diff = self.insert_count() - self.remove_count()

    def op(self):
        """Returns the type of operation: '!', '+', or '-'."""
        removals = self.remove_count()
        insertions = self.insert_count()
        if removals and insertions:
            return '!'
        if removals:
            return '-'
        if insertions:
            return '+'
        return '^'

    def remove_count(self):
        return sum(1 for c in self.changes if c['sign'] == '-')

    def insert_count(self):
        return sum(1 for c in self.changes if c['sign'] == '+')

    def removes(self):
        return [c for c in self.changes if c['sign'] == '-']

    def inserts(self):
        return [c for c in self.changes if c['sign'] == '+']

class Hunk:
    """Represents a group of overlapping blocks, possibly with context lines."""
    
    def __init__(self, chunk, context_lines):
        global file_length_difference
        
        block = Block(chunk)
        
        before_diff = file_length_difference
        file_length_difference += block.length_diff
        after_diff = file_length_difference

        removes = block.removes()
        inserts = block.inserts()
        
        start1 = removes[0]['item_no'] if removes else inserts[0]['item_no'] - before_diff
        end1 = removes[-1]['item_no'] if removes else inserts[-1]['item_no'] - after_diff
        start2 = inserts[0]['item_no'] if inserts else removes[0]['item_no'] + before_diff
        end2 = inserts[-1]['item_no'] if inserts else removes[-1]['item_no'] + after_diff

        self.start1, self.end1 = start1, end1
        self.start2, self.end2 = start2, end2
        self.blocks = [block]

        self.flag_context(context_lines)
    
    def flag_context(self, context_lines):
        if not context_lines:
            return

        self.start1 = max(0, self.start1 - context_lines)
        self.start2 = max(0, self.start2 - context_lines)

        self.end1 = min(len(f1) - 1, self.end1 + context_lines)
        self.end2 = min(len(f2) - 1, self.end2 + context_lines)

    def does_overlap(self, other_hunk):
        if other_hunk is None:
            return False
        return (self.start1 - other_hunk.end1 <= 1) or (self.start2 - other_hunk.end2 <= 1)

    def prepend_hunk(self, other_hunk):
        self.start1 = other_hunk.start1
        self.start2 = other_hunk.start2
        self.blocks = other_hunk.blocks + self.blocks

    def output_old_diff(self, f1_ref, f2_ref):
        block = self.blocks[0]
        op_hash = {'+': 'a', '-': 'd', '!': 'c'}
        action = op_hash.get(block.op(), 'u')

        range1 = self.context_range(1)
        range2 = self.context_range(2)
        print(f"{range1}{action}{range2}")

        if block.removes():
            for i in range(self.start1, self.end1 + 1):
                print(f"< {f1_ref[i]}")

        if block.op() == '!':
            print("---")
            
        if block.inserts():
            for i in range(self.start2, self.end2 + 1):
                print(f"> {f2_ref[i]}")

    def output_unified_diff(self, f1_ref, f2_ref):
        range1 = self.unified_range(1)
        range2 = self.unified_range(2)
        print(f"@@ -{range1} +{range2} @@")

        low1, high1 = self.start1, self.end1
        low2, high2 = self.start2, self.end2

        outlist = []
        i1, i2 = low1, low2
        
        while i1 <= high1 or i2 <= high2:
            is_remove = i1 <= high1 and any(i1 == c['item_no'] for block in self.blocks for c in block.removes())
            is_insert = i2 <= high2 and any(i2 == c['item_no'] for block in self.blocks for c in block.inserts())
            
            if is_remove and is_insert:
                outlist.append(f"-{f1_ref[i1]}")
                outlist.append(f"+{f2_ref[i2]}")
                i1 += 1
                i2 += 1
            elif is_remove:
                outlist.append(f"-{f1_ref[i1]}")
                i1 += 1
            elif is_insert:
                outlist.append(f"+{f2_ref[i2]}")
                i2 += 1
            else:
                outlist.append(f" {f1_ref[i1]}")
                i1 += 1
                i2 += 1

        print("\n".join(outlist))


    def output_context_diff(self, f1_ref, f2_ref):
        print("***************")
        range1 = self.context_range(1)
        range2 = self.context_range(2)
        print(f"*** {range1} ****")

        # Print file 1 part
        if any(b.removes() for b in self.blocks):
            outlist1 = list(f1_ref[self.start1:self.end1 + 1])
            for i in range(len(outlist1)):
                outlist1[i] = f"  {outlist1[i]}"
            
            for block in self.blocks:
                op = block.op()
                for item in block.removes():
                    outlist1[item['item_no'] - self.start1] = f"{op} {outlist1[item['item_no'] - self.start1].strip()}"
            print("\n".join(outlist1))

        print(f"--- {range2} ----")

        # Print file 2 part
        if any(b.inserts() for b in self.blocks):
            outlist2 = list(f2_ref[self.start2:self.end2 + 1])
            for i in range(len(outlist2)):
                outlist2[i] = f"  {outlist2[i]}"
                
            for block in self.blocks:
                op = block.op()
                for item in block.inserts():
                    outlist2[item['item_no'] - self.start2] = f"{op} {outlist2[item['item_no'] - self.start2].strip()}"
            print("\n".join(outlist2))

    def store_ed_diff(self, *args):
        global ed_hunks
        ed_hunks.appendleft(self)

    def output_ed_diff(self, f1_ref, f2_ref, diff_type):
        block = self.blocks[0]
        op_hash = {'+': 'a', '-': 'd', '!': 'c'}
        action = op_hash.get(block.op(), 'u')
        
        range1 = self.context_range(1)
        
        if diff_type == 'REVERSE_ED':
            range1 = range1.replace(',', ' ')
            print(f"{action}{range1}")
        else:
            print(f"{range1}{action}")
        
        if block.inserts():
            for i in range(self.start2, self.end2 + 1):
                print(f2_ref[i])
            print(".")

    def context_range(self, flag):
        start = getattr(self, f'start{flag}') + 1
        end = getattr(self, f'end{flag}') + 1
        return f"{start},{end}" if start < end else str(end)

    def unified_range(self, flag):
        start = getattr(self, f'start{flag}') + 1
        end = getattr(self, f'end{flag}') + 1
        length = end - start + 1
        return f"{start},{length}" if length > 1 else str(first)

def lcs_matrix(a, b):
    """Computes the Longest Common Subsequence matrix."""
    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                matrix[i][j] = 1 + matrix[i - 1][j - 1]
            else:
                matrix[i][j] = max(matrix[i][j - 1], matrix[i - 1][j])
    return matrix

def diff(a, b):
    """
    Computes the difference between two sequences using LCS.
    Returns a list of change blocks.
    """
    matrix = lcs_matrix(a, b)
    changes = []
    i, j = len(a), len(b)
    
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            i -= 1
            j -= 1
        else:
            if j > 0 and (i == 0 or matrix[i][j - 1] >= matrix[i - 1][j]):
                changes.append(('+', j - 1))
                j -= 1
            elif i > 0 and (j == 0 or matrix[i][j - 1] < matrix[i - 1][j]):
                changes.append(('-', i - 1))
                i -= 1
    
    changes.reverse()
    
    # Group changes into blocks
    blocks = []
    current_block = []
    if changes:
        current_block.append(changes[0])
    
    for k in range(1, len(changes)):
        prev_sign, prev_idx = changes[k - 1]
        curr_sign, curr_idx = changes[k]
        
        # Check for continuity
        if prev_sign == curr_sign and abs(prev_idx - curr_idx) == 1:
            current_block.append(changes[k])
        else:
            blocks.append(current_block)
            current_block = [changes[k]]
    if current_block:
        blocks.append(current_block)
    
    return blocks

def identical():
    """Prints a message for identical files and exits."""
    if options.get('s'):
        print(f"Files {file1} and {file2} are identical")
    sys.exit(EX_SUCCESS)

def bag(msg):
    """Prints an error message and exits."""
    sys.stderr.write(f"{program_name}: {msg}\n")
    sys.exit(EX_FAILURE)

def checklen(n):
    """Validates and returns a non-negative integer context length."""
    try:
        n = int(n)
        if n < 0:
            raise ValueError
        return n
    except (ValueError, TypeError):
        sys.stderr.write(f"{program_name}: invalid context length '{n}'\n")
        usage()

def set_diff_type(val):
    """Sets the diff type, checking for incompatible options."""
    global diff_type
    if diff_type != 'OLD' and diff_type != val:
        sys.stderr.write(f"{program_name}: incompatible diff type options\n")
        usage()
    diff_type = val

# Main program execution
if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('files', nargs='*')
    parser.add_argument('-c', action='store_true', help='context diff with 3 lines')
    parser.add_argument('-C', type=int, help='context diff with NUM lines')
    parser.add_argument('-e', action='store_true', help='ed script diff')
    parser.add_argument('-f', action='store_true', help='reverse ed script diff')
    parser.add_argument('-q', action='store_true', help='quiet mode')
    parser.add_argument('-s', action='store_true', help='show message for identical files')
    parser.add_argument('-u', action='store_true', help='unified diff with 3 lines')
    parser.add_argument('-U', type=int, help='unified diff with NUM lines')

    options = parser.parse_args()

    context_lines = 0
    diff_type = "OLD"

    if options.C is not None:
        context_lines = checklen(options.C)
        set_diff_type('CONTEXT')
    elif options.c:
        context_lines = 3
        set_diff_type('CONTEXT')
    elif options.e:
        set_diff_type('ED')
    elif options.f:
        set_diff_type('REVERSE_ED')
    elif options.U is not None:
        context_lines = checklen(options.U)
        set_diff_type('UNIFIED')
    elif options.u:
        context_lines = 3
        set_diff_type('UNIFIED')

    if len(options.files) != 2:
        if len(options.files) < 2:
            bag("missing operand")
        else:
            bag(f"extra operand: '{options.files[2]}'")

    file1, file2 = options.files
    
    # Read files into memory
    f1, f2 = [], []
    try:
        if file1 == '-':
            f1 = [line.strip() for line in sys.stdin.readlines()]
        else:
            with open(file1, 'r') as fh:
                f1 = [line.strip() for line in fh.readlines()]
    except IOError as e:
        bag(f"Couldn't open '{file1}': {e}")
    
    try:
        if file2 == '-':
            # If both are STDIN, it's not a valid comparison
            if file1 == '-':
                bag("cannot compare '-' to '-'")
            f2 = [line.strip() for line in sys.stdin.readlines()]
        else:
            with open(file2, 'r') as fh:
                f2 = [line.strip() for line in fh.readlines()]
    except IOError as e:
        bag(f"Couldn't open '{file2}': {e}")

    # The actual diff logic
    diffs = diff(f1, f2)
    
    if not diffs:
        identical()

    if options.q:
        print(f"Files {file1} and {file2} differ")
        sys.exit(EX_DIFFERENT)

    if diff_type in ['CONTEXT', 'UNIFIED']:
        char1 = '***' if diff_type == 'CONTEXT' else '---'
        char2 = '---' if diff_type == 'CONTEXT' else '+++'
        mtime1 = datetime.fromtimestamp(os.stat(file1).st_mtime) if os.path.exists(file1) else 'N/A'
        mtime2 = datetime.fromtimestamp(os.stat(file2).st_mtime) if os.path.exists(file2) else 'N/A'
        print(f"{char1} {file1}\t{mtime1}")
        print(f"{char2} {file2}\t{mtime2}")

    old_hunk = None
    for piece in diffs:
        hunk = Hunk(piece, context_lines)
        if old_hunk and context_lines > 0 and hunk.does_overlap(old_hunk):
            hunk.prepend_hunk(old_hunk)
        else:
            if old_hunk:
                if diff_type == 'OLD': old_hunk.output_old_diff(f1, f2)
                elif diff_type == 'CONTEXT': old_hunk.output_context_diff(f1, f2)
                elif diff_type == 'UNIFIED': old_hunk.output_unified_diff(f1, f2)
                elif diff_type == 'ED': old_hunk.store_ed_diff(f1, f2)
                elif diff_type == 'REVERSE_ED': old_hunk.output_ed_diff(f1, f2, 'REVERSE_ED')

        old_hunk = hunk
    
    if old_hunk:
        if diff_type == 'OLD': old_hunk.output_old_diff(f1, f2)
        elif diff_type == 'CONTEXT': old_hunk.output_context_diff(f1, f2)
        elif diff_type == 'UNIFIED': old_hunk.output_unified_diff(f1, f2)
        elif diff_type == 'ED': old_hunk.store_ed_diff(f1, f2)
        elif diff_type == 'REVERSE_ED': old_hunk.output_ed_diff(f1, f2, 'REVERSE_ED')
    
    if diff_type == 'ED':
        for hunk in ed_hunks:
            hunk.output_ed_diff(f1, f2, 'ED')

    sys.exit(EX_DIFFERENT)
