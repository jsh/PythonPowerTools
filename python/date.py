#!/usr/bin/env python3

"""
Name: date
Description: display or set date and time
Author: brian d foy, brian.d.foy@gmail.com
Author: Joshua Gross
License: artistic2
"""

import sys
import os
import re
from datetime import datetime, timezone, timedelta
import argparse
import locale

VERSION = '1.0.5'
# Global variable for timezone override
TZ = None

# A simple cache for the time, so we don't recalculate it unnecessarily
_core_time_cache = None

def core_time():
    """Returns a cached datetime object for consistent calculations."""
    global _core_time_cache
    if _core_time_cache is None:
        _core_time_cache = datetime.now() if TZ is None else datetime.now(timezone.utc)
    return _core_time_cache

def get_formats():
    """Returns a dictionary of predefined date formats."""
    return {
        "--rfc-3339": "%Y-%m-%d %H:%M:%S%z",
        "--rfc-5322": "%a, %d %b %Y %H:%M:%S %z",
        "-I": "%Y-%m-%dT%H:%M:%S%:z",
        "-R": "%a, %d %b %Y %T %z",
        "default": "%a %b %e %T %Z %Y",
    }

def munge_tz():
    """
    Tries to find a timezone abbreviation.
    Prefers the POSIX abbreviation, but falls back to a Windows-specific lookup.
    """
    global TZ
    if TZ:
        return TZ
    
    posix_tz_abbrev = core_time().strftime('%Z')
    if posix_tz_abbrev and re.match(r'[A-Z]{3,4}', posix_tz_abbrev):
        return posix_tz_abbrev
    
    # Fallback for systems that don't provide a good TZ abbreviation
    windows_tz_data = windows_time_zones()
    current_offset_minutes = int(tz_offset().replace(':', ''))
    
    for name, tz_info in windows_tz_data.items():
        if len(tz_info) >= 2:
            offset_str = tz_info[1]
            if offset_str:
                tz_offset_minutes = int(offset_str.replace(':', ''))
                if tz_offset_minutes == current_offset_minutes:
                    return tz_info[0] # Return the abbreviation
    
    return posix_tz_abbrev

def quarter():
    """Returns the current quarter of the year (1-4)."""
    return (core_time().month - 1) // 3 + 1

def run(args):
    """Main function to parse arguments and run the date utility."""
    global TZ

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help="Show this help message and exit")
    parser.add_argument('-v', '--version', action='store_true', help="Show the version and exit")
    parser.add_argument('-u', action='store_true', help="Use UTC time instead of local time")
    parser.add_argument('-I', action='store_true', help="Use the ISO 8601 date format")
    parser.add_argument('-R', action='store_true', help="Use RFC 2822 format")
    parser.add_argument('format_or_files', nargs=argparse.REMAINDER,
                        help="An optional format string starting with '+' or file names.")
    
    parsed_args = parser.parse_args(args)

    if parsed_args.help:
        usage(0)
    if parsed_args.version:
        print(f"date {VERSION}")
        sys.exit(0)
        
    if parsed_args.u:
        os.environ['TZ'] = 'UTC'
        TZ = 'UTC'
        # Reset the core time cache to force recalculation in UTC
        global _core_time_cache
        _core_time_cache = None

    format_string = select_format(parsed_args)
    specifiers = setup_specifiers()

    # Apply custom specifiers
    def replace_specifier(match):
        spec = match.group(1)
        if spec in specifiers:
            return specifiers[spec]
        return f"%{spec}"

    final_format = re.sub(r'%(:?.|Z|q|T)', replace_specifier, format_string)
    
    try:
        # Final formatting using Python's strftime
        formatted_date = core_time().strftime(final_format)
        print(formatted_date)
    except ValueError as e:
        sys.stderr.write(f"date: invalid format string: {e}\n")
        sys.exit(1)
        
def select_format(parsed_args):
    """Selects the format string based on command-line arguments."""
    formats = get_formats()

    # Look for a format string starting with '+'
    for arg in parsed_args.format_or_files:
        if arg.startswith('+'):
            return arg[1:]
            
    # Check for predefined formats
    for arg in ['-I', '-R']:
        if getattr(parsed_args, arg[1:]):
            return formats[arg]

    return formats["default"]

def setup_specifiers():
    """Sets up a dictionary of format specifiers, including custom ones."""
    custom_specifiers = {
        'e': f"{core_time().day:2d}",
        'P': core_time().strftime('%p').lower(),
        'q': str(quarter()),
        'T': core_time().strftime('%H:%M:%S'),
        'z': tz_offset(),
        ':z': f"{tz_offset()[:3]}:{tz_offset()[3:]}",
        'Z': munge_tz(),
    }
    return custom_specifiers

