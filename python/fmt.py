#!/usr/bin/env python3
"""
Name: fmt
Description: reformat paragraphs
Author: Dmitri Tikhonov dmitri@cpan.org (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import re
import textwrap
import fileinput

def preprocess_argv(args_list: list) -> list:
    """
    Translates the historical '-WIDTH' syntax to the standard '--width WIDTH'.
    For example, '-80' becomes ['--width', '80'].
    """
    processed_args = []
    for arg in args_list:
        match = re.match(r'^-(\d+)$', arg)
        if match:
            processed_args.extend(['--width', match.group(1)])
        else:
            processed_args.append(arg)
    return processed_args

def get_paragraphs(stream):
    """
    A generator that reads from a stream and yields paragraphs.
    A paragraph is a block of text separated by blank lines or a change in indentation.
    Yields tuples of (indent_string, paragraph_text).
    """
    paragraph_lines = []
    current_indent = None

    for line in stream:
        stripped_line = line.lstrip()
        
        # A blank line always ends the current paragraph.
        if not stripped_line:
            if paragraph_lines:
                yield "".join(paragraph_lines)
                paragraph_lines = []
            current_indent = None
            # Yield a special marker for the blank line itself to preserve spacing.
            yield "\n"
            continue
            
        indent_len = len(line) - len(stripped_line)
        indent = line[:indent_len]

        # A change in indentation also ends the current paragraph.
        if current_indent is not None and indent != current_indent:
            if paragraph_lines:
                yield "".join(paragraph_lines)
                paragraph_lines = []
            current_indent = None
        
        if not paragraph_lines:
            current_indent = indent
            
        paragraph_lines.append(stripped_line)

    # Yield any remaining paragraph at the end of the file.
    if paragraph_lines:
        yield "".join(paragraph_lines)

def main():
    """Parses arguments and reformats text from files or stdin."""
    # Pre-process arguments to handle the '-WIDTH' syntax.
    args_to_parse = preprocess_argv(sys.argv[1:])

    parser = argparse.ArgumentParser(
        description="A simple text formatter.",
        usage="%(prog)s [-w width] [file...]"
    )
    parser.add_argument(
        '-w', '--width',
        type=int,
        default=75,
        help='Maximum line width (default: 75).'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to process. Reads from stdin if none are given.'
    )

    try:
        args = parser.parse_args(args_to_parse)
    except SystemExit:
        sys.exit(1)

    if args.width <= 0:
        print(f"{os.path.basename(sys.argv[0])}: width must be positive", file=sys.stderr)
        sys.exit(1)

    # --- Process Input ---
    try:
        # Create a paragraph generator from fileinput.
        paragraphs = get_paragraphs(fileinput.input(files=args.files or ('-',)))
        
        for paragraph in paragraphs:
            if paragraph == "\n":
                print()
                continue

            # Determine the indentation of the paragraph.
            indent_match = re.match(r'(\s*)', paragraph)
            indent = indent_match.group(1) if indent_match else ""
            
            # Use the textwrap module to handle the formatting.
            wrapper = textwrap.TextWrapper(
                width=args.width,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False
            )
            
            # Join the wrapped lines and print.
            print("\n".join(wrapper.wrap(paragraph)))

    except FileNotFoundError as e:
        print(f"{sys.argv[0]}: failed to open '{e.filename}': {e.strerror}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
