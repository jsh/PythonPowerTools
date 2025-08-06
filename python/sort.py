#!/usr/bin/env python3

"""
Name: sort
Description: sort or merge text files
Author: Chris Nandor, pudge@pobox.com
License: perl
"""

import sys
import os
import re
import tempfile
import locale
import shutil
import functools
import argparse
from pathlib import Path
from collections import deque

VERSION = '1.01'

def usage():
    """Prints a usage message and exits."""
    sys.stderr.write("""
Usage: sort [-cmudfinrbD] [-o output_file]
    [-t field_separator] [-X regex_field_separator] [-R record_separator]
    [-k pos1[,pos2]] [+pos1 [-pos2]]
    [-y max_records] [-F max_files] [file ...]
""")
    sys.exit(1)

def _sort_file(opts, fhs, recs):
    """
    The main sorting logic, handling file reads, temporary file creation,
    and merging.
    """
    # Record separator, default to \n
    record_separator = opts.get('R', '\n')
    
    # Get input files
    input_files = opts.get('I', [])
    
    if not input_files:
        usage()
    
    # Check if file is sorted
    if opts.get('c'):
        last_rec = None
        for rec in _read_records(input_files[0], record_separator):
            if last_rec is not None:
                if not _is_sorted(last_rec, rec, opts):
                    return 0
                if opts.get('u') and last_rec == rec:
                    return 0 # Not unique
            last_rec = rec
        return 1

    # Merging files
    elif opts.get('m'):
        for filein in input_files:
            if Path(filein).is_dir():
                raise ValueError(f"sort: '{filein}' is a directory")
            fhs.append(open(filein, 'r'))
        
    # Main sorting loop
    else:
        for filein in input_files:
            if Path(filein).is_dir():
                raise ValueError(f"sort: '{filein}' is a directory")
            
            _debug(f"Sorting file {filein} ...\n", opts.get('D'))
            
            record_count = 0
            for rec in _read_records(filein, record_separator):
                recs.append(rec)
                record_count += 1
                
                if record_count >= opts.get('y', 200000):
                    _debug(f"{record_count} records reached in '{filein}'\n", opts.get('D'))
                    fhs.append(_write_temp(recs, opts))
                    recs.clear()
                    record_count = 0
                    
                    if len(fhs) >= opts.get('F', 40):
                        fhs = [_merge_files(opts, fhs, recs, None)]
                        _debug("\nCreating temp files ...\n", opts.get('D'))
            
        if recs:
            _debug("\nSorting leftover records ...\n", opts.get('D'))
            recs.sort(key=functools.cmp_to_key(lambda a, b: _sort_sub(a, b, opts)))

    # Merge remaining files and records
    output_file = opts.get('o')
    _merge_files(opts, fhs, recs, output_file)
    
    _debug("\nDone!\n\n", opts.get('D'))
    return 1

def _merge_files(opts, fhs, recs, output_file):
    """Merges sorted inputs into a single output stream."""
    
    # Open output file
    if output_file:
        outfile = open(output_file, 'w')
    else:
        outfile = sys.stdout
        
    records = []
    
    # Read one record from each file
    for fh in fhs:
        rec = fh.readline()
        if rec: records.append((rec, fh))
    
    # Add records from the main list
    for rec in recs:
        records.append((rec, None))

    while records:
        # Find the smallest record
        if opts.get('K'):
            records.sort(key=lambda x: x[0], reverse=opts.get('r'))
        else:
            records.sort(key=functools.cmp_to_key(lambda a,b: _sort_sub(a[0], b[0], opts)), reverse=opts.get('r'))

        smallest_rec, fh = records.pop(0)

        # Handle unique records
        if not opts.get('u') or (not records or _sort_sub(smallest_rec, records[0][0], opts) != 0):
            outfile.write(smallest_rec)
        
        # Read the next record from the file
        if fh:
            next_rec = fh.readline()
            if next_rec:
                records.append((next_rec, fh))

    for fh in fhs:
        fh.close()
    
    if output_file:
        outfile.close()
        
    return outfile

def _read_records(filename, separator):
    """A generator to read records from a file with a given separator."""
    if filename == '-':
        fh = sys.stdin
    else:
        fh = open(filename, 'r', newline='')
    
    if separator == '\n':
        yield from fh
    else:
        buffer = ''
        while True:
            chunk = fh.read(4096)
            if not chunk:
                if buffer: yield buffer
                break
            buffer += chunk
            while separator in buffer:
                rec, buffer = buffer.split(separator, 1)
                yield rec + separator
        
    if filename != '-':
        fh.close()

