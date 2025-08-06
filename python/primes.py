#!/usr/bin/env python3
"""
Name: primes
Description: generate primes
Author: Jonathan Feinberg, Benjamin Tilly (Original Perl Authors)
License: perl
"""

import sys
import argparse
import math

def segmented_sieve(limit: int):
    """
    A generator that yields prime numbers up to a given limit using a
    segmented Sieve of Eratosthenes. This is memory-efficient for large limits.
    """
    if limit < 2:
        return

    # 1. Generate base primes up to sqrt(limit) using a simple sieve.
    sqrt_limit = int(math.sqrt(limit))
    sieve = [True] * (sqrt_limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.sqrt(sqrt_limit)) + 1):
        if sieve[i]:
            for multiple in range(i * i, sqrt_limit + 1, i):
                sieve[multiple] = False
    
    base_primes = [i for i, is_prime in enumerate(sieve) if is_prime]
    
    # Yield the base primes themselves first.
    for p in base_primes:
        yield p

    # 2. Sieve the remaining numbers in segments.
    segment_size = 10**5  # Process numbers in chunks of 100,000
    low = sqrt_limit + 1
    
    while low < limit:
        high = min(low + segment_size, limit)
        
        # Create a boolean list for the current segment.
        segment_sieve = [True] * (high - low)
        
        # Mark off multiples of the base primes.
        for p in base_primes:
            # Find the first multiple of p that is >= low
            start = math.floor(low / p) * p
            if start < low:
                start += p
            
            # Mark all multiples of p within the current segment.
            for i in range(start, high, p):
                segment_sieve[i - low] = False
                
        # Yield the numbers from the segment that are still marked as prime.
        for i, is_prime in enumerate(segment_sieve):
            if is_prime:
                yield low + i
                
        low += segment_size

def main():
    """Parses arguments and prints primes in the specified range."""
    # The maximum value, as in the original script.
    MAX_INT = 2**32

    parser = argparse.ArgumentParser(
        description="Generate prime numbers in a given range.",
        usage="%(prog)s [start [stop]]"
    )
    parser.add_argument('start', nargs='?', help="The starting number (inclusive).")
    parser.add_argument('stop', nargs='?', type=int, default=MAX_INT,
                        help=f"The ending number (exclusive). Default is {MAX_INT}.")

    args = parser.parse_args()

    # --- Argument Handling and Validation ---
    start_val = args.start
    if start_val is None:
        try:
            print("Enter starting number: ", end='', file=sys.stderr, flush=True)
            start_val = sys.stdin.readline()
        except (IOError, KeyboardInterrupt):
            sys.exit(1)
    
    try:
        # Clean and convert start value
        start_val = int(str(start_val).strip().lstrip('+'))
    except (ValueError, TypeError):
        print(f"{sys.argv[0]}: {args.start}: illegal numeric format", file=sys.stderr)
        sys.exit(1)

    end_val = args.stop

    if not (0 <= start_val < MAX_INT and start_val < end_val <= MAX_INT):
        print(f"{sys.argv[0]}: Invalid range. Ensure 0 <= start < stop <= {MAX_INT}", file=sys.stderr)
        sys.exit(1)

    # --- Prime Generation and Output ---
    try:
        # Create the generator to produce primes up to the end value.
        prime_generator = segmented_sieve(end_val)
        
        for prime in prime_generator:
            # Only print primes that are within the requested start/end range.
            if prime >= start_val:
                print(prime)
    except (IOError, KeyboardInterrupt):
        # Handle broken pipes (e.g., `| head`) and Ctrl+C gracefully.
        sys.stderr.close() # Silence final error message on broken pipe
        sys.exit(1)

if __name__ == "__main__":
    main()
