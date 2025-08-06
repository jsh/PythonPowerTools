#!/usr/bin/env python3
"""
Name: addbib
Description: create or extend a bibliographic database
Author: Jeffrey S. Haemer (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import subprocess
import re

# The default list of prompts and their corresponding 'refer' field codes.
DEFAULT_PROMPTS = [
    ("Author name:", "%A"),
    ("Title:",       "%T"),
    ("Journal:",     "%J"),
    ("Volume:",      "%V"),
    ("Pages:",       "%P"),
    ("Publisher:",   "%I"),
    ("City:",        "%C"),
    ("Date:",        "%D"),
    ("Other:",       "%O"),
    ("Keywords:",    "%K"),
]

INSTRUCTIONS = """
    Addbib will prompt you for various bibliographic fields.
    - If you don't need a particular field, just press ENTER.
    - To go back to the previous field, enter a single minus sign (-).
      (This is the best way to input multiple authors).
    - To continue a field onto a new line, end the line with a backslash (\\).
    - To quit, type 'q' or 'n' when asked if you want to continue.
    - To edit the database, type an editor command (e.g., 'vi', 'emacs')
      at the 'Continue?' prompt.
"""

def load_prompts_from_file(filepath: str) -> list:
    """Loads a custom set of prompts from a user-provided file."""
    prompts = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                # The format is "Prompt Text\t%X"
                match = re.match(r'^\s*([^\t]+)\t(%\w)', line)
                if match:
                    prompts.append(match.groups())
    except IOError as e:
        print(f"Error: can't read prompt file '{filepath}': {e.strerror}", file=sys.stderr)
        sys.exit(1)
    return prompts

def main():
    """Parses arguments and runs the interactive session."""
    parser = argparse.ArgumentParser(
        description="Create or extend a bibliographic database.",
        usage="%(prog)s [-a] [-p promptfile] database"
    )
    parser.add_argument(
        '-a', '--no-abstract',
        action='store_true',
        help='Suppress prompting for an abstract.'
    )
    parser.add_argument(
        '-p', '--prompt-file',
        help='Specify a file containing alternate prompts.'
    )
    parser.add_argument('database', help='The database file to create or append to.')
    
    args = parser.parse_args()

    prompts = load_prompts_from_file(args.prompt_file) if args.prompt_file else DEFAULT_PROMPTS
    
    # --- Instructions ---
    try:
        show_instructions = input("Instructions? (y/N) ")
        if show_instructions.lower().startswith('y'):
            print(INSTRUCTIONS)
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        sys.exit(0)

    # --- Main Loop ---
    db_file = None
    try:
        db_file = open(args.database, 'a')
        
        while True: # This loop is for each new entry
            db_file.write("\n") # Start new entry with a blank line
            
            i = 0
            while i < len(prompts): # This loop is for each field
                prompt_text, field_code = prompts[i]
                
                try:
                    user_input = input(f"{prompt_text} ")
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting.")
                    return # This will trigger the finally block

                if not user_input: # Empty line, skip field
                    i += 1
                    continue
                if user_input.strip() == '-': # Go back one field
                    i = max(0, i - 1)
                    continue
                
                # Write the field code and the first line of input.
                db_file.write(f"{field_code}\t{user_input}\n")

                # Handle multi-line input for a field.
                while user_input.endswith('\\'):
                    try:
                        user_input = input("> ")
                        db_file.write(f"{user_input}\n")
                    except (EOFError, KeyboardInterrupt):
                        # Stop multi-line input and move to abstract/continue
                        break
                i += 1
            
            # --- Abstract ---
            if not args.no_abstract:
                print("Abstract: (end with Ctrl+D)")
                try:
                    abstract_first_line = sys.stdin.readline()
                    if abstract_first_line:
                        db_file.write(f"%X\t{abstract_first_line}")
                        for line in sys.stdin:
                            db_file.write(line)
                except (EOFError, KeyboardInterrupt):
                    pass # Ctrl+D was pressed, this is expected.
            
            # --- Continue? ---
            while True: # Loop until we get a valid continue/quit/edit command
                try:
                    continue_answer = input("\nContinue? (y/N) ")
                except (EOFError, KeyboardInterrupt):
                    continue_answer = 'n' # Treat Ctrl+D/C as "no"

                if continue_answer.lower().startswith(('n', 'q')):
                    return # Exit the main function
                
                editor_match = re.match(r'^\s*(vi|vim|emacs|nano|edit|ex)\s*', continue_answer)
                if editor_match:
                    editor = editor_match.group(1)
                    print(f"Temporarily closing database to run '{editor}'...")
                    db_file.close()
                    try:
                        # Run the editor as a subprocess
                        subprocess.run([editor, args.database])
                    except FileNotFoundError:
                        print(f"Error: Command '{editor}' not found.", file=sys.stderr)
                    except Exception as e:
                        print(f"Error running editor: {e}", file=sys.stderr)

                    db_file = open(args.database, 'a') # Re-open the file
                    continue # Ask "Continue?" again
                    
                break # Default is 'y', so break to the outer loop for a new entry

    finally:
        if db_file and not db_file.closed:
            db_file.close()

if __name__ == "__main__":
    main()
