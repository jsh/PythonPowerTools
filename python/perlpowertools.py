#!/usr/bin/env python3
"""
Name: pythonpowertools
Description: a program launcher for Python Power Tools
Author: kal247, https://github.com/kal247 (Original Perl Author)
License: artistic2
"""

import sys
import os
import argparse
import subprocess

__version__ = "1.025"

# Using a set for fast 'in' lookups.
# The original 'perldoc' is replaced with 'pydoc' for the Python ecosystem.
TOOLS = {
    'addbib', 'apply', 'ar', 'arch', 'arithmetic', 'asa', 'awk', 'banner', 
    'base64', 'basename', 'bc', 'bcd', 'cal', 'cat', 'chgrp', 'ching', 'chmod', 
    'chown', 'clear', 'cmp', 'col', 'colrm', 'comm', 'cp', 'cut', 'date', 'dc', 
    'deroff', 'diff', 'dirname', 'du', 'echo', 'ed', 'env', 'expand', 'expr', 
    'factor', 'false', 'file', 'find', 'fish', 'fmt', 'fold', 'fortune', 'from', 
    'glob', 'grep', 'hangman', 'head', 'hexdump', 'id', 'install', 'join', 
    'kill', 'ln', 'lock', 'look', 'ls', 'mail', 'maze', 'mimedecode', 'mkdir', 
    'mkfifo', 'moo', 'morse', 'nl', 'od', 'par', 'paste', 'patch', 'pydoc', 
    'pig', 'ping', 'pom', 'ppt', 'pr', 'primes', 'printenv', 'printf', 'pwd', 
    'rain', 'random', 'rev', 'rm', 'rmdir', 'robots', 'rot13', 'seq', 'shar', 
    'sleep', 'sort', 'spell', 'split', 'strings', 'sum', 'tac', 'tail', 'tar', 
    'tee', 'test', 'time', 'touch', 'tr', 'true', 'tsort', 'tty', 'uname', 
    'unexpand', 'uniq', 'units', 'unlink', 'unpar', 'unshar', 'uudecode', 
    'uuencode', 'wc', 'what', 'which', 'whoami', 'whois', 'words', 'wump', 
    'xargs', 'yes'
}

def main():
    """Parses arguments and launches the specified tool."""
    parser = argparse.ArgumentParser(
        description="A program launcher for Python Power Tools.",
        usage="%(prog)s [-l | --list] [-V | --version] [-h | --help] tool [arg ...]"
    )
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='list available tools'
    )
    # This collects the tool name and all subsequent arguments.
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help='The tool to run followed by its arguments.'
    )

    args = parser.parse_args()

    # If --list is used, print tools and exit.
    if args.list:
        # Print sorted list for consistent output.
        print("\n".join(sorted(list(TOOLS))))
        sys.exit(0)

    # If no tool is specified, show the help message.
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # The first item in the remainder is the tool name.
    tool = args.command[0]
    tool_args = args.command # The full command for execv includes the tool name as arg[0]

    # Validate that the requested tool is in our list.
    if tool not in TOOLS:
        print(f"Error:
