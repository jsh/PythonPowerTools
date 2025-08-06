#!/usr/bin/env python3

"""
Name: fortune
Description: print a random, hopefully interesting, adage
Author: Andy Murren, andy@murren.org
License: gpl
"""

import sys
import os
import re
import random
import struct
import time
from pathlib import Path
import argparse

# Constants
VERSION = '2.2'
HEADER_LENGTH = 4 * 6
STR_RANDOM = 0x1
STR_ORDERED = 0x2
STR_ROTATED = 0x4
SHORT_LENGTH = 160

# Globals
debug = False

def version_message():
    """Prints version message and exits."""
    print(f"{os.path.basename(sys.argv[0])} version {VERSION}")
    sys.exit(0)

def print_help():
    """Prints usage message and exits."""
    sys.stderr.write(f"""
Usage: {os.path.basename(sys.argv[0])} [-adefilosvw] [-n length] [-m pattern] [[N%] file/dir/all]

    See the POD for more information.

      -a Choose from all lists of maxims, both offensive and not.
      -d Enable debug messages
      -e Consider all fortune files to be of equal size.
      -f Print out the list of files which would be searched.
      -l Long dictums only.
      -m Print out all fortunes which match the regular expression pattern.
      -n Set the limit for long or short fortunes (default 160 chars)
      -o Choose only from potentially offensive aphorisms.
      -s Short apothegms only.
      -i Ignore case for -m patterns.
      -v Show version number.
      -w Wait before termination for a calculated amount of time.

      all Same as the -a switch.

      N% file/dir
          You can specify a specific file or directory which contains
          one or more files. Any of these may be preceded by a percentage,
          which is a number N between 0 and 100 inclusive, followed by a %.
""")
    sys.exit(1)

def main():
    """Main function to parse arguments and run the fortune program."""
    global debug, SHORT_LENGTH
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-a', action='store_true')
    parser.add_argument('-d', action='store_true')
    parser.add_argument('-e', action='store_true')
    parser.add_argument('-f', action='store_true')
    parser.add_argument('-l', action='store_true')
    parser.add_argument('-o', action='store_true')
    parser.add_argument('-s', action='store_true')
    parser.add_argument('-i', action='store_true')
    parser.add_argument('-v', action='store_true')
    parser.add_argument('-w', action='store_true')
    parser.add_argument('-m', type=str)
    parser.add_argument('-n', type=int)
    parser.add_argument('files', nargs='*')

    try:
        args = parser.parse_args()
    except argparse.ArgumentError:
        print_help()
    
    if args.v:
        version_message()

    debug = args.d
    if args.n:
        SHORT_LENGTH = args.n

    fortunes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fortunes')
    FORTDIRS = [fortunes_path]
    OFFDIRS = [os.path.join(fortunes_path, 'off')]

    top_item = {
        'name': 'Top level file/directory list',
        'num_choices': 100,
        'files': [{
            'name': 'Percent specified',
            'files': [],
            'percent': 0
        }, {
            'name': 'Percent unspecified',
            'files': [],
            'percent': 100
        }]
    }

    build_file_list(top_item['files'][0], top_item['files'][1], args.files, FORTDIRS, OFFDIRS, args.o, args.a)

    if args.m:
        for item in list_files(top_item):
            print_matching_fortunes(item, args.m, args.i, args.s, args.l, SHORT_LENGTH)
    elif args.f:
        for item in list_files(top_item):
            print_file_list(item)
    else:
        pfile = pick_file(top_item)
        if pfile is None:
            sys.stderr.write("fortune: no files to choose from!\n")
            sys.exit(1)
        pick = pick_fortune(pfile, args.s, args.l, SHORT_LENGTH)
        print_fortune(pfile, pick, args.w)

# Subroutines

def build_file_list(specified, unspecified, argv, FORTDIRS, OFFDIRS, opt_o, opt_a):
    """Builds a list of available files based on command-line arguments."""
    if debug:
        sys.stderr.write(f"Building file list. Containers are {specified['name']} and {unspecified['name']}\n")

    if argv:
        build_w_args(specified, unspecified, argv, FORTDIRS, OFFDIRS, opt_o, opt_a)
    else:
        add_all(unspecified, FORTDIRS, OFFDIRS, opt_o, opt_a)

