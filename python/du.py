#!/usr/bin/env python3
"""
Name: du
Description: display disk usage statistics
Author: Greg Hewgill, greg@hewgill.com (Original Perl Author)
License: perl
"""

import sys
import os
import math
import argparse

class DiskUsageTraverser:
    """
    A class to encapsulate the state and logic for traversing filesystems
    and calculating disk usage, mimicking the `du` command.
    """
    def __init__(self, args):
        self.args = args
        self.exit_status = 0
        self.grand_total = 0
        self.seen_inodes = set()
        self.start_filesystem = -1
        
        # Determine block size from environment or -k flag
        self.block_size = int(os.environ.get('BLOCKSIZE', 512))
        if args.k:
            self.block_size = 1024
        if self.block_size <= 0:
            print(f"{sys.argv[0]}: unexpected block size: {self.block_size}", file=sys.stderr)
            sys.exit(1)

    def run(self, paths):
        """
        Processes all command-line paths.
        """
        for path in paths:
            self.seen_inodes.clear() # Reset for each top-level argument
            total = self._traverse(path, 0)
            self.grand_total += total
        
        if self.args.c:
            print(f"{self.grand_total}\ttotal")
            
        return self.exit_status

    def _traverse(self, path, depth):
        """
        Recursively traverses a path, calculating and printing disk usage.
        """
        total = 0
        
        # --- 1. Get File Stats (handles -H, -L, -P for symlinks) ---
        try:
            # -L: follow all links. -H: follow command-line links (depth 0).
            if self.args.L or (self.args.H and depth == 0):
                stats = os.stat(path)
            else: # -P (default): do not follow links
                stats = os.lstat(path)
        except OSError as e:
            print(f"{sys.argv[0]}: cannot access '{path}': {e.strerror}", file=sys.stderr)
            self.exit_status = 1
            return 0

        # --- 2. Check Filesystem Boundary (-x) ---
        if depth == 0:
            self.start_filesystem = stats.st_dev
        elif self.args.x and stats.st_dev != self.start_filesystem:
            return 0
        
        # --- 3. Handle Hard Links (-l) ---
        # By default, only count a file once if it has multiple hard links.
        dev_inode_pair = (stats.st_dev, stats.st_ino)
        if not self.args.l and stats.st_nlink > 1 and dev_inode_pair in self.seen_inodes:
            return 0
        self.seen_inodes.add(dev_inode_pair)
        
        # --- 4. Calculate Size ---
        # Always count the size of the directory entries themselves.
        # The calculation rounds up to the nearest whole block.
        size_in_blocks = math.ceil(stats.st_size / self.block_size)
        total += size_in_blocks

        # --- 5. Recurse into Directories ---
        # We only recurse if the path is a directory and not a symlink (unless -L/-H)
        is_dir_to_traverse = os.path.isdir(path) and not os.path.islink(path)
        if os.path.islink(path) and (self.args.L or (self.args.H and depth == 0)):
             if os.path.isdir(path): # Check if the link's target is a directory
                 is_dir_to_traverse = True
        
        if is_dir_to_traverse:
            try:
                for entry in os.scandir(path):
                    total += self._traverse(entry.path, depth + 1)
            except OSError as e:
                 print(f"{sys.argv[0]}: could not read directory '{path}': {e.strerror}", file=sys.stderr)
                 self.exit_status = 1
        
        # --- 6. Print Output based on -a and -s flags ---
        if self.args.a or (not self.args.s and is_dir_to_traverse):
            print(f"{total}\t{path}")
        elif self.args.s and depth == 0:
            print(f"{total}\t{path}")

        return total

def main():
    """Parses arguments and starts the disk usage traversal."""
    parser = argparse.ArgumentParser(
        description="Display disk usage statistics.",
        usage="%(prog)s [-H | -L | -P] [-a | -s] [-cklrx] [file ...]"
    )
    # Symlink handling group
    link_group = parser.add_mutually_exclusive_group()
    link_group.add_argument('-H', action='store_true', help='Follow symbolic links on the command line.')
    link_group.add_argument('-L', action='store_true', help='Follow all symbolic links.')
    link_group.add_argument('-P', action='store_true', help='Do not follow any symbolic links (default).')
    
    # Display mode group
    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument('-a', action='store_true', help='Display an entry for each file.')
    display_group.add_argument('-s', action='store_true', help='Display only a total for each argument.')
    
    # Other flags
    parser.add_argument('-c', action='store_true', help='Display a grand total.')
    parser.add_argument('-k', action='store_true', help='Use 1024-byte blocks instead of 512-byte.')
    parser.add_argument('-l', action='store_true', help='Count hard-linked files multiple times.')
    parser.add_argument('-r', action='store_true', help='Report errors (default behavior, for compatibility).')
    parser.add_argument('-x', action='store_true', help='Do not cross filesystem boundaries.')
    
    parser.add_argument('files', nargs='*', default=['.'], help='Files or directories to process.')
    
    args = parser.parse_args()

    traverser = DiskUsageTraverser(args)
    exit_status = traverser.run(args.files)
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
