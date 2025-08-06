#!/usr/bin/env python3
"""
Name: ping
Description: probe for network hosts
Author: Nick Ing-Simmons, nick@ni-s.u-net.com (Original Perl Author)
License: perl

A Python port of the 'ping' utility.

Looks up a hostname and then attempts to contact it via the network
using an ICMP ECHO_REQUEST packet. Requires administrator/root
privileges to create raw ICMP sockets.
"""

import sys
import socket
import argparse
try:
    import ping3
except ImportError:
    print("Error: This script requires the 'ping3' library.", file=sys.stderr)
    print("Please install it using: pip install ping3", file=sys.stderr)
    sys.exit(1)

def main():
    """Parses arguments and pings the specified host."""
    parser = argparse.ArgumentParser(
        description="Probe for a network host.",
        usage="%(prog)s [-n] hostname [timeout]"
    )
    parser.add_argument(
        '-n',
        action='store_true',
        help='Report the address as a numeric IP instead of a hostname.'
    )
    parser.add_argument('hostname', help='The hostname or IP address to ping.')
    parser.add_argument('timeout', nargs='?', type=int, default=20,
                        help='Timeout in seconds (default: 20).')

    args = parser.parse_args()

    target_host = args.hostname
    display_host = target_host # The name to use in messages

    # --- 1. Name Resolution ---
    try:
        # Resolve the given hostname to an IP address to ping.
        ip_addr = socket.gethostbyname(target_host)
    except socket.gaierror:
        # This error occurs if the hostname cannot be resolved.
        print(f"Unknown host {target_host}", file=sys.stderr)
        sys.exit(1)

    # --- 2. Determine Display Name (-n) ---
    if args.n:
        # If -n is specified, use the numeric IP for all output.
        display_host = ip_addr
    else:
        # Otherwise, try a reverse DNS lookup for the canonical name.
        try:
            # socket.gethostbyaddr returns (hostname, aliaslist, ipaddrlist)
            canonical_name, _, _ = socket.gethostbyaddr(ip_addr)
            display_host = canonical_name
        except socket.herror:
            # If reverse lookup fails, just use the original hostname.
            pass

    # --- 3. Pinging ---
    print(f"Pinging {display_host} ({ip_addr})...", file=sys.stderr)
    try:
        # `ping3.ping()` returns the delay on success, False on timeout,
        # or None on other errors.
        delay = ping3.ping(ip_addr, timeout=args.timeout, unit='s')

        if delay is not None and delay is not False:
            print(f"{display_host} is alive", file=sys.stderr)
            sys.exit(0)
        elif delay is False:
            print(f"No answer from {display_host}", file=sys.stderr)
            sys.exit(1)
        else: # delay is None, indicating another error like Host Unknown
            print(f"Error pinging {display_host}", file=sys.stderr)
            sys.exit(1)

    except PermissionError:
        print("Permission denied: ICMP messages can only be sent from processes running as root.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
