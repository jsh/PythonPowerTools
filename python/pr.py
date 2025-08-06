#!/usr/bin/env python3

"""
Name: pr
Description: convert text files for printing
Author: Clinton Pierce, clintp@geeksalad.org
License: perl
"""

import sys
import os
import re
import time
from collections import deque

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
TRAILER_LENGTH = 5
DEFAULT_PAGE_LENGTH = 66
DEFAULT_PAGE_WIDTH = 72
DEFAULT_COLUMN_SEP_WIDTH = 1
NUMBER_CHAR = '\t'

# Global variables for options
length = DEFAULT_PAGE_LENGTH
trailer = True
multimerge = False
columns = 1
pagewidth = 0
offsetspaces = 0
doublespace = False
number = 0
startpageno = 1
header = None
formfeed = False
quietskip = False
column_sep = ''
roundrobin = False

# Global state for printing
program_name = os.path.basename(sys.argv[0])
curfile = ""
finfo = []
colinfo = []
pageno = 0

def usage(message=""):
    """Prints a usage message and exits with an error."""
    if message:
        sys.stderr.write(f"{program_name}: {message}\n")
    sys.stderr.write(
        f"usage: {program_name} [-columns] [+page] [-adFfrts] [-n[char][count]] [-schar] [-ei] [-w width]\n"
        f"       [-o count] [-l length] [-h text] files\n"
        f"       {program_name} -m [+page] [-adFfrts] [-n[char][count]] [-schar] [-ei] [-w width]\n"
        f"       [-o count] [-l length] [-h text] files\n"
    )
    sys.exit(EX_FAILURE)

def checknum(n):
    """Checks if a string is a valid positive integer and returns it."""
    try:
        n = int(n)
        if n < 0:
            raise ValueError
    except (ValueError, IndexError):
        sys.stderr.write(f"{program_name}: invalid number: '{n}'\n")
        sys.exit(EX_FAILURE)
    return n

def process_options():
    """Manually processes command-line arguments to handle a messy format."""
    global length, trailer, multimerge, columns, pagewidth, offsetspaces, \
           doublespace, number, startpageno, header, formfeed, quietskip, \
           column_sep, roundrobin

    args = sys.argv[1:]
    
    while args and args[0].startswith('-'):
        arg = args.pop(0)
        
        if arg == '-':
            break

        option = arg[1:]

        # Handle -s and -n with their optional arguments
        if option.startswith('s'):
            column_sep = option[1:] if len(option) > 1 else args.pop(0)
            continue
        if option.startswith('n'):
            match = re.match(r'n(.)?(\d*)', option)
            if match:
                char, count = match.groups()
                number = int(count) if count else 5 # POSIX default
                column_sep = char if char else '\t'
                continue
        
        # Simple boolean flags
        if 'm' in option: multimerge = True
        if 'a' in option: roundrobin = True
        if 'd' in option: doublespace = True
        if 'F' in option or 'f' in option: formfeed = True
        if 'r' in option: quietskip = True
        if 't' in option: trailer = False

        # Options with a value
        if 'w' in option: pagewidth = checknum(args.pop(0))
        if 'o' in option: offsetspaces = checknum(args.pop(0))
        if 'l' in option: length = checknum(args.pop(0))
        if 'h' in option: header = args.pop(0)
        
        # Handle -columns
        match = re.fullmatch(r'\d+', option)
        if match:
            columns = checknum(option)
            if columns <= 0:
                usage(f"invalid number of columns: {columns}")

    # Handle +page
    if args and args[0].startswith('+'):
        startpageno = checknum(args.pop(0)[1:])
    
    sys.argv = [sys.argv[0]] + args

