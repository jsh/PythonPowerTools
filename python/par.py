#!/usr/bin/env python3
"""
Name: par
Description: create a Perl archive of files
Author: Tim Gim Yee, tim.gim.yee@gmail.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import stat
import time
import getpass
import socket
import base64
import binascii

# --- Helper Functions ---

def is_binary_file(filepath: str, block_size=1024) -> bool:
    """Heuristically determines if a file is binary by checking for null bytes."""
    try:
        with open(filepath, 'rb') as f:
            return b'\x00' in f.read(block_size)
    except IOError:
        return False

def get_file_stats(filepath: str) -> dict:
    """Gathers metadata (mode, size, mtime, etc.) for a file."""
    try:
        s = os.stat(filepath)
        return {
            'path': filepath,
            'mode': stat.S_IMODE(s.st_mode),
            'size': s.st_size,
            'mtime': s.st_mtime,
            'isdir': stat.S_ISDIR(s.st_mode)
        }
    except OSError:
        return None

def generate_python_archive(file_stats: list, args: argparse.Namespace):
    """Generates a self-extracting Python script."""
    print("#!/usr/bin/env python3")
    print("# This is a Python archive. To extract, run: python <this_file_name>")
    
    # --- Generate the data payload as a Python dictionary ---
    print("\nARCHIVE_DATA = {")
    for stats in file_stats:
        path = stats['path']
        print(f"    '{path}': {{")
        print(f"        'isdir': {stats['isdir']},")
        print(f"        'mode': 0o{stats['mode']:o},")
        print(f"        'mtime': {stats['mtime']},")
        
        if not stats['isdir']:
            is_bin = args.B or (not args.T and is_binary_file(path))
            print(f"        'is_binary': {is_bin},")
            print( "        'content': (")
            with open(path, 'rb') as f:
                if is_bin:
                    # Encode binary files with Base64
                    encoded = base64.b64encode(f.read())
                    # Split into 76-char lines for readability
                    for i in range(0, len(encoded), 76):
                        print(f"            b'{encoded[i:i+76].decode('ascii')}'")
                else:
                    # Embed text files in triple-quoted strings
                    content = f.read().decode('utf-8', errors='replace')
                    print("            '''" + content.replace("'''", r"\'\'\'") + "'''")
            print("        ),")
        print("    },")
    print("}\n")

    # --- Generate the Python extraction logic ---
    print(
"""
import os, base64, sys

def extract():
    overwrite_all = '-c' in sys.argv
    print("Extracting archive...")
    
    # Sort to ensure directories are created before files inside them.
    for path, data in sorted(ARCHIVE_DATA.items()):
        if os.path.exists(path) and not overwrite_all:
            print(f"Skipping existing file: {path}")
            continue

        if data['isdir']:
            print(f"Creating directory: {path}")
            os.makedirs(path, exist_ok=True)
        else:
            print(f"Extracting file: {path}")
            content = data['content']
            if isinstance(content, tuple): # Handle multi-line base64
                content = b"".join(content)
                
            with open(path, 'wb' if data['is_binary'] else 'w') as f:
                if data['is_binary']:
                    f.write(base64.b64decode(content))
                else:
                    f.write(content)
        
        try:
            os.chmod(path, data['mode'])
            os.utime(path, (data['mtime'], data['mtime']))
        except OSError as e:
            print(f"Warning: Could not set metadata for {path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    extract()
"""
    )


def generate_shar_archive(file_stats: list, args: argparse.Namespace):
    """Generates a self-extracting shell script."""
    print("#!/bin/sh")
    print("# This is a shell archive. To extract, run: sh <this_file_name>")
    
    for stats in file_stats:
        path = stats['path']
        mode = stats['mode']
        mtime = time.strftime('%Y%m%d%H%M.%S', time.localtime(stats['mtime']))
        
        print(f"\n# ============= {path} =============")
        if stats['isdir']:
            print(f"echo 'x - creating directory {path}'")
            print(f"mkdir -p '{path}'")
            print(f"chmod {mode:o} '{path}'")
            continue

        is_bin = args.B or (not args.T and is_binary_file(path))
        print(f"echo 'x - extracting {path} ({'binary' if is_bin else 'text'})'")
        
        # Use a here-document to create the file
        if is_bin:
            print(f"uudecode << 'SHAR_EOF'")
            print(f"begin {mode:o} {path}")
            # Generate uuencoded content
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(45)
                    if not chunk: break
                    sys.stdout.buffer.write(binascii.b2a_uu(chunk))
            print("`\nend")
        else:
            print(f"sed 's/^X//' > '{path}' << 'SHAR_EOF'")
            # Prepend 'X' to each line
            with open(path, 'r', errors='ignore') as f:
                for line in f:
                    print('X' + line, end='')

        print("SHAR_EOF")
        # Set metadata
        print(f"chmod {mode:o} '{path}'")
        print(f"touch -m -t {mtime} '{path}'")

def main():
    """Parses arguments and orchestrates the archive creation."""
    parser = argparse.ArgumentParser(
        description="Create a self-extracting archive of files.",
        usage="%(prog)s [-s submitter] [-STBqvz] file..."
    )
    # Add all options from the original script
    parser.add_argument('-B', action='store_true', help='Treat all files as binary.')
    parser.add_argument('-S', action='store_true', help='Read list of files from standard input.')
    parser.add_argument('-T', action='store_true', help='Treat all files as text.')
    parser.add_argument('-s', '--submitter', help='Submitter name to include in the header (cosmetic).')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode (suppresses warnings).')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.08')
    parser.add_argument('-z', '--shar', action='store_true', help='Create a shell archive (shar) instead of a Python archive.')
    
    parser.add_argument('files', nargs='*', help='Files or directories to archive.')
    
    args = parser.parse_args()
    
    # --- Gather File List ---
    files_to_process = args.files
    if args.S:
        files_to_process.extend(line.strip() for line in sys.stdin if line.strip())

    if not files_to_process:
        parser.error("missing file operand.")

    # --- Collect Stats for all files recursively ---
    all_file_stats = []
    for path in files_to_process:
        if os.path.isdir(path):
            # Use os.walk for recursion
            for root, dirs, files in os.walk(path):
                # Add directories first, then files
                for name in sorted(dirs + files):
                    full_path = os.path.join(root, name)
                    stats = get_file_stats(full_path)
                    if stats: all_file_stats.append(stats)
        else:
            stats = get_file_stats(path)
            if stats: all_file_stats.append(stats)

    # --- Generate the correct archive type ---
    if args.shar:
        generate_shar_archive(all_file_stats, args)
    else:
        generate_python_archive(all_file_stats, args)

if __name__ == "__main__":
    main()
