#!/usr/bin/env python3
"""
Name: glob
Description: find pathnames matching a pattern
Author: Marc Mengel, brian d foy (Original Perl Authors)
License: perl
"""

import sys
import os
import argparse
import glob
import re

# --- Exit Codes ---
EX_SUCCESS = 0
EX_NO_MATCHES = 1
EX_ERROR = 2

def brace_expand(pattern: str) -> list:
    """
    Performs csh-style brace expansion on a pattern.
    e.g., 'a{b,c}d' -> ['abd', 'acd']
    e.g., 'a{b,c{d,e}}f' -> ['abf', 'acdf', 'acef']
    """
    # Regex to find the innermost brace that doesn't contain other braces.
    innermost_brace_re = re.compile(r'\{[^{}]*?\}')
    
    # A set to hold the patterns being worked on.
    patterns = {pattern}
    
    while True:
        # Find a pattern that still has braces to expand.
        p_with_braces = next((p for p in patterns if '{' in p), None)
        if p_with_braces is None:
            break # No more braces to expand, we're done.

        patterns.remove(p_with_braces)
        
        match = innermost_brace_re.search(p_with_braces)
        if not match:
            # This can happen with mismatched braces, e.g., 'a{b,c'
            # We'll treat it as a literal string.
            patterns.add(p_with_braces)
            continue
            
        # Expand this one brace
        start, end = match.span()
        prefix = p_with_braces[:start]
        suffix = p_with_braces[end:]
        alternatives = match.group(0).strip('{}').split(',')
        
        # Add the new expanded patterns to the set for the next iteration.
        for alt in alternatives:
            patterns.add(prefix + alt + suffix)
            
    return list(patterns)


def main():
    """Parses arguments and performs csh-style globbing."""
    parser = argparse.ArgumentParser(
        description="Find pathnames matching a csh-style pattern.",
        usage="%(prog)s [-0] pattern..."
    )
    parser.add_argument(
        '-0', dest='null_separator', action='store_true',
        help='Separate output with NUL characters instead of newlines.'
    )
    parser.add_argument(
        'patterns',
        nargs='+',
        help='One or more glob patterns to expand.'
    )
    
    args = parser.parse_args()
    
    all_matches = set()

    for pattern in args.patterns:
        # 1. Check for mismatched braces before trying to expand.
        if pattern.count('{') != pattern.count('}'):
            print(f"{sys.argv[0]}: Missing '}}'.", file=sys.stderr)
            sys.exit(EX_ERROR)
            
        # 2. Perform brace expansion.
        expanded_brace_patterns = brace_expand(pattern)
        
        # 3. For each resulting pattern, perform tilde and wildcard expansion.
        for p in expanded_brace_patterns:
            # os.path.expanduser handles '~' and '~user'
            tilde_expanded = os.path.expanduser(p)
            # glob.glob handles '*', '?', and '[...]'
            matches = glob.glob(tilde_expanded)
            all_matches.update(matches)
            
    # --- Print results and set exit code ---
    if all_matches:
        separator = '\0' if args.null_separator else '\n'
        # Sort the final list of matches alphabetically.
        sorted_matches = sorted(list(all_matches))
        print(separator.join(sorted_matches), end=separator)
        sys.exit(EX_SUCCESS)
    else:
        print(f"glob: No match.", file=sys.stderr)
        sys.exit(EX_NO_MATCHES)

if __name__ == "__main__":
    main()
