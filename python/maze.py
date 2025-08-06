#!/usr/bin/env python3
"""
Name: maze
Description: generate a maze problem
Author: Rocco Caputo, troc@netrus.net (Original Perl Author)
License: perl
"""

import sys
import random
import argparse

# --- Bitmask constants for walls ---
R, B, L, T = 1, 2, 4, 8 # Right, Bottom, Left, Top

# --- Traversal functions for different maze styles ---
def traverse_by_depth(walk_list):
    return -1 # LIFO (stack-like behavior)

def traverse_by_breadth(walk_list):
    return 0 # FIFO (queue-like behavior)

def traverse_randomly(walk_list):
    return random.randint(0, len(walk_list) - 1)

def traverse_randomly_deep(walk_list):
    # Prefers items from the end of the list
    return -random.randint(1, len(walk_list) // 2)

def traverse_randomly_shallow(walk_list):
    # Prefers items from the start of the list
    return random.randint(0, (len(walk_list) - 1) // 2)

def get_validated_number(prompt: str, value: str) -> int:
    """
    Prompts the user for a valid integer (>= 2) if the initial value is invalid.
    """
    while True:
        try:
            num = int(value)
            if num >= 2:
                return num
            print(f"Error: {prompt} is too small (must be 2 or greater).")
        except (ValueError, TypeError):
            print(f"Error: Expected an integer value, got '{value}'.")
        
        try:
            value = input(f"{prompt}? ")
        except (EOFError, KeyboardInterrupt):
            print("\nUnexpected end of input.")
            sys.exit(1)

def main():
    """Parses arguments and generates the maze."""
    alg_map = {
        'fl': traverse_by_breadth,
        'fi': traverse_randomly,
        'df': traverse_randomly_deep,
        'sf': traverse_randomly_shallow,
    }
    parser = argparse.ArgumentParser(
        description="Generate a maze problem.",
        usage="%(prog)s [-fl|-fi|-df|-sf] [width height]"
    )
    # The algorithm flags are mutually exclusive.
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-fl', dest='walk_function', action='store_const', const=traverse_by_breadth)
    group.add_argument('-fi', dest='walk_function', action='store_const', const=traverse_randomly)
    group.add_argument('-df', dest='walk_function', action='store_const', const=traverse_randomly_deep)
    group.add_argument('-sf', dest='walk_function', action='store_const', const=traverse_randomly_shallow)
    
    parser.add_argument('width', nargs='?', help="The width of the maze.")
    parser.add_argument('height', nargs='?', help="The height of the maze.")
    
    args = parser.parse_args()
    
    walk_function = args.walk_function or traverse_by_depth
    
    width = get_validated_number('width', args.width)
    height = get_validated_number('height', args.height)

    # --- 1. Initialize the Maze Grid ---
    maze = [[0] * width for _ in range(height)]
    walk = []

    # Start at a random cell in the top row.
    start_x = random.randint(0, width - 1)
    walk.append((0, start_x))

    # --- 2. Generate the Maze (Randomized Walk) ---
    while walk:
        # Select the next cell to visit based on the chosen algorithm.
        walk_index = walk_function(walk)
        y, x = walk[walk_index]

        # Find all unvisited neighbors.
        neighbors = []
        if y > 0 and maze[y - 1][x] == 0: neighbors.append(('N', T, B, y - 1, x))
        if y < height - 1 and maze[y + 1][x] == 0: neighbors.append(('S', B, T, y + 1, x))
        if x > 0 and maze[y][x - 1] == 0: neighbors.append(('W', L, R, y, x - 1))
        if x < width - 1 and maze[y][x + 1] == 0: neighbors.append(('E', R, L, y, x + 1))

        if not neighbors:
            # This cell is a dead end; remove it from the walk list.
            walk.pop(walk_index)
            continue
        
        # Choose a random neighbor to move to.
        _, wall_to_break, opposite_wall, next_y, next_x = random.choice(neighbors)
        
        # "Knock down" the wall between the current cell and the neighbor.
        maze[y][x] |= wall_to_break
        maze[next_y][next_x] |= opposite_wall
        
        # If the current cell has no more unvisited neighbors, it can be removed.
        if len(neighbors) == 1:
            walk.pop(walk_index)
        
        # Add the new cell to the walk list.
        walk.append((next_y, next_x))

    # --- 3. Display the Maze ---
    # Print the top wall with an opening at the start position.
    print('+' + ''.join('---+' if i != start_x else '   +' for i in range(width)))

    # Print the rows of the maze.
    for y, row in enumerate(maze):
        # Print the vertical walls (cell interiors).
        line = "|"
        for x, cell in enumerate(row):
            line += '   ' if cell & R else '  |'
        print(line)
        
        # Print the horizontal walls.
        line = "+"
        for x, cell in enumerate(row):
            line += '   +' if cell & B else '---+'
        print(line)

if __name__ == "__main__":
    main()
