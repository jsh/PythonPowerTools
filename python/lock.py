#!/usr/bin/env python3
"""
Name: lock
Description: reserves a terminal
Author: Aron Atkins, atkins@gweep.net (Original Perl Author)
License: perl
"""

import sys
import os
import argparse
import time
import signal
import getpass
import socket

# These modules are specific to Unix-like systems.
try:
    import termios
    import tty
    import pwd
    import crypt
except ImportError:
    print("Error: This script requires a Unix-like environment and is not compatible with Windows.", file=sys.stderr)
    sys.exit(1)

# --- Terminal Control Functions ---
original_termios_settings = None

def disable_echo(fd):
    """Disables character echoing on the terminal."""
    global original_termios_settings
    if not os.isatty(fd):
        return
    original_termios_settings = termios.tcgetattr(fd)
    new = original_termios_settings[:]
    new[3] &= ~termios.ECHO  # lflags
    termios.tcsetattr(fd, termios.TCSADRAIN, new)

def enable_echo(fd):
    """Re-enables character echoing on the terminal."""
    global original_termios_settings
    if not os.isatty(fd) or original_termios_settings is None:
        return
    termios.tcsetattr(fd, termios.TCSADRAIN, original_termios_settings)

# --- Signal Handler ---
def signal_handler(signum, frame):
    """Handles signals like Ctrl+C to prevent easy termination."""
    if signum == signal.SIGALRM:
        print("\nlock: timeout", flush=True)
        enable_echo(sys.stdin.fileno())
        sys.exit(0)
    else:
        # For other signals, re-prompt for the key.
        print("\nlock: type in the unlock key.", end='', flush=True)
        remaining_time = signal.alarm(0) # Get remaining time
        if remaining_time > 0:
            mins, secs = divmod(remaining_time, 60)
            print(f" timeout in {mins}:{secs:02d} minutes", end='', flush=True)
            signal.alarm(remaining_time) # Reset the alarm
        print(flush=True)

def main():
    """Parses arguments and runs the terminal locking logic."""
    parser = argparse.ArgumentParser(
        description="Reserves a terminal by locking it.",
        usage="%(prog)s [-n] [-p] [-t timeout]"
    )
    parser.add_argument('-n', '--no-timeout', action='store_true', help="Lock forever, no timeout.")
    parser.add_argument('-p', '--password', action='store_true', help="Use the user's login password as the key.")
    parser.add_argument('-t', '--timeout', type=int, default=15, help="Set timeout in minutes (default: 15).")
    
    args = parser.parse_args()

    # --- 1. Get the Key/Password ---
    key = None
    if args.password:
        try:
            username = getpass.getuser()
            # Get the encrypted password hash from the system.
            key = pwd.getpwnam(username).pw_passwd
        except (KeyError, Exception) as e:
            print(f"Error: Could not retrieve password for user: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            # Use getpass for a safe, no-echo prompt.
            key1 = getpass.getpass("Key: ")
            key2 = getpass.getpass("Again: ")
            if key1 != key2:
                print("lock: passwords didn't match.", file=sys.stderr)
                sys.exit(1)
            key = key1
        except (EOFError, KeyboardInterrupt):
            print("\nLock aborted.")
            sys.exit(1)

    # --- 2. Print Lock Message and Set Timers ---
    tty_name = os.ttyname(sys.stdin.fileno())
    hostname = socket.gethostname()
    current_time = time.strftime('%c')

    print(f"lock: {tty_name} on {hostname}. ", end='')
    if args.no_timeout:
        print("no timeout")
        timeout_seconds = 0
    else:
        print(f"timeout in {args.timeout} minutes")
        timeout_seconds = args.timeout * 60
    print(f"time is now {current_time}")

    # --- 3. Set Up Signal Handlers and Lock ---
    # Catch common interrupt signals.
    catchable_sigs = set(signal.Signals) - {signal.SIGKILL, signal.SIGSTOP}
    for sig in catchable_sigs:
        try:
            signal.signal(sig, signal_handler)
        except (OSError, RuntimeError):
            pass # Ignore signals that can't be caught

    if timeout_seconds > 0:
        signal.alarm(timeout_seconds)
    
    # This is the main lock loop.
    stdin_fd = sys.stdin.fileno()
    disable_echo(stdin_fd)
    try:
        while True:
            print("\nKey: ", end='', flush=True)
            # We must read directly from stdin now that echo is off.
            unlock_attempt = sys.stdin.readline().rstrip('\n')
            
            is_correct = False
            if args.password:
                # Compare the encrypted hashes.
                salt = key[:2]
                is_correct = (crypt.crypt(unlock_attempt, salt) == key)
            else:
                is_correct = (unlock_attempt == key)
            
            if is_correct:
                break
    finally:
        # --- 4. Cleanup ---
        # This `finally` block ensures the terminal is restored even if an error occurs.
        enable_echo(stdin_fd)
        signal.alarm(0) # Cancel any pending alarm
        print() # Print a final newline for a clean prompt

if __name__ == "__main__":
    main()
