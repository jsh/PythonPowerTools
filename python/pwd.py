#!/usr/bin/env python3
"""
Name: pwd
Description: working directory name
Author: Kevin Meltzer, perlguy@perlguy.com (Original Perl Author)
License: perl

A Python port of the 'pwd' utility.

Prints the pathname of the current working directory. By default, it
resolves all symbolic links (-P behavior). The -L option will display
the logical path from the PWD environment variable if it is valid.
"""

import os
import sys
import argparse

# Define exit codes for clarity
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

def get_logical_pwd():
    """
    Tries to get the logical PWD from the environment, falling back
    to the physical path if it's not available or invalid.
    """
    try:
        # The 'logical' path is what's in the $PWD environment variable.
        pwd_env = os.getenv('PWD')
        # We must verify that $PWD still points to the current directory.
        if pwd_env and os.path.samefile(pwd_env, '.'):
             return pwd_env
    except (TypeError, FileNotFoundError):
        # Fallback if PWD is not set, or is no longer a valid path.
        pass
    
    # If the PWD environment variable isn't valid, the behavior of `pwd -L`
    # is to fall back to the physical path.
    return get_physical_pwd()

def get_physical_pwd():
    """
    Gets the physical PWD, resolving all symlinks. This is the default.
    """
    try:
        # os.getcwd() returns the canonical, physical path.
        return os.getcwd()
    except OSError as e:
        # This can happen if the directory was deleted or permissions changed.
        # We print the error and return None to signal failure.
        print(f"pwd: error retrieving current directory: {e.strerror}",
              file=sys.stderr)
        return None

def main():
    """Parses arguments and prints the current working directory."""
    parser = argparse.ArgumentParser(
        description="Print the full filename of the current working directory.",
        usage="%(prog)s [-L|-P]",
        add_help=False
    )
    # Use a mutually exclusive group because -L and -P cannot be used together.
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-L',
        action='store_true',
        help='print the value of $PWD if it names the current working directory'
    )
    group.add_argument(
        '-P',
        action='store_true',
        help='print the physical directory, without any symbolic links (default)'
    )
    parser.add_argument(
        '-h', '--help', 
        action='help', 
        help='show this help message and exit'
    )

    args = parser.parse_args()
