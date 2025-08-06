#!/usr/bin/env python3

"""
Name: grep
Description: search for regular expressions and print
Author: Tom Christiansen, tchrist@perl.com
Author: Greg Bacon, gbacon@itsc.uah.edu
Author: Paul Grassie
License: perl
"""

import sys
import os
import re
import argparse
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
import shutil
import glob

# Constants
EX_MATCHED = 0
EX_NOMATCH = 1
EX_FAILURE = 2
VERSION = '1.019'

# Global variables
Me = os.path.basename(sys.argv[0])
Errors = 0
Grand_Total = 0
# A simple way to handle compression based on file extension
COMPRESS = {
    'z': 'zcat',
    'gz': 'zcat',
    'Z': 'zcat',
    'bz2': 'bzcat',
    'zip': 'unzip -c',
}

def version_message():
    """Prints version message and exits."""
    print(f"{Me} version {VERSION}")
    sys.exit(EX_MATCHED)

def usage():
    """Prints usage message and exits."""
    sys.stderr.write(f"""usage: {Me} [-acFgHhIiLlnqRrsTuvwxZ] [-e pattern] [-A NUM] [-B NUM] [-C NUM]
          [-m NUM] [-f pattern-file] [pattern] [file...]

Options:
	-A   show lines after each matching line
	-a   treat binary files as plain text files
	-B   show lines before each matching line
	-C   show lines of context around each matching line
	-c   give count of lines matching
	-e   expression (for exprs beginning with -)
	-F   search for fixed strings (disable regular expressions)
	-f   file with expressions
	-g   highlight matches
	-H   show filenames
	-h   hide filenames
	-I   ignore binary files
	-i   case insensitive
	-L   list filenames which do not match
	-l   list filenames matching
	-m   limit total matches per file
	-n   number lines
	-q   quiet; nothing is written to standard output
	-r   recursive on directories or dot if none
	-s   suppress errors for failed file and dir opens
	-T   trace files as opened
	-u   underline matches
	-v   invert search sense (lines that DON'T match)
	-w   word boundaries only
	-x   exact matches only
	-Z   force grep to behave as zgrep
""")
    sys.exit(EX_FAILURE)

def get_term_escapes(opt_g, opt_u):
    """
    Finds terminal escapes for highlighting.
    This is a simplified port of the original Perl function.
    """
    try:
        if opt_g:
            return subprocess.check_output(['tput', 'smso']).decode(), subprocess.check_output(['tput', 'rmso']).decode()
        elif opt_u:
            return subprocess.check_output(['tput', 'smul']).decode(), subprocess.check_output(['tput', 'rmul']).decode()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    
    return '', ''