def create_col():
    """Initializes a column structure with calculated dimensions."""
    global length, doublespace, trailer
    
    page_length = length - (TRAILER_LENGTH * 2 if trailer else 0)
    
    if page_length <= 0:
        trailer = False
        page_length = 1

    if doublespace:
        page_length = (page_length // 2) if (page_length % 2 == 0) else (page_length // 2 + 1)

    return {
        'height': page_length,
        'oheight': page_length,
        'cfile': "",
        'text': deque(),
    }

def still_have_files():
    """Checks if any file still has data to be read."""
    return any(not f['handle'].closed for f in finfo)

def fill_column_1(col, fstruct):
    """Fills a single column cell with one line from a file."""
    global roundrobin

    if col['height'] <= 0:
        return False
        
    try:
        line = fstruct['handle'].readline()
        if not line:
            return False
            
        line = line.rstrip('\n')
        line = line.replace('\f', '')
        
        col['cfile'] = fstruct['name']
        fstruct['lineno'] += 1
        
        col['text'].append({
            'text': line,
            'lineno': fstruct['lineno']
        })
        col['height'] -= 1
        
        return True
    except IOError:
        return False

def print_header():
    """Prints the page header."""
    global pageno, startpageno, curfile, header, columns, multimerge, trailer
    
    if not trailer:
        return
        
    sys.stdout.write("\n\n")
    sys.stdout.write(' ' * offsetspaces)
    sys.stdout.write(f"{time.strftime('%b %d %H:%M %Y')} ")

    if header:
        sys.stdout.write(f"{header} ")
    elif not multimerge:
        if finfo and finfo[0]['name'] != curfile:
            pageno = startpageno
            curfile = finfo[0]['name']
        sys.stdout.write(f"{curfile} ")
    
    sys.stdout.write(f"Page {pageno}\n\n\n")
    pageno += 1

def print_footer():
    """Prints the page footer."""
    if not trailer:
        return
    
    if formfeed:
        sys.stdout.write('\f')
    else:
        sys.stdout.write('\n' * TRAILER_LENGTH)

def print_page():
    """Prints a full page with all its columns."""
    global colinfo, columns, pagewidth, number, column_sep, doublespace, trailer

    col_width = (pagewidth / len(colinfo)) if colinfo else 0
    if number:
        col_width -= (len(NUMBER_CHAR) + number)
    
    print_header()

    for line_num in range(colinfo[0]['oheight']):
        sys.stdout.write(' ' * offsetspaces)

        for col_idx, column in enumerate(colinfo):
            if line_num < len(column['text']):
                line_data = column['text'][line_num]
                
                # Line numbering
                numbering = ""
                if number:
                    fmt = f"%{number}s"
                    numbering = f"{line_data['lineno']:{fmt}}"[-number:]
                    
                sys.stdout.write(numbering)
                if number:
                    sys.stdout.write(column_sep if column_sep else '\t')
                
                # Content
                text = line_data['text']
                if not column_sep and trailer:
                    fmt = f"%{-int(col_width)}s"
                    sys.stdout.write(f"{text:{fmt}}")
                else:
                    sys.stdout.write(text)
                    if col_idx < len(colinfo) - 1:
                        sys.stdout.write(column_sep)
            
            # Pad with spaces if the column is shorter
            else:
                if not column_sep and trailer:
                    fmt = f"%{-int(col_width + (len(column_sep) if column_sep else 0))}s"
                    sys.stdout.write(f"{' ':{fmt}}")
        
        sys.stdout.write('\n' * (2 if doublespace else 1))

    print_footer()

    # Reset columns for the next page
    colinfo.clear()
    for _ in range(columns):
        colinfo.append(create_col())

def main():
    """Main function to parse, format, and print files."""
    global pagewidth, column_sep, columns, multimerge, roundrobin, finfo, colinfo

    process_options()
    
    if not column_sep:
        pagewidth = DEFAULT_PAGE_WIDTH
    else:
        # A large default width for -s option as columns are not fixed-width
        pagewidth = 512

    for _ in range(columns):
        colinfo.append(create_col())

    if not sys.argv[1:]:
        sys.argv.append('-')
    
    for file_name in sys.argv[1:]:
        fh = None
        if file_name == '-':
            fh = sys.stdin
        else:
            if os.path.isdir(file_name):
                sys.stderr.write(f"{program_name}: '{file_name}' is a directory\n")
                sys.exit(EX_FAILURE)
            try:
                fh = open(file_name, 'r', encoding='utf-8')
            except IOError as e:
                if not quietskip:
                    sys.stderr.write(f"{program_name}: Can't open '{file_name}': {e}\n")
                    sys.exit(EX_FAILURE)
                continue
        
        finfo.append({
            'name': file_name,
            'handle': fh,
            'lineno': 0,
        })
    
    if roundrobin:
        current_file_idx = 0
        while any(not f['handle'].closed for f in finfo):
            for col in colinfo:
                if fill_column_1(col, finfo[current_file_idx]):
                    pass
                else:
                    # End of file, move to next
                    finfo[current_file_idx]['handle'].close()
                current_file_idx = (current_file_idx + 1) % len(finfo)
            print_page()

    elif multimerge:
        while still_have_files():
            for i, col in enumerate(colinfo):
                if i < len(finfo) and not finfo[i]['handle'].closed:
                    fill_column_1(col, finfo[i])
            print_page()

    else:
        for fstruct in finfo:
            while not fstruct['handle'].closed:
                for col in colinfo:
                    if not fill_column_1(col, fstruct):
                        break
                print_page()

    # Close all files
    for f in finfo:
        if not f['handle'].closed:
            f['handle'].close()
    
    sys.exit(EX_SUCCESS)

if __name__ == "__main__":
    main()
