#!/usr/bin/env python3
"""
Name: unpar.py
Description: extract files from a Perl archive (.par file)
Author: Tim Gim Yee, tim.gim.yee@gmail.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import zipfile
import io

__version__ = "0.02"

def extract_par_archive(filepath: str, output_dir: str, force_overwrite: bool, quiet: bool):
    """
    Finds the embedded ZIP archive in a .par file and extracts its contents.

    Args:
        filepath (str): The path to the .par file.
        output_dir (str): The directory to extract files into.
        force_overwrite (bool): If True, overwrite existing files.
        quiet (bool): If True, suppress informational messages.
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()

        # A PAR file has a ZIP archive appended. Find the start of it
        # by looking for the ZIP magic number 'PK\x03\x04'.
        zip_start_offset = data.rfind(b'PK\x03\x04')

        if zip_start_offset == -1:
            if not quiet:
                print(f"Warning: Not a valid PAR or ZIP file: {filepath}", file=sys.stderr)
            return False

        # Create a file-like object in memory from the zip data.
        zip_data = io.BytesIO(data[zip_start_offset:])
        
        with zipfile.ZipFile(zip_data) as zf:
            for member in zf.infolist():
                dest_path = os.path.join(output_dir, member.filename)
                
                # Check if the file exists and if we should skip it.
                if os.path.exists(dest_path) and not force_overwrite:
                    if not quiet:
                        print(f"Skipping existing file: {member.filename}", file=sys.stderr)
                    continue

                if not quiet:
                    print(f"Extracting: {member.filename}")
                
                # ZipFile.extract() handles creating subdirectories automatically.
                zf.extract(member, path=output_dir)
        return True

    except FileNotFoundError:
        print(f"Error: Couldn't open '{filepath}': No such file or directory", file=sys.stderr)
    except zipfile.BadZipFile:
        if not quiet:
            print(f"Warning: Found ZIP header but failed to parse archive in: {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred with '{filepath}': {e}", file=sys.stderr)

    return False


def main():
    """Parses command-line arguments and orchestrates the extraction."""
    parser = argparse.ArgumentParser(
        description="Extract files from Perl archives (.par files).",
        usage="%(prog)s [-d dir] [-cfqv] file [files...]"
    )
    parser.add_argument(
        '-c', '-f', '--force',
        action='store_true',
        help='Overwrite existing files.'
    )
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='Change directory to DIR before extracting files.'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode; suppress informational messages.'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        'files',
        nargs='*', # Zero or more files
        help='One or more .par files to process. Reads from stdin if none are given.'
    )

    args = parser.parse_args()
    
    # --- Handle pre-extraction setup ---
    try:
        if args.directory != '.':
            os.makedirs(args.directory, exist_ok=True)
            os.chdir(args.directory)
            if not args.quiet:
                print(f"Changed directory to '{os.getcwd()}'", file=sys.stderr)
    except OSError as e:
        print(f"Error: Couldn't chdir to '{args.directory}': {e}", file=sys.stderr)
        sys.exit(1)

    # --- Process Files ---
    files_to_process = args.files
    if not files_to_process:
        print("Error: This script requires a file argument and cannot read from stdin.", file=sys.stderr)
        sys.exit(1)

    for par_file in files_to_process:
        extract_par_archive(par_file, '.', args.force, args.quiet)

if __name__ == "__main__":
    main()
