#!/usr/bin/env python3

"""
Name: rot13
Description: Rotate the Latin letters by 13 positions
Author: Mark Rosetta (@marked on GitHub)
Contributor: brian d foy, bdfoy@cpan.org
License: artistic2
"""

import sys
import codecs
import fileinput

def main():
  """
  Reads from standard input or files and prints the ROT13 version.
  """
  try:
    for line in fileinput.input():
      # Encode the line using the built-in 'rot_13' codec
      encoded_line = codecs.encode(line, 'rot_13')
      # Write directly to standard output to preserve original line endings
      sys.stdout.write(encoded_line)
  except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
  main()
