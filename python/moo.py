#!/usr/bin/env python3
"""
Name: moo
Description: play a game of MOO (Bulls and Cows)
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import random
import argparse

def generate_secret(size: int) -> list:
    """
    Generates a secret number of a given size with unique digits.
    Returns the digits as a list of strings.
    """
    # random.sample is perfect for choosing unique items from a sequence.
    population = '0123456789'
    return random.sample(population, k=size)

def play_game(size: int):
    """
    Runs a single round of the MOO (Bulls and Cows) game.
    """
    secret_digits = generate_secret(size)
    secret_set = set(secret_digits)
    attempts = 0
    print("\nNew game started.")

    while True:
        # --- Get Player Guess ---
        try:
            prompt = "Your guess? (or 'q' to quit) "
            guess_str = input(prompt)
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+D or Ctrl+C gracefully
            print("\nExiting.")
            sys.exit(0)

        if guess_str.lower() == 'q':
            print("Thanks for playing!")
            sys.exit(0)
            
        # --- Validate Guess ---
        has_dupes = len(set(guess_str)) != len(guess_str)
        if (not guess_str.isdigit() or 
                len(guess_str) != size or 
                has_dupes):
            print("Bad guess. Please enter a {}-digit number with unique digits.".format(size))
            continue
            
        attempts += 1
        guess_digits = list(guess_str)
        
        # --- Calculate Bulls and Cows ---
        # Bulls are correct digits in the correct position.
        bulls = sum(1 for i in range(size) if guess_digits[i] == secret_digits[i])
        
        # Cows are correct digits in the wrong position.
        # This is calculated by finding all correct digits (the intersection of the sets)
        # and subtracting the bulls.
        correct_digits = len(set(guess_digits) & secret_set)
        cows = correct_digits - bulls
        
        print(f"Bulls = {bulls}\tCows = {cows}")

        # --- Check for Win Condition ---
        if bulls == size:
            print(f"You win! 🥳 It took you {attempts} attempts.")
            break # Exit the inner game loop to start a new game

def main():
    """
    Parses arguments and controls the "new game" loop.
    """
    parser = argparse.ArgumentParser(
        description="Play a game of MOO (Bulls and Cows).",
        usage="%(prog)s [size]"
    )
    parser.add_argument(
        'size',
        nargs='?',
        type=int,
        default=4,
        help='The number of digits in the secret number (1-10, default: 4).'
    )
    args = parser.parse_args()

    if not 1 <= args.size <= 10:
        parser.error("secret size must be within the range 1-10")

    print("--- Welcome to MOO! ---")
    
    # This outer loop allows for a new game to start after one is won.
    while True:
        play_game(args.size)

if __name__ == "__main__":
    main()
