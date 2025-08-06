#!/usr/bin/env python3
"""
Name: random
Description: display lines at random, or exit with a random value
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl

A Python port of the 'random' utility.

This script has two modes:
1.  Default: Reads lines from standard input and prints each line with a
    probability of 1/N, where N is the 'denominator'.
2.  Exit Mode (-e): Exits immediately with a random status code from
    0 to N-1.
"""

import sys
import random
import argparse

__version__ = "1.3"

def main():
    """Parses arguments and executes one of the two random modes."""
    parser = argparse.ArgumentParser(
        description="Select lines from standard input randomly or exit with a random value.",
        usage="%(prog)s [-er] [denominator]"
    )
    parser.add_argument(
        '-e', '--exit-mode',
        action='store_true',
        help='Exit with a random value from 0 to denominator-1 instead of filtering input.'
    )
    parser.add_argument(
        '-r', '--unbuffered',
        action='store_true',
        help='Use unbuffered output when filtering lines.'
    )
    parser.add_argument(
        'denominator',
        nargs='?',
        type=int,
        default=2,
        help='The denominator for the probability 1/N (default: 2).'
    )

    args = parser.parse_args()
    denominator = args.denominator

    # Validate the denominator to prevent division by zero.
    # argparse already ensures it's an integer.
    if denominator == 0:
        parser.error("denominator cannot be zero.")

    # --- Mode 1: Exit with a random status code ---
    if args.exit_mode:
        # random.randrange(N) returns a random integer from 0 to N-1.
        random_code = random.randrange(denominator)
        sys.exit(random_code)

    # --- Mode 2: Filter standard input randomly (Default Behavior) ---