def _write_temp(recs, opts):
    """Writes sorted records to a temporary file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    
    recs.sort(key=functools.cmp_to_key(lambda a, b: _sort_sub(a, b, opts)))
    
    temp_file.writelines(recs)
    temp_file.seek(0)
    
    _debug(f"New tempfile: {temp_file.name}\n", opts.get('D'))
    
    return temp_file

def _is_sorted(rec1, rec2, opts):
    """Checks if two records are in sorted order."""
    return _sort_sub(rec1, rec2, opts) <= 0

def _sort_sub(a, b, opts):
    """A comparison function that wraps the sorting logic."""
    if opts.get('K'):
        # No keydefs, simple comparison
        if opts.get('n'):
            res = float(a) - float(b)
        else:
            res = locale.strcoll(a, b)
    else:
        # With keydefs, more complex logic is needed
        # This is a simplified version, as the original Perl logic
        # is extremely complex and hard to port directly
        res = 0
        for k in opts['k']:
            key_a = _extract_key(a, k, opts)
            key_b = _extract_key(b, k, opts)
            
            if k.get('n'):
                res = float(key_a) - float(key_b)
            else:
                res = locale.strcoll(key_a, key_b)
            
            if res != 0:
                break
                
    if opts.get('r'):
        res = -res
        
    return res

def _extract_key(record, k_opts, global_opts):
    """Extracts a key from a record based on keydef options."""
    field_separator = k_opts.get('t', global_opts.get('t', ' '))
    fields = record.split(field_separator)
    
    start_field = k_opts.get('ksf', 0)
    end_field = k_opts.get('kff', len(fields))
    
    key_fields = fields[start_field:end_field]
    
    key = ''.join(key_fields)
    
    if k_opts.get('b'):
        key = key.lstrip()
    if k_opts.get('f'):
        key = key.upper()
    
    return key


def _debug(msg, enabled):
    """Prints debug messages to stderr if enabled."""
    if enabled:
        sys.stderr.write(msg)

def main():
    """Main function to parse arguments and run the sorting process."""
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    
    parser.add_argument('-c', action='store_true', help='Check if file is sorted.')
    parser.add_argument('-m', action='store_true', help='Merge sorted files.')
    parser.add_argument('-u', action='store_true', help='Suppress duplicate keys.')
    parser.add_argument('-d', action='store_true', help='Dictionary order.')
    parser.add_argument('-f', action='store_true', help='Fold lowercase to uppercase.')
    parser.add_argument('-i', action='store_true', help='Ignore non-printable characters.')
    parser.add_argument('-n', action='store_true', help='Numeric sort.')
    parser.add_argument('-r', action='store_true', help='Reverse sort order.')
    parser.add_argument('-b', action='store_true', help='Ignore leading blanks.')
    parser.add_argument('-D', action='store_true', help='Enable debugging.')
    parser.add_argument('-o', type=str, help='Output file.')
    parser.add_argument('-t', type=str, help='Field separator.')
    parser.add_argument('-X', type=str, help='Regex field separator.')
    parser.add_argument('-R', type=str, help='Record separator.')
    parser.add_argument('-y', type=int, help='Max records to hold in memory.')
    parser.add_argument('-F', type=int, help='Max temp files to hold open.')
    parser.add_argument('-k', action='append', help='Sort key definition.')
    
    # Handle obsolete +pos -pos syntax
    args = sys.argv[1:]
    new_args = []
    
    for i in range(len(args)):
        arg = args[i]
        
        if re.match(r'^\+(\d+)(?:\.(\d+))?([bdfinr]+)?$', arg):
            key_def = arg.lstrip('+')
            if i + 1 < len(args) and re.match(r'^-(\d+)(?:\.(\d+))?([bdfinr]+)?$', args[i+1]):
                key_def += ',' + args[i+1].lstrip('-')
                new_args.append(f'-k{key_def}')
                args[i+1] = None
            else:
                new_args.append(f'-k{key_def}')
            
        elif arg is not None:
            new_args.append(arg)
            
    parsed_args = parser.parse_args(new_args)
    opts = vars(parsed_args)
    
    # Set locale for proper sorting
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
        
    opts['I'] = opts.pop('files') or ['-']
    
    # Normalize `k` option
    if not opts.get('k'):
        opts['K'] = True
    else:
        opts['K'] = False
        
    if opts.get('c') and len(opts['I']) > 1:
        sys.stderr.write("sort: -c option is only valid for a single input file\n")
        sys.exit(1)

    _sort_file(opts, [], [])
    
if __name__ == "__main__":
    main()
