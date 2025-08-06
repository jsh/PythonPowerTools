#!/usr/bin/env python3

"""
Name: pom
Description: display the phase of the moon
Author: Rocco Caputo, troc@netrus.net
License: perl
"""

import sys
import os
import re
import time
from math import sin, cos, tan, atan, sqrt, floor, fmod, pi
from datetime import datetime
import argparse

# Constants
EX_SUCCESS = 0
EX_FAILURE = 1
LINES_DEFAULT = 25
COLS_DEFAULT = 80
ASPECT_RATIO = 5 / 7

# Astronomical constants
EPOCH = 2444238.5  # 1980 January 0.0
ELONGE = 278.833540  # ecliptic longitude of the Sun at EPOCH
ELONGP = 282.596403  # ecliptic longitude of the Sun at perigee
ECCENT = 0.01671542  # Earth's orbit's eccentricity
MMLONG = 64.975464  # moon's mean longitude at EPOCH
MMLONGP = 349.383063  # mean longitude of the perigee at EPOCH

# Helper functions
def usage():
    """Prints usage message and exits."""
    program_name = os.path.basename(sys.argv[0])
    sys.stderr.write(f"usage: {program_name} [-d] [-e] [[[[[[cc]yy]mm]dd]HH]]\n")
    sys.exit(EX_FAILURE)

def checknum(n, label='number'):
    """Checks if a string is a valid positive integer."""
    if not isinstance(n, str) or not n.isdigit():
        sys.stderr.write(f"Bad {label}: '{n}'\n")
        sys.exit(EX_FAILURE)
    return int(n)

def fixangle(a):
    """Normalizes an angle to be within 0 and 360 degrees."""
    return fmod(a - (360 * floor(a / 360)), 360)

def deg2rad(a):
    """Converts degrees to radians."""
    return a * pi / 180

def rad2deg(a):
    """Converts radians to degrees."""
    return a * 180 / pi

def mdy_to_julian(month, day, year):
    """Converts a Gregorian date to a Julian day number."""
    if month < 3:
        month += 12
        year -= 1
    
    if (year < 1582) or (year == 1582 and month < 10) or (year == 1582 and month == 10 and day < 15):
        b = 0
    else:
        a = floor(year / 100)
        b = 2 - a + floor(a / 4)
    
    if year >= 0:
        c = floor(365.25 * year) - 694025
    else:
        c = floor(365.25 * year - 0.75) - 694025
    
    d = floor(30.6001 * (month + 1))

    return b + c + d + day + 2415020

def kepler(m, ecc):
    """
    Solves Kepler's equation to find the eccentric anomaly.
    
    This function iteratively solves the equation E - e*sin(E) = M,
    where E is the eccentric anomaly, e is the eccentricity, and M
    is the mean anomaly. It's used here to calculate the position of
    the Earth in its orbit around the Sun.
    """
    EPSILON = 1e-6
    e_val = m = deg2rad(m)
    
    while True:
        delta = e_val - ecc * sin(e_val) - m
        e_val -= delta / (1 - ecc * cos(e_val))
        if abs(delta) <= EPSILON:
            break
    
    return e_val

def calc_phase(hour, month, day, year):
    """
    Calculates the phase of the moon as a fraction (0.0 to 0.99).
    0.0 is New Moon, 0.25 is First Quarter, 0.5 is Full Moon, 0.75 is Last Quarter.
    """
    pdate = mdy_to_julian(month, day, year) + hour / 24
    
    # Sun's position
    day_count = pdate - EPOCH
    sun_mean_anomaly = fixangle((360 / 365.2422) * day_count)
    sun_epoch_coords = fixangle(sun_mean_anomaly + ELONGE - ELONGP)
    sun_ecc = kepler(sun_epoch_coords, ECCENT)
    sun_ecc = sqrt((1 + ECCENT) / (1 - ECCENT)) * tan(sun_ecc / 2)
    sun_ecc = 2 * rad2deg(atan(sun_ecc))
    sun_lambda = fixangle(sun_ecc + ELONGP)

    # Moon's position
    moon_mean_longitude = fixangle(13.1763966 * day_count + MMLONG)
    moon_mean_anomaly = fixangle(moon_mean_longitude - 0.1114041 * day_count - MMLONGP)
    
    moon_evection = 1.2739 * sin(deg2rad(2 * moon_mean_longitude - sun_lambda) - moon_mean_anomaly)
    moon_annual_equation = 0.1858 * sin(deg2rad(sun_epoch_coords))
    moon_correction_1 = 0.37 * sin(deg2rad(sun_epoch_coords))
    moon_corrected_anomaly = moon_mean_anomaly + moon_evection - moon_annual_equation - moon_correction_1
    moon_correction_for_center = 6.2886 * sin(deg2rad(moon_corrected_anomaly))
    moon_correction_2 = 0.214 * sin(deg2rad(2 * moon_corrected_anomaly))
    moon_corrected_longitude = moon_mean_longitude + moon_evection + moon_correction_for_center - moon_annual_equation - moon_correction_2
    moon_variation = 0.6583 * sin(deg2rad(2 * (moon_corrected_longitude - sun_lambda)))
    moon_true_longitude = moon_corrected_longitude + moon_variation
    
    # Age of moon, in degrees and as a fraction
    moon_age = moon_true_longitude - sun_lambda
    
    return fixangle(moon_age) / 360

def display_moon(month, day, year, hour, enhanced_behavior):
    """
    Displays the moon phase based on the given date and options.
    """
    real_phase = calc_phase(hour, month, day, year)
    
    # Convert phase to percentage and name
    rotated_scaled_phase = (real_phase * 360 - 180) / 180
    phase_percent = int(abs(rotated_scaled_phase) * 100)
    
    phase_name = ""
    if phase_percent < 2:
        phase_name = 'New'
    elif phase_percent > 99:
        phase_name = 'Full'
    elif phase_percent == 50:
        phase_name = 'First Quarter' if real_phase < 0.5 else 'Last Quarter'
    elif phase_percent < 50:
        phase_name = 'Waxing Crescent' if real_phase < 0.5 else 'Waning Crescent'
    else:
        phase_name = 'Waxing Gibbous' if real_phase < 0.5 else 'Waning Gibbous'

    if enhanced_behavior:
        # Get terminal dimensions
        terminal_width = (int(os.environ.get('COLS', os.environ.get('COLUMNS', COLS_DEFAULT