def parse_args():
    """
    Parses command-line arguments and constructs a unified options object and a matcher function.
    """
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    
    # Options
    parser.add_argument('-A', type=int)
    parser.add_argument('-a', action='store_true')
    parser.add_argument('-B', type=int)
    parser.add_argument('-C', type=int)
    parser.add_argument('-c', action='store_true')
    parser.add_argument('-e', action='append', default=[], help='pattern expression')
    parser.add_argument('-F', action='store_true', help='fixed strings')
    parser.add_argument('-f', type=argparse.FileType('r'), help='file with expressions')
    parser.add_argument('-g', action='store_true', help='highlight matches')
    parser.add_argument('-H', action='store_true', help='show filenames')
    parser.add_argument('-h', action='store_true', help='hide filenames')
    parser.add_argument('-I', action='store_true', help='ignore binary files')
    parser.add_argument('-i', action='store_true', help='case insensitive')
    parser.add_argument('-L', action='store_true', help='list non-matching files')
    parser.add_argument('-l', action='store_true', help='list matching files')
    parser.add_argument('-m', type=int, help='max matches per file')
    parser.add_argument('-n', action='store_true', help='number lines')
    parser.add_argument('-q', action='store_true', help='quiet')
    parser.add_argument('-R', dest='r', action='store_true', help='recursive')
    parser.add_argument('-r', action='store_true', help='recursive')
    parser.add_argument('-s', action='store_true', help='suppress errors')
    parser.add_argument('-T', action='store_true', help='trace files')
    parser.add_argument('-u', action='store_true', help='underline matches')
    parser.add_argument('-v', action='store_true', help='invert match')
    parser.add_argument('-w', action='store_true', help='word boundaries')
    parser.add_argument('-x', action='store_true', help='exact matches')
    parser.add_argument('-Z', action='store_true', help='zgrep mode')
    
    # Positional arguments
    parser.add_argument('pattern', nargs='?', help='pattern')
    parser.add_argument('files', nargs='*', default=[])
    
    args = sys.argv[1:]
    
    if not args or args[0] in ['--help', '-h', '-?']:
        usage()
    
    # Combine -e and -f patterns
    patterns = []
    
    # Process -e
    e_args = [a for a in args if a.startswith('-e')]
    for e_arg in e_args:
        idx = args.index(e_arg)
        if len(e_arg) > 2:
            patterns.append(e_arg[2:])
        else:
            patterns.append(args[idx + 1])
            args.pop(idx + 1)
        args.pop(idx)
        
    # Process -f
    f_arg_idx = -1
    if '-f' in args:
        f_arg_idx = args.index('-f')
        f_path = args[f_arg_idx + 1]
        try:
            with open(f_path, 'r') as f_file:
                for line in f_file:
                    patterns.append(line.strip())
            args.pop(f_arg_idx)
            args.pop(f_arg_idx)
        except IOError as e:
            sys.stderr.write(f"{Me}: Can't open '{f_path}': {e}\n")
            sys.exit(EX_FAILURE)
    
    # Parse remaining arguments
    parsed = parser.parse_args(args)
    
    # If no patterns from -e or -f, the first non-option argument is the pattern
    if not patterns:
        if parsed.pattern:
            patterns.append(parsed.pattern)
            parsed.pattern = None
        else:
            usage()
            
    # Finalize options
    opts = vars(parsed)
    if opts.get('C'):
        opts['A'] = opts['B'] = opts['C']
    if opts.get('L'):
        opts['l'] = False
    if opts.get('r') and not opts.get('files'):
        opts['files'] = ['.']
        
    # Highlight setup
    SO, SE = '', ''
    if opts.get('g') or opts.get('u'):
        SO, SE = get_term_escapes(opts.get('g'), opts.get('u'))
        if not (SO and SE):
            opts['g'] = opts['u'] = False
            
    # Construct regex pattern
    regex_flags = re.DOTALL
    if opts.get('i'):
        regex_flags |= re.IGNORECASE
        
    if opts.get('F'):
        if opts.get('g') or opts.get('u') or opts.get('w'):
            sys.stderr.write(f"{Me}: -g, -u and -w are incompatible with -F\n")
            sys.exit(EX_FAILURE)
        
        # Fixed string matching, a simple `in` check is sufficient
        def fgrep_matcher(line, patterns):
            for pat in patterns:
                if pat in line:
                    return True
            return False
            
        matcher = fgrep_matcher
        
    else:
        # Construct the final regex
        final_pattern = '|'.join(f'(?:{p})' for p in patterns)
        
        if opts.get('w'):
            final_pattern = f'\\b({final_pattern})\\b'
        
        if opts.get('x'):
            final_pattern = f'^{final_pattern}$'
            
        try:
            compiled_regex = re.compile(final_pattern, flags=regex_flags)
        except re.error as e:
            sys.stderr.write(f"{Me}: bad pattern: {e}\n")
            sys.exit(EX_FAILURE)
            
        def regex_matcher(line, patterns_list):
            if opts.get('v'):
                return not compiled_regex.search(line)
            else:
                return compiled_regex.search(line)
        
        matcher = regex_matcher
    
    return opts, patterns, matcher, SO, SE, parsed.files

