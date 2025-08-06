#!/usr/bin/env python3
"""
Name: hangman
Description: the game hangman
Author: Michael E. Schechter, mschechter@earthlink.net (Original Perl Author)
License: gpl
"""

import random
import sys

# The name of the file containing the words for the game.
WORDLIST_FILENAME = "wordlist.txt"

# A list of strings representing the hangman's gallows at each stage.
HANGMAN_PICS = [
    """
     +--+
         |
         |
         |
         |
    ----+""",
    """
     +--+
     O   |
         |
         |
         |
    ----+""",
    """
     +--+
     O   |
     |   |
         |
         |
    ----+""",
    """
     +--+
     O   |
    /|   |
         |
         |
    ----+""",
    """
     +--+
     O   |
    /|\\  |
         |
         |
    ----+""",
    """
     +--+
     O   |
    /|\\  |
    /    |
         |
    ----+""",
    """
     +--+
     O   |
    /|\\  |
    / \\  |
         |
    ----+"""
]

def get_random_word(filename: str) -> str:
    """
    Reads a wordlist file and returns a single, random word from it.
    """
    try:
        with open(filename, 'r') as f:
            # Read all lines, strip whitespace, and filter out empty lines.
            words = [line.strip().lower() for line in f if line.strip()]
        if not words:
            print(f"Error: Word list '{filename}' is empty.", file=sys.stderr)
            sys.exit(1)
        # Return a random choice from the list of words.
        return random.choice(words)
    except FileNotFoundError:
        print(f"Error: Word list '{filename}' not found.", file=sys.stderr)
        print("Please create it with one word per line in the same directory.", file=sys.stderr)
        sys.exit(1)

def display_board(wrong_guesses: int, display_word: list, guessed_letters: set):
    """
    Prints the current state of the game board, including the gallows,
    the word, and the letters that have been guessed.
    """
    print(HANGMAN_PICS[wrong_guesses])
    print("\nWord: ", " ".join(display_word))
    
    if guessed_letters:
        print("Letters Chosen: ", " ".join(sorted(list(guessed_letters))))

def play_game():
    """
    Runs a single round of the Hangman game.
    """
    secret_word = get_random_word(WORDLIST_FILENAME)
    unique_letters_in_word = set(secret_word)
    display_word = ['_'] * len(secret_word)
    guessed_letters = set()
    wrong_guesses = 0

    while wrong_guesses < 6 and '_' in display_word:
        display_board(wrong_guesses, display_word, guessed_letters)
        
        try:
            guess = input("\nEnter a letter: ").lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\nThanks for playing!")
            sys.exit(0)

        # --- Input Validation ---
        if len(guess) != 1 or not guess.isalpha():
            print("\nPLEASE ENTER A SINGLE LETTER FROM A TO Z.")
            continue
        
        if guess in guessed_letters:
            print("\nYOU HAVE ALREADY GUESSED THAT LETTER.")
            continue
            
        guessed_letters.add(guess)

        # --- Process Guess ---
        if guess in unique_letters_in_word:
            # Correct guess: reveal the letter(s) in the display word.
            for i, letter in enumerate(secret_word):
                if letter == guess:
                    display_word[i] = letter
        else:
            # Incorrect guess.
            wrong_guesses += 1
            
    # --- End of Game ---
    display_board(wrong_guesses, display_word, guessed_letters)
    if '_' not in display_word:
        print("\nYOU WIN! 🎉")
    else:
        print(f'\nYOU LOSE! 😢\nThe word was "{secret_word}".')

def main():
    """
    Main function to control the "Play Again?" loop.
    """
    while True:
        play_game()
        
        try:
            play_again = input("\nPlay Again (y/N)? ").lower()
        except (EOFError, KeyboardInterrupt):
            break # Exit loop on Ctrl+D or Ctrl+C
            
        if not play_again.startswith('y'):
            break
            
    print("\nTHANKS FOR PLAYING!")

if __name__ == "__main__":
    main()
