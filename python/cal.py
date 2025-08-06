#!/usr/bin/env python3
"""
Name: cal
Description: displays a calendar and the date of Easter
Author: Michael E. Schechter, mschechter@earthlink.net (Original Perl Author)
License: gpl
"""

import sys
import argparse
from datetime import date
import math

# --- Core Date Calculation Functions (ported from original) ---

def is_julian(year: int, month: int) -> bool:
    """Checks if a date falls before the Gregorian reform of Sep 1752."""
    return year < 1752 or (year == 1752 and month < 9) or \
           (year == 1752 and month == 9 and date.today().day < 14)

def is_leap_year(year: int) -> bool:
    """Determines if a year is a leap year, respecting Julian/Gregorian rules."""
    if is_julian(year, 12):
        return year % 4 == 0
    else:
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def days_in_month(year: int, month: int) -> int:
    """Returns the number of days in a given month for a given year."""
    month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and is_leap_year(year):
        return 29
    # The Gregorian reform skipped 11 days in September 1752.
    if year == 1752 and month == 9:
        return 19
    return month_days[month]

def day_of_week(year: int, month: int, day: int) -> int:
    """Calculates the day of the week (0=Sun, 1=Mon...). Zeller's congruence."""
    a = math.floor((14 - month) / 12)
    y = year - a
    m = month + (12 * a) - 2
    if is_julian(year, month):
        return (5 + day + y + math.floor(y/4) + math.floor(31*m/12)) % 7
    else:
        return (day + y + math.floor(y/4) - math.floor(y/100) + math.floor(y/400) + math.floor(31*m/12)) % 7

def day_of_year(year: int, month: int, day: int) -> int:
    """Calculates the Julian day number (day of the year)."""
    days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    leap = 1 if is_leap_year(year) and month > 2 else 0
    doy = days[month - 1] + day + leap
    # Account for the 11 skipped days in 1752
    if year == 1752 and (month > 9 or (month == 9 and day >= 14)):
        doy -= 11
    return doy

# --- Formatting and Display Functions ---

def format_month(year: int, month: int, julian_mode: bool, show_year_title: bool) -> list:
    """Generates a list of strings representing a single formatted month."""
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    col_width = 4 if julian_mode else 3
    box_width = col_width * 7 - 1
    
    # --- Title ---
    title = month_names[month]
    if show_year_title:
        title += f" {year}"
    lines = [title.center(box_width).rstrip()]

    # --- Day Header ---
    day_headers = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
    header_line = "".join(f"{day:<{col_width}}" for day in day_headers)
    lines.append(header_line.rstrip())

    # --- Day Grid ---
    first_weekday = day_of_week(year, month, 1)
    num_days = days_in_month(year, month)
    
    grid = [''] * first_weekday
    for d in range(1, num_days + 1):
        day_val = day_of_year(year, month, d) if julian_mode else d
        # Handle the jump from Sep 2 to Sep 14 in 1752
        if year == 1752 and month == 9 and d == 3:
            grid.extend([''] * 11)
        grid.append(str(day_val))
        
    # Format grid into lines
    for i in range(0, len(grid), 7):
        week = grid[i:i+7]
        week_line = "".join(f"{day:>{col_width-1}} " for day in week)
        lines.append(week_line.rstrip())
        
    return lines

def display_year(year: int, julian_mode: bool):
    """Formats and prints an entire year in a grid."""
    print(str(year).center(62))
    months_data = [format_month(year, m, julian_mode, False) for m in range(1, 13)]
    
    # Print the year row by row, with 3 months per row
    for m_row in range(0, 12, 3):
        print()
        # Find the max number of lines needed for this row of months
        max_lines = max(len(months_data[m_row+i]) for i in range(3))
        
        for line_idx in range(max_lines):
            line_parts = []
            for month_idx in range(m_row, m_row + 3):
                # Get the line from each month, or an empty string if it's shorter
                line = months_data[month_idx][line_idx] if line_idx < len(months_data[month_idx]) else ""
                line_parts.append(f"{line:<20}")
            print("  ".join(line_parts).rstrip())

def main():
    """Parses arguments and displays the appropriate calendar."""
    parser = argparse.ArgumentParser(
        description="Displays a calendar.",
        usage="%(prog)s [-jy] [[month] year]"
    )
    parser.add_argument('-j', '--julian', action='store_true', help='Display Julian days (day of year).')
    parser.add_argument('-y', '--year', action='store_true', help='Display calendar for the entire year.')
    parser.add_argument('args', nargs='*', help='Month and/or year.')

    parsed_args = parser.parse_args()

    # --- Determine what to display ---
    year, month = None, None
    today = date.today()

    if len(parsed_args.args) == 0:
        if parsed_args.year:
            year, month = today.year, None
        else:
            year, month = today.year, today.month
    elif len(parsed_args.args) == 1:
        year = int(parsed_args.args[0])
    elif len(parsed_args.args) == 2:
        if parsed_args.year:
            parser.error("cannot use -y with both month and year")
        month = int(parsed_args.args[0])
        year = int(parsed_args.args[1])
    else:
        parser.error("too many arguments")

    # Validate inputs
    if not 1 <= year <= 9999:
        parser.error("invalid year")
    if month and not 1 <= month <= 12:
        parser.error("invalid month")
        
    # --- Print the result ---
    if month:
        lines = format_month(year, month, parsed_args.julian, True)
        print("\n".join(lines))
    else:
        display_year(year, parsed_args.julian)

if __name__ == "__main__":
    main()
