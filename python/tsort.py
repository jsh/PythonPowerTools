#!/usr/bin/env python3
"""
Name: tsort
Description: topological sort
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
from collections import defaultdict, deque

def main():
    """Parses arguments and performs a topological sort on the input."""
    parser = argparse.ArgumentParser(
        description="Perform a topological sort on pairs of nodes.",
        usage="%(prog)s [-b|-d] [filename]"
    )
    # Use a mutually exclusive group to ensure -b and -d cannot be used together.
    traversal_group = parser.add_mutually_exclusive_group()
    traversal_group.add_argument(
        '-b', '--breadth-first',
        action='store_true',
        help='Use breadth-first (FIFO) traversal.'
    )
    traversal_group.add_argument(
        '-d', '--depth-first',
        action='store_true',
        help='Use depth-first (LIFO) traversal (default).'
    )
    parser.add_argument(
        'filename',
        nargs='?', # The filename is optional.
        help='Input file containing whitespace-separated pairs. Reads from stdin if not provided.'
    )

    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])

    # --- 1. Read and Parse Input ---
    input_stream = None
    try:
        if args.filename:
            if os.path.isdir(args.filename):
                print(f"{program_name}: '{args.filename}' is a directory", file=sys.stderr)
                sys.exit(1)
            input_stream = open(args.filename, 'r')
        else:
            input_stream = sys.stdin

        # Read all tokens from the input into a single list.
        tokens = input_stream.read().split()

    except IOError as e:
        print(f"{program_name}: '{args.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    finally:
        if input_stream and input_stream is not sys.stdin:
            input_stream.close()

    if len(tokens) % 2 != 0:
        print(f"{program_name}: odd number of tokens", file=sys.stderr)
        sys.exit(1)

    # --- 2. Build the Graph ---
    # defaultdict simplifies graph building; no need to check if a key exists.
    successors = defaultdict(list)
    in_degree = defaultdict(int)
    all_nodes = set()
    
    # Process the tokens in pairs to build the graph edges.
    for i in range(0, len(tokens), 2):
        u, v = tokens[i], tokens[i+1]
        all_nodes.add(u)
        all_nodes.add(v)
        
        # Add the edge only if it's not a self-loop and not a duplicate.
        if u != v and v not in successors[u]:
            successors[u].append(v)
            in_degree[v] += 1
    
    # --- 3. Find Initial Nodes with No Predecessors ---
    # A deque is an efficient list-like object for adding/removing from both ends.
    zero_in_degree_nodes = deque([node for node in all_nodes if in_degree[node] == 0])

    # --- 4. Perform the Topological Sort (Kahn's Algorithm) ---
    sorted_result = []
    while zero_in_degree_nodes:
        # LIFO (pop from right) for depth-first, FIFO (pop from left) for breadth-first.
        # The original script's logic was reversed; this version is canonical.
        node = zero_in_degree_nodes.pop() if not args.breadth_first else zero_in_degree_nodes.popleft()
        sorted_result.append(node)
        
        for child in successors[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                zero_in_degree_nodes.append(child)

    # --- 5. Check for Cycles and Print Result ---
    if len(sorted_result) == len(all_nodes):
        for node in sorted_result:
            print(node)
        sys.exit(0)
    else:
        print(f"{program_name}: cycle detected", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