def build_w_args(specified, unspecified, argv, FORTDIRS, OFFDIRS, opt_o, opt_a):
    """Builds the file list based on files or directories given on the cmd line."""
    if debug:
        sys.stderr.write(f"\nargv ({len(argv)} arguments):\n")
        for arg in argv:
            sys.stderr.write(f"{arg}\n")
        sys.stderr.write("\n\n")

    percent = None
    total_percent = 0
    
    for arg in argv:
        match = re.match(r'^(\d+)\%$', arg)
        if match:
            percent = int(match.group(1))
            total_percent += percent
        else:
            if percent is not None:
                add_item(specified, arg, percent, FORTDIRS, OFFDIRS, opt_o, opt_a)
                percent = None
            else:
                add_item(unspecified, arg, None, FORTDIRS, OFFDIRS, opt_o, opt_a)
    
    if percent is not None:
        sys.stderr.write("fortune: percentages must precede files\n")
        sys.exit(1)

    if total_percent > 100:
        sys.stderr.write(f"fortune: probabilities sum to {total_percent} %!\n")
        sys.exit(1)

def add_all(file_list, FORTDIRS, OFFDIRS, opt_o, opt_a, percent=None):
    """Adds all default fortunes to the specified file_list container."""
    if percent is not None:
        all_item = {
            'name': 'all',
            'percent': percent,
            'files': []
        }
        add_to_list(file_list, all_item)
        file_list = all_item
        
    for d in fortune_dirs(FORTDIRS, OFFDIRS, opt_o, opt_a):
        add_dir(file_list, d, FORTDIRS, OFFDIRS, opt_o, opt_a)

def add_item(file_list, name, percent, FORTDIRS, OFFDIRS, opt_o, opt_a):
    """Adds a file or directory to the container."""
    container_name = file_list.get('name') or file_list.get('path')
    if debug:
        sys.stderr.write(f"trying to add item {name} to {container_name}\n")
    
    if name == 'all':
        add_all(file_list, FORTDIRS, OFFDIRS, opt_o, opt_a, percent)
        return

    path = find_path(name, FORTDIRS, OFFDIRS, opt_o, opt_a)
    if debug:
        sys.stderr.write(f"path = {path}\n")

    if Path(path).is_dir():
        add_dir(file_list, path, FORTDIRS, OFFDIRS, opt_o, opt_a, percent)
    elif is_fortune_file(path, opt_o, opt_a):
        add_file(file_list, os.path.basename(path), path, percent)
    else:
        sys.stderr.write("fortune: VERY BAD ERROR in function add_item\n")
        sys.exit(1)

def find_path(name, FORTDIRS, OFFDIRS, opt_o, opt_a):
    """Finds the full path of a fortune file or directory."""
    if Path(name).is_dir() or is_fortune_file(name, opt_o, opt_a):
        return name

    if not os.path.isabs(name):
        for d in fortune_dirs(FORTDIRS, OFFDIRS, opt_o, opt_a):
            abs_path = os.path.join(d, name)
            if is_fortune_file(abs_path, opt_o, opt_a):
                return abs_path
    
    sys.stderr.write(f"fortune: {name} not a fortune file or directory\n")
    sys.exit(1)

def fortune_dirs(FORTDIRS, OFFDIRS, opt_o, opt_a):
    """Returns a list of default fortune directories."""
    searchdirs = []
    if not opt_o:
        searchdirs.extend(FORTDIRS)
    if opt_o or opt_a:
        searchdirs.extend(OFFDIRS)
    return searchdirs

checked_fortune_files = {}

def is_fortune_file(path, opt_o, opt_a):
    """Checks if a file is a valid fortune file."""
    msg = f"is_fortune_file({path}) returns"
    if path in checked_fortune_files:
        if debug: sys.stderr.write(f"{msg} TRUE (already checked)\n")
        return True
    if not Path(path).is_file() or not os.access(path, os.R_OK):
        if debug: sys.stderr.write(f"{msg} FALSE (can't read file)\n")
        return False
    if path.endswith(('.dat', '.pos', '.c', '.h', '.p', '.i', '.f', '.pas', '.ftn', '.ins.c', '.ins.pas', '.ins.ftn', '.sml')):
        if debug: sys.stderr.write(f"{msg} FALSE (file has illegal suffix)\n")
        return False
    
    datfile = f"{path}.dat"
    if not Path(datfile).is_file() or not os.access(datfile, os.R_OK):
        if debug: sys.stderr.write(f"{msg} FALSE (no \".dat\" file)\n")
        return False
    
    is_off = is_offensive(path)
    if opt_o and not is_off:
        if debug: sys.stderr.write(f"{msg} FALSE (inoffensive files not allowed)\n")
        return False
    if is_off and not (opt_a or opt_o):
        if debug: sys.stderr.write(f"{msg} FALSE (offensive files not allowed)\n")
        return False
        
    checked_fortune_files[path] = True
    if debug: sys.stderr.write(f"{msg} TRUE\n")
    return True

