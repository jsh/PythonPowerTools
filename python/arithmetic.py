#!/usr/bin/env python3
"""
Name: arithmetic
Description: improve your arithmetic skills
Author: Abigail, perlpowertools@abigail.be (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import random
import time
import signal

# --- Global state for score and timing ---
# This is necessary so the signal handler can access it.
start_time = 0
questions_asked = 0
correct_answers = 0

def generate_problem(operator: str, num_range: int):
    """
    Generates the operands and answer for a new arithmetic problem.
    """
    # For division, the right operand cannot be zero.
    right = random.randrange(1, num_range + 1) if operator == '/' else random.randrange(num_range + 1)
    
    # For subtraction and division, we generate the answer first to ensure
    # the result and operands stay within the desired range and division is integral.
    if operator in ('-', '/'):
        answer = random.randrange(num_range + 1)
        if operator == '-':
            left = answer + right
        else: # operator == '/'
            left = answer * right
    else: # For addition and multiplication
        left = random.randrange(num_range + 1)
        if operator == '+':
            answer = left + right
        else: # operator == 'x'
            answer = left * right
            
    return left, right, answer

def report(signum=None, frame=None):
    """
    Prints the final score and time report, then exits.
    This function also acts as a signal handler for Ctrl+C.
    """
    elapsed = int(time.time() - start_time)
    
    # Format the elapsed time into a human-readable string.
    parts = []
    if elapsed >= 3600:
        h = elapsed // 3600
        parts.append(f"{h} hour{'s' if h > 1 else ''}")
        elapsed %= 3600
    if elapsed >= 60:
        m = elapsed // 60
        parts.append(f"{m} minute{'s' if m > 1 else ''}")
        elapsed %= 60
    if elapsed > 0:
        parts.append(f"{elapsed} second{'s' if elapsed > 1 else ''}")

    time_str = ", ".join(parts) or "no time at all!"
    
    print(f"\nYou had {correct_answers} answers correct, out of {questions_asked}. "
          f"It took you {time_str}.")
    sys.exit(0)

def main():
    """Parses arguments and runs the arithmetic game loop."""
    global start_time, questions_asked, correct_answers

    parser = argparse.ArgumentParser(
        description="A simple arithmetic practice game.",
        usage="%(prog)s [-o OPERATORS] [-r RANGE]"
    )
    parser.add_argument(
        '-o', '--operators',
        default='+',
        help='A string of operators to use (+-x/). Default is "+".'
    )
    parser.add_argument(
        '-r', '--range',
        type=int,
        default=10,
        help='The upper bound for numbers in the problems (default: 10).'
    )
    args = parser.parse_args()

    # --- Validate arguments ---
    valid_ops = "+-x/"
    operators = "".join(c for c in args.operators if c in valid_ops)
    if not operators:
        parser.error(f"invalid operators specified. Choose from '{valid_ops}'.")
    
    if args.range == 0 and '/' in operators:
        operators = operators.replace('/', '') # Remove division
        if not operators:
            parser.error("division by 0 is not allowed and no other operators were given.")
    
    # --- Game Setup ---
    TOTAL_QUESTIONS = 20
    CHANCE_TO_REMEMBER = 20 # 20% chance
    remembered_problems = {op: [] for op in valid_ops}

    # Set the signal handler for Ctrl+C to call our report function.
    signal.signal(signal.SIGINT, report)
    
    start_time = time.time()
    
    # --- Main Game Loop ---
    while questions_asked < TOTAL_QUESTIONS:
        operator = random.choice(operators)
        
        # Decide whether to ask a new question or a previously failed one.
        if remembered_problems[operator] and random.randrange(100) < CHANCE_TO_REMEMBER:
            left, right, answer = random.choice(remembered_problems[operator])
        else:
            left, right, answer = generate_problem(operator, args.range)
            
        # Get a valid numeric answer from the user.
        guess = None
        while guess is None:
            try:
                prompt = f"{left} {operator} {right} = "
                raw_input = input(prompt)
                guess = int(raw_input.strip())
            except (EOFError, KeyboardInterrupt):
                report() # Exit gracefully on Ctrl+D or Ctrl+C
            except (ValueError):
                print("Please type a number.")

        questions_asked += 1
        
        # Check the answer.
        if guess == answer:
            print("Right!")
            correct_answers += 1
            # If we got it right, remove it from the list of problems to remember.
            remembered_problems[operator] = [
                p for p in remembered_problems[operator] if p != (left, right, answer)
            ]
        else:
            print("What?")
            # If we got it wrong, add it to the list to be asked again later.
            if (left, right, answer) not in remembered_problems[operator]:
                remembered_problems[operator].append((left, right, answer))

    # After the loop finishes, print the final report.
    report()

if __name__ == "__main__":
    main()
