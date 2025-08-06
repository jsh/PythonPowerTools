#!/usr/bin/env python3
"""
Name: whoami
Description: display effective user ID
Author: Oğuz Ersen, oguzersen@protonmail.com (Original Perl Author)
License: artistic2

A Python port of the 'whoami' utility.

Prints the username associated with the current effective user ID. It tries
several methods to determine the username to ensure cross-platform
compatibility.
"""

import os
import sys

# Define exit codes for clarity, mirroring the Perl script's constants.
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

# The 'pwd' module provides access to the Unix user account database
# and is not available on Windows. We handle its absence gracefully.
try:
    import pwd
except ImportError:
    pwd = None # Will be None on non-Unix systems


def get_username():
    """
    Determines the current user's name by trying a sequence of methods,
    returning the first successful result.
    """
    # Method 1: (Unix-only) Get username from effective user ID.
    # This is the most reliable method on POSIX systems.
    if pwd:
        try:
            return pwd.getpwuid(os.geteuid()).pw_name
        except (KeyError, OSError):
            # This can fail if the user ID doesn't exist in the password db.
            pass

    # Method 2: Get username from the controlling terminal.
    # This works on Unix and Windows but can fail if the script is not
    # run from an interactive terminal (e.g., in a cron job).
    try:
        login_name = os.getlogin()
        if login_name:
            return login_name
    except OSError:
        pass # No controlling terminal

    # Method 3: Fall back to common environment variables.
    # The order checks for common Unix variables first, then Windows.
    for var in ['USER', 'LOGNAME', 'USERNAME']:
        user = os.environ.get(var)
        if user:
            return user

    return None # Return None if all methods have failed.


def main():
    """
    Main script logic: check arguments, get the username, and print it.
    """
    # The 'whoami' command does not accept arguments.
    if len(sys.argv) > 1:
        print("usage: whoami", file=sys.stderr)
        sys.exit(EXIT_FAILURE)

    username = get_username()

    if username:
        print(username)
        sys.exit(EXIT_SUCCESS)
    else:
        # This case is rare, but we handle it just in case.
        print("whoami: cannot find username", file=sys.stderr)
        sys.
