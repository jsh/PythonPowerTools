#!/usr/bin/env python3
#
# pydoc_wrapper - A pydoc wrapper for a Python-based PowerTools project

"""
Name: pydoc_wrapper
Description: pydoc wrapper to find docs in the current project
Author: jul, kaldor@cpan.org (Original Perl Author)
License: artistic2
"""

import sys
import os
from pydoc import cli

def main():
    """
    Configures the Python path and runs the standard pydoc tool.
    """
    # Get the absolute path of the directory containing this script.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Prepend the script's directory to Python's module search path.
    # This is the equivalent of Perl's 'unshift @INC, ...'.
    # It allows pydoc to find modules located in the same project.
    sys.path.insert(0, script_dir)

    # Execute the pydoc command-line interface. pydoc.cli() automatically
    # processes arguments from sys.argv and handles exiting, just like
    # 'Pod::Perldoc->run()' does in the original script.
    cli()

if __name__ == "__main__":
    main()
