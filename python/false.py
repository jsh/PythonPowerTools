#!/usr/bin/env python3
"""
Name: false
Description: exit unsuccessfully
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl

A Python port of the 'false' utility.

This program exits with a non-zero status code to indicate failure,
emulating the standard UNIX `false` command. It takes no arguments
and its operation is not affected by any environment variables.
"""

import sys

def main():
  """Exits the program with a status code of 1."""
  sys.exit(1)

if __name__ == "__main__":
  main()