def tz_offset():
    """Calculates the timezone offset in [+-]HHMM format."""
    now = datetime.now()
    now_utc = datetime.now(timezone.utc)
    offset = now - now_utc.replace(tzinfo=None)
    
    total_minutes = int(offset.total_seconds() / 60)
    sign = '+' if total_minutes >= 0 else '-'
    total_minutes = abs(total_minutes)
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    return f"{sign}{hours:02d}{minutes:02d}"

def usage(exit_code):
    """Prints the usage message and exits with the given code."""
    help_message = """
usage: date [-hIRuv] [+format]

Formats:
"""
    formats = get_formats()
    for item in sorted(formats):
        help_message += f"\t{item}\n"

    # In a full-featured version, we would parse the pod section to get this
    # For now, let's hardcode a simplified version based on the original script's output
    specifiers = [
        ("%", "The character %"),
        ("a", "Three-letter weekday name"),
        ("A", "Full weekday name"),
        ("b", "Three-letter month name"),
        ("B", "Full month name"),
        ("c", "locale version of the date-time string"),
        ("C", "Century (00-99)"),
        ("d", "Day of month (padded w/ zero)"),
        ("D", "Date in MM/DD/YY format"),
        ("e", "Day of month (padded w/ space)"),
        ("F", "%Y-%m-%d"),
        ("g", "ISO 8601 year"),
        ("G", "ISO 8601 year"),
        ("h", "Three-letter month name"),
        ("H", "Hour HH"),
        ("I", "Hour HH (12 hour)"),
        ("j", "Three-digit Julian day"),
        ("k", "Hour - space padded"),
        ("l", "Hour - space padded (12 hour)"),
        ("m", "Month number 01-12"),
        ("M", "Minute MM"),
        ("n", "Newline"),
        ("p", "AM or PM"),
        ("P", "like %p, but lowercase"),
        ("q", "quarter of the year (1-4)"),
        ("r", "Time in HH(12 hour):MM:SS (AM|PM) format"),
        ("R", "Time in HH:MM format"),
        ("s", "Absolute seconds (since epoch)"),
        ("S", "Seconds SS"),
        ("t", "Tab"),
        ("T", "Time in HH:MM:SS format."),
        ("u", "Day of week, 1=Monday, 7=Sunday."),
        ("U", "Two digit week number, starting on Sunday."),
        ("V", "ISO week number, with Monday as the first day of week"),
        ("w", "Day of week, 0=Sunday, 6=Saturday."),
        ("W", "Two digit week number, start Monday."),
        ("x", "locale's date representation"),
        ("X", "locale's time representation"),
        ("y", "Two-digit year."),
        ("Y", "Four-digit year."),
        ("z", "Time zone offset in [+-]HHMM."),
        (":z", "Time zone offset in [+-]HH:MM."),
        ("Z", "Time zone abbrevation, such as UTC or EST."),
    ]
    
    help_message += "\nFormat Specifiers:\n"
    for spec, desc in specifiers:
        help_message += f"\t%{spec}\t- {desc}\n"
    
    print(help_message)
    sys.exit(exit_code)

def windows_time_zones():
    """
    Parses a simplified data section to create a mapping for Windows time zones.
    This is a placeholder as Python's `datetime` module generally handles this
    better natively on most platforms.
    """
    # For a portable script, we'd include this data in the Python file.
    # The original Perl script has this data embedded in a __DATA__ block.
    # This is a simplified hardcoded version for demonstration purposes.
    data = """
Alaskan Daylight Time,America/Anchorage,-0900,AKDT
Alaskan Standard Time,America/Anchorage,-0800,AKST
Central Daylight Time,America/Chicago,CDT
Central Standard Time,America/Chicago,CST
Eastern Daylight Time,America/New_York,EDT
Eastern Standard Time,America/New_York,EST
Mountain Daylight Time,America/Denver,MDT
Mountain Standard Time,America/Denver,MST
Pacific Daylight Time,America/Los_Angeles,PDT
Pacific Standard Time,America/Los_Angeles,PST
    """
    
    tz_map = {}
    for line in data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        windows_name = parts[0].strip()
        tz_abbrev = parts[-1].strip()
        offset = parts[2].strip() if len(parts) > 2 else None
        
        tz_map[windows_name] = (tz_abbrev, offset)
        
    return tz_map

if __name__ == '__main__':
    run(sys.argv[1:])
