#!/usr/bin/env python3
"""
Name: wc
Description: paragraph, line, word, character, and byte counter
Author: Peter Prymmer, pvhp@best.com (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import locale

def count_in_stream(stream):
    """
    Reads from a stream and returns a dictionary of counts.
    """
    counts = {
        'lines': 0,
        'words': 0,
        'chars': 0,
        'bytes': 0,
        'paras': 0,
    }
    in_paragraph = False
    
    # Read the file in binary mode to accurately count bytes, then decode.
    for byte_line in stream:
        counts['bytes'] += len(byte_line)
        try:
            # Decode using the system's preferred encoding.
            line = byte_line.decode(locale.getpreferredencoding(False))
        except UnicodeDecodeError:
            # Fallback for data that doesn't match the locale.
            line = byte_line.decode('latin-1')

        counts['lines'] += 1
        counts['chars'] += len(line)
        counts['words'] += len(line.split())
        
        # Paragraphs are blocks of non-empty lines.
        if line.strip():
            if not in_paragraph:
                counts['paras'] += 1
                in_paragraph = True
        else:
            in_paragraph = False
            
    return counts

def format_counts(counts, args, filename=""):
    """
    Formats the counts into a single output string based on the active flags.
    """
    output_parts = []
    if args.p: output_parts.append(f"{counts['paras']:>8}")
    if args.l: output_parts.append(f"{counts['lines']:>8}")
    if args.w: output_parts.append(f"{counts['words']:>8}")
    if args.m: output_parts.append(f"{counts['chars']:>8}")
    if args.c: output_parts.append(f"{counts['bytes']:>8}")
    
    output_parts.append(f" {filename}")
    return "".join(output_parts)

def main():
    """Parses arguments and orchestrates the counting process."""
    # Set the locale to respect the user's environment for word splitting.
    locale.setlocale(locale.LC_ALL, '')

    parser = argparse.ArgumentParser(
        description="A paragraph, line, word, character, and byte counter.",
        usage="%(prog)s [-a | [-p] [-l] [-w] [-m] [-c] ] [file...]"
    )
    parser.add_argument('-a', action='store_true', help='Equivalent to -plwmc.')
    parser.add_argument('-p', action='store_true', help='Count paragraphs.')
    parser.add_argument('-l', action='store_true', help='Count lines.')
    parser.add_argument('-w', action='store_true', help='Count words.')
    parser.add_argument('-m', action='store_true', help='Count characters.')
    parser.add_argument('-c', action='store_true', help='Count bytes.')
    
    parser.add_argument('files', nargs='*', help='Files to process. Reads from stdin if none are given.')
    
    args = parser.parse_args()
    program_name = os.path.basename(sys.argv[0])
    
    # --- Handle Flag Logic ---
    # -a is a shortcut for all flags.
    if args.a:
        args.p = args.l = args.w = args.m = args.c = True
    
    # Default is -lwc if no flags are specified.
    if not any([args.p, args.l, args.w, args.m, args.c]):
        args.l = args.w = args.c = True
        
    # --- Process Files ---
    total_counts = { 'lines': 0, 'words': 0, 'chars': 0, 'bytes': 0, 'paras': 0 }
    exit_status = 0
    
    files_to_process = args.files
    if not files_to_process:
        # If no files, read from stdin.
        file_counts = count_in_stream(sys.stdin.buffer)
        print(format_counts(file_counts, args))
    else:
        for filepath in files_to_process:
            try:
                if os.path.isdir(filepath):
                    print(f"{program_name}: '{filepath}' is a directory", file=sys.stderr)
                    exit_status = 1
                    continue
                with open(filepath, 'rb') as f:
                    file_counts = count_in_stream(f)
                
                print(format_counts(file_counts, args, filepath))
                
                # Add to totals for the final summary line.
                for key in total_counts:
                    total_counts[key] += file_counts[key]

            except FileNotFoundError:
                print(f"{program_name}: failed to open '{filepath}': No such file or directory", file=sys.stderr)
                exit_status = 1
            except IOError as e:
                print(f"{program_name}: I/O error on '{filepath}': {e.strerror}", file=sys.stderr)
                exit_status = 1
    
    # If more than one file was processed, print the total.
    if len(files_to_process) > 1:
        print(format_counts(total_counts, args, "total"))
        
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
