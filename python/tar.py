#!/usr/bin/env python3
"""
Name: tar
Description: manipulate tape archives
License: perl
"""

import sys
import os
import argparse
import tarfile
import stat
from datetime import datetime

def list_archive(tar: tarfile.TarFile, verbose: bool):
    """
    Lists the contents of the tar archive.
    """
    for member in tar.getmembers():
        if verbose:
            # Recreate the 'ls -l'-style output
            mode = stat.filemode(member.mode)
            owner_group = f"{member.uname or member.uid}/{member.gname or member.gid}"
            size = member.size
            mtime = datetime.fromtimestamp(member.mtime).strftime('%b %d %H:%M %Y')
            
            print(f"{mode} {owner_group:<17} {size:>8d} {mtime} {member.name}")
        else:
            print(member.name)

def extract_archive(tar: tarfile.TarFile, verbose: bool):
    """
    Extracts the contents of the tar archive to the current directory.
    """
    # tarfile is secure by default and will not extract files outside the
    # destination directory.
    if verbose:
        for member in tar.getmembers():
            print(member.name)
    
    tar.extractall()
    
def main():
    """Parses arguments and performs the requested tar operation."""
    parser = argparse.ArgumentParser(
        description="Manipulate tape archives. A simplified tar implementation.",
        usage="%(prog)s {-t | -x} [-v] [-z] -f archive [file ...]",
        # Allow bundling of single-character flags (e.g., -tvf)
        prefix_chars='-'
    )
    # The main operation modes are mutually exclusive.
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('-t', dest='list', action='store_true', help='List the contents of an archive.')
    mode_group.add_argument('-x', dest='extract', action='store_true', help='Extract files from an archive.')
    mode_group.add_argument('-c', dest='create', action='store_true', help='Create a new archive (not implemented).')
    
    # Modifier flags
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbosely list files processed.')
    parser.add_argument('-f', '--file', dest='archive_file', required=True, help="Use archive file or device ARCHIVE. Use '-' for stdin.")
    parser.add_argument('-z', '--gzip', action='store_true', help='Filter the archive through gzip.')
    
    # Unused arguments from the original script, for compatibility.
    parser.add_argument('-Z', dest='compress', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-m', action='store_true', help=argparse.SUPPRESS)

    # Allow unknown args to be passed through (e.g., file list for extraction)
    args, _ = parser.parse_known_args()
    program_name = os.path.basename(sys.argv[0])

    if args.create:
        print(f"{program_name}: -c (create) is not implemented in this version.", file=sys.stderr)
        sys.exit(1)

    # --- 1. Determine Read Mode and Input Stream ---
    read_mode = "r:gz" if args.gzip or args.compress else "r:"
    
    try:
        if args.archive_file == '-':
            # Read from stdin's binary buffer
            tar = tarfile.open(fileobj=sys.stdin.buffer, mode=read_mode)
        else:
            tar = tarfile.open(args.archive_file, mode=read_mode)
            
        with tar:
            # --- 2. Perform Action ---
            if args.list:
                list_archive(tar, args.verbose)
            elif args.extract:
                extract_archive(tar, args.verbose)

    except tarfile.TarError as e:
        print(f"{program_name}: An error occurred reading the archive: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"{program_name}: Cannot open '{args.archive_file}': No such file or directory", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
        
    sys.exit(0)

if __name__ == "__main__":
    main()
