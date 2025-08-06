#!/usr/bin/env python3
"""
Name: true
Description: exit successfully
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl

A Python port of the 'true' utility.

This program exits with a status code of 0 to indicate success,
emulating the standard UNIX `true` command. It takes no arguments
and its operation is not affected by any environment variables.
"""

import sys

def main():
  """Exits the program with a status code of 0."""
  sys.exit(0)

if __name__ == "__main__":
  main()