def match_file(options, patterns, matcher, files, SO, SE):
    """
    Main loop for processing files and directories.
    """
    global Grand_Total, Errors
    
    file_queue = deque(files)
    
    while file_queue:
        file_path = file_queue.popleft()
        
        is_binary = False
        
        if file_path == '-':
            file_name = '<STDIN>'
            file_handle = sys.stdin
        else:
            file_name = file_path
            
            if Path(file_path).is_dir():
                if not options.get('r'):
                    sys.stderr.write(f"grep: {file_path}: Is a directory\n")
                    Errors += 1
                    continue
                
                try:
                    for entry in os.scandir(file_path):
                        if entry.name not in ['.', '..']:
                            file_queue.append(entry.path)
                except OSError as e:
                    if not options.get('s'):
                        sys.stderr.write(f"grep: {file_path}: {e}\n")
                        Errors += 1
                continue
                
            try:
                # Handle compressed files
                ext = Path(file_path).suffix[1:].lower()
                if options.get('Z') and ext in COMPRESS:
                    cmd = COMPRESS[ext].split() + [file_path]
                    file_handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True).stdout
                    file_name = file_path
                else:
                    file_handle = open(file_path, 'r', errors='ignore')
                
                if Path(file_path).is_symlink() and Path(file_path).is_dir() and len(files) != 1:
                    if options.get('T'):
                        sys.stderr.write(f"grep: '{file_path}' is a symlink to a directory\n")
                    continue
                    
                is_binary = Path(file_path).is_file() and not Path(file_path).is_symlink() and options.get('I') and 'text' not in str(subprocess.check_output(['file', file_path]))
                if is_binary:
                    if options.get('I'):
                        continue
                    if not options.get('a'):
                        sys.stderr.write(f"grep: {file_path}: binary file matches\n")
                        continue
            except IOError as e:
                if not options.get('s'):
                    sys.stderr.write(f"grep: {file_path}: {e}\n")
                    Errors += 1
                continue

        line_count = 0
        matches_found = 0
        context_before = deque(maxlen=options.get('B') if options.get('B') else 0)
        context_after = 0
        
        for line in file_handle:
            line_count += 1
            
            if options.get('v') and matcher(line, patterns):
                if not options.get('q'):
                    print_line(file_name, line_count, line, options, False, '', '', False)
                matches_found += 1
                if options.get('l'):
                    print(file_name)
                    break
            elif not options.get('v') and matcher(line, patterns):
                # A match was found
                
                if context_before:
                    for old_line in context_before:
                        print_line(file_name, line_count, old_line, options, False, '', '', False)
                    print('--')
                
                if options.get('g') or options.get('u'):
                    highlighted_line = re.sub(matcher_re.pattern, f'{SO}\\g<0>{SE}', line, flags=matcher_re.flags)
                    print_line(file_name, line_count, highlighted_line, options, True, '', '', True)
                else:
                    print_line(file_name, line_count, line, options, True, '', '', False)

                matches_found += 1
                context_after = options.get('A') if options.get('A') else 0
                
            elif context_after > 0:
                print_line(file_name, line_count, line, options, False, '', '', False)
                context_after -= 1
                
            else:
                context_before.append(line)

        if options.get('c'):
            print_line(file_name, 0, str(matches_found), options, False, '', '', False, count_mode=True)
            
        if options.get('L') and matches_found == 0:
            print(file_name)
            
        Grand_Total += matches_found
        
        if file_handle is not sys.stdin:
            file_handle.close()

def print_line(file_name, line_num, line, options, is_match, SO, SE, is_highlighted, count_mode=False):
    """Formats and prints a line of output."""
    if options.get('q'):
        return
        
    prefix = ''
    if options.get('H') or (options.get('r') or len(sys.argv) > 2) and not options.get('h'):
        prefix += f'{file_name}:'

    if options.get('n') and not count_mode:
        prefix += f'{line_num}:'
    
    if count_mode:
        print(f"{prefix}{line}")
    elif is_highlighted:
        print(f"{prefix}{line.strip()}")
    else:
        print(f"{prefix}{line.strip()}")
    
if __name__ == '__main__':
    opts, patterns, matcher, SO, SE, files = parse_args()
    
    if opts.get('F'):
        matcher_func = lambda line, p: matcher(line, p)
        # Store fixed patterns for `fgrep` mode
        matcher_re = None
    else:
        matcher_re = re.compile('|'.join(f'(?:{p})' for p in patterns), flags=re.DOTALL | (re.IGNORECASE if opts.get('i') else 0))
        matcher_func = lambda line, p: matcher(line, p)

    match_file(opts, patterns, matcher_func, files, SO, SE)
    
    if Errors:
        sys.exit(EX_FAILURE)
    elif Grand_Total > 0:
        sys.exit(EX_MATCHED)
    else:
        sys.exit(EX_NOMATCH)