def is_offensive(path):
    """Returns true if the fortune file is believed to be offensive."""
    return bool(re.search(r'-o$|limerick$', os.path.basename(path))) or any(path.startswith(d) for d in OFFDIRS)

def is_dir(item):
    """Returns true if the item is a container/directory."""
    return 'files' in item

def list_files(d):
    """Returns the list of files in a container."""
    return d.get('files', [])

def add_dir(file_list, path, FORTDIRS, OFFDIRS, opt_o, opt_a, percent=None):
    """Recursively adds a directory's files to a container."""
    d_item = {'path': path, 'percent': percent, 'files': []}
    add_to_list(file_list, d_item)

    try:
        for entry in os.listdir(path):
            abs_path = os.path.join(path, entry)
            if not entry.startswith('.') and is_fortune_file(abs_path, opt_o, opt_a):
                add_file(d_item, entry, abs_path)
    except OSError as e:
        sys.stderr.write(f"could not open {path}: {e}\n")
        return

    if not list_files(d_item):
        if percent:
            sys.stderr.write(f"No acceptable fortune files in directory {path}\n")
            sys.exit(1)
        if debug:
            sys.stderr.write(f"add_dir: no acceptable files in directory {path}\n")

def add_file(file_list, name, path, percent=None):
    """Adds a single fortune file to the container."""
    add_to_list(file_list, {'name': name, 'path': path, 'percent': percent})
    container_name = file_list.get('name') or file_list.get('path')
    if debug:
        sys.stderr.write(f"Added file {path} to {container_name}\n")

def add_to_list(file_list, item):
    """Adds an item to the files list of a container."""
    file_list['files'].append(item)

def print_matching_fortunes(file, match, opt_i, opt_s, opt_l, short_length):
    """Searches for and prints all matching fortunes."""
    if debug: sys.stderr.write(f"Searching for matches in {file['name']}...\n")
    if is_dir(file):
        for item in list_files(file):
            print_matching_fortunes(item, match, opt_i, opt_s, opt_l, short_length)
        return
    
    read_table(file)
    if not num_choices(file, opt_s, opt_l, short_length):
        return

    try:
        with open(file['path'], 'r', encoding='latin-1') as f:
            fortunes = f.read().split(f"\n{file['delim']}\n")
            matching_fortunes = [f for f in fortunes if is_wrong_length(len(f), opt_s, opt_l, short_length) and fortune_match(f, match, opt_i)]
            if matching_fortunes:
                print(f"{file['name']}\n%\n")
                print('\n%\n'.join(matching_fortunes))
    except IOError as e:
        sys.stderr.write(f"Can't open {file['path']}: {e}\n")

def print_file_list(item, percent=100.0, depth=0):
    """Lists files with their probability of being chosen."""
    num_choices_total = num_choices(item) or 1
    for sub_item in list_files(item):
        prob = percent * (num_chances(sub_item, num_choices_total) / num_choices_total) if num_choices_total > 0 else 0
        print(f"{'    ' * depth}{prob:5.2f}% {sub_item.get('name') or sub_item.get('path')}")
        print_file_list(sub_item, prob, depth + 1)

def pick_file(item):
    """Randomly picks a fortune file based on probabilities."""
    if not is_dir(item):
        return item

    num_choices_total = num_choices(item)
    if not num_choices_total:
        return None
        
    choice = random.randrange(num_choices_total)
    for sub_item in list_files(item):
        chances = num_chances(sub_item, num_choices_total)
        if chances > choice:
            return pick_file(sub_item)
        choice -= chances
    return None

def num_chances(item, parent_choices=1):
    """Returns the number of chances an item has of being chosen."""
    if item.get('percent') is not None:
        return item['percent']
    return num_choices(item)

