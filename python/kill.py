#!/usr/bin/env python3
"""
Name: kill
Description: send signals to a process
Author: Theo Van Dinter, felicity@kluge.net (Original Perl Author)
License: perl
"""

import sys
import os
import signal
import re

def get_signal_maps():
    """
    Builds maps of signal names to numbers and vice-versa from the signal module.
    """
    sig_name_to_num = {}
    sig_num_to_name = {}
    for sig_name in dir(signal):
        if sig_name.startswith('SIG') and not sig_name.startswith('SIG_'):
            num = getattr(signal, sig_name)
            # Remove the 'SIG' prefix for matching
            clean_name = sig_name[3:]
            sig_name_to_num[clean_name] = num
            sig_num_to_name[num] = clean_name
    return sig_name_to_num, sig_num_to_name

def list_signals(sig_num_to_name):
    """
    Prints a formatted list of available signal numbers and names.
    """
    # Sort signals by number for consistent output
    sorted_signals = sorted(sig_num_to_name.items())
    
    output_line = []
    for i, (num, name) in enumerate(sorted_signals):
        output_line.append(f"{num:>2d}:{name:<6s}")
        # Print 8 columns per row, or flush on the last item
        if (i + 1) % 8 == 0 or i == len(sorted_signals) - 1:
            print(" ".join(output_line))
            output_line = []

def usage(program_name):
    """Prints a usage message to the console and exits."""
    print(f"""usage:  {program_name} [-s signalname] PID...
        {program_name} [-signalname] PID...
        {program_name} [-signalnumber] PID...
        {program_name} [-l]""")
    sys.exit(1)

def main():
    """Parses arguments and sends signals to processes."""
    program_name = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    
    if not args:
        usage(program_name)

    sig_name_to_num, sig_num_to_name = get_signal_maps()
    
    # Default signal is TERM
    signal_to_send = signal.SIGTERM

    # --- Argument Parsing ---
    first_arg = args[0]

    if first_arg == '-l':
        list_signals(sig_num_to_name)
        sys.exit(0)
    
    elif first_arg.startswith('-'):
        # This block handles -SIGNALNAME, -SIGNALNUMBER, and -s SIGNALNAME
        args.pop(0) # Consume the flag
        
        # Check for -s SIGNALNAME
        if first_arg == '-s':
            if not args:
                print(f"{program_name}: option requires an argument -- 's'", file=sys.stderr)
                usage(program_name)
            signal_spec = args.pop(0)
        else:
            signal_spec = first_arg[1:] # Strip the leading '-'

        # Try to interpret as a number first
        if signal_spec.isdigit():
            sig_num = int(signal_spec)
            if sig_num in sig_num_to_name:
                signal_to_send = sig_num
            else:
                print(f"{program_name}: {sig_num}: Unknown signal; valid signals...", file=sys.stderr)
                list_signals(sig_num_to_name)
                sys.exit(1)
        # Otherwise, interpret as a name
        else:
            sig_name = signal_spec.upper().lstrip("SIG")
            if sig_name in sig_name_to_num:
                signal_to_send = sig_name_to_num[sig_name]
            else:
                print(f"{program_name}: {sig_name}: Unknown signal; valid signals...", file=sys.stderr)
                list_signals(sig_num_to_name)
                sys.exit(1)

    # --- PID Processing ---
    pids_to_kill = args
    if not pids_to_kill:
        print(f"{program_name}: No PIDs specified.", file=sys.stderr)
        sys.exit(1)
        
    exit_status = 0
    for pid_str in pids_to_kill:
        try:
            pid = int(pid_str)
            os.kill(pid, signal_to_send)
        except ValueError:
            print(f"{program_name}: failed to parse argument '{pid_str}'", file=sys.stderr)
            exit_status = 1
        except OSError as e:
            # os.kill raises OSError for problems like "No such process"
            print(f"{program_name}: {pid_str}: {e.strerror}", file=sys.stderr)
            exit_status = 1
            
    sys.exit(exit_status)

if __name__ == "__main__":
    main()