def num_choices(item, opt_e=False, opt_s=False, opt_l=False, short_length=160):
    """Returns the number of choices an item contains."""
    if 'num_choices' in item:
        return item['num_choices']
    
    if is_dir(item):
        item['num_choices'] = sum(num_chances(f) for f in list_files(item))
        return item['num_choices']
    
    if opt_e:
        return 1
    
    read_table(item)
    if 'num_strings' not in item:
        return 0
    
    item['num_choices'] = item['num_strings']
    return item['num_choices']

def is_wrong_length(length, opt_s, opt_l, short_length):
    """Returns true if the fortune length is too long or too short."""
    return (opt_s and length > short_length) or (opt_l and length <= short_length)

def fortune_match(fortune, match, opt_i):
    """Returns true if the fortune matches the regex pattern."""
    if opt_i:
        return re.search(match, fortune, re.IGNORECASE)
    return re.search(match, fortune)

def print_fortune(file, index, opt_w):
    """Prints a single fortune and handles the wait option."""
    fortune_text = read_fortune(file, index)
    print(fortune_text)
    
    if opt_w:
        time.sleep(len(fortune_text) / 75.0)

def fortune_length(file, index):
    """Returns the length of a specific fortune."""
    if file.get('index') == index:
        return file['fortune_length']

    read_fortune(file, index)
    return file['fortune_length']

def is_rotated(file):
    """Returns true if the fortune file is encoded with ROT13."""
    return file.get('flags', 0) & STR_ROTATED

def is_unordered(file):
    """Returns true if the datfile's offsets are unordered."""
    return not (file.get('flags', 0) & (STR_RANDOM | STR_ORDERED))

def read_table(file):
    """Reads the header table from the dat file."""
    if 'num_strings' in file:
        return
        
    datfile = f"{file['path']}.dat"
    try:
        with open(datfile, 'rb') as f:
            header = f.read(HEADER_LENGTH)
            if len(header) < HEADER_LENGTH:
                raise IOError("Failed to read header")
            
            (version, num_strings, longest, shortest, flags) = struct.unpack("IIIII", header[:20])
            delim = struct.unpack("s", header[20:21])[0]
            
            file.update({
                'version': version,
                'num_strings': num_strings,
                'longest': longest,
                'shortest': shortest,
                'flags': flags,
                'delim': delim
            })
    except (IOError, struct.error) as e:
        sys.stderr.write(f"Failed to read table from {datfile}: {e}\n")

def read_fortune(file, index):
    """Reads a fortune from a file at a given index."""
    if file.get('index') == index and file.get('fortune') is not None:
        return file['fortune']

    clear_fortune(file)
    file['index'] = index
    
    offset_length = (os.path.getsize(f"{file['path']}.dat") - HEADER_LENGTH) // (file['num_strings'] + 1)
    
    offsets = read_offsets(file, index, offset_length)
    
    try:
        with open(file['path'], 'r', encoding='latin-1') as f:
            f.seek(offsets[0])
            fortune_text = ""
            while True:
                line = f.readline()
                if not line or line.strip() == file['delim'].decode('latin-1'):
                    break
                fortune_text += line
    except IOError as e:
        sys.stderr.write(f"Can't read fortune from {file['path']}: {e}\n")
        return ""

    if is_rotated(file):
        fortune_text = fortune_text.translate(
            str.maketrans('N-ZA-Mn-za-m', 'A-Za-z')
        )
    
    file['fortune'] = fortune_text
    file['fortune_length'] = len(fortune_text)
    return fortune_text
    
def read_offsets(file, index, offset_length):
    """Reads the byte offsets from the datfile."""
    offsets = [0, 0]
    datfile = f"{file['path']}.dat"
    try:
        with open(datfile, 'rb') as f:
            f.seek(HEADER_LENGTH + offset_length * index)
            for i in range(2):
                bytes_read = f.read(offset_length)
                if not bytes_read:
                    break
                offsets[i] = int.from_bytes(bytes_read, byteorder='big')
    except IOError as e:
        sys.stderr.write(f"Can't open {datfile}: {e}\n")
        sys.exit(1)
    return offsets

def clear_fortune(file):
    """Clears cached fortune data from a file object."""
    file['fortune'] = None
    file['index'] = None
    file['offsets'] = None

if __name__ == '__main__':
    main()
