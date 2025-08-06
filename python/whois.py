#!/usr/bin/env python3
"""
Name: whois
Description: internet domain name and network number directory service
Author: Yiorgos Adamopoulos, adamo@ieee.org (Original Perl Author)
License: perl
"""

import sys
import socket
import argparse

def query_whois(domain, server, port=43):
    """
    Performs a WHOIS query for a given domain to a specific server.

    Args:
        domain (str): The domain name to query.
        server (str): The WHOIS server to connect to.
        port (int): The port for the WHOIS service (default is 43).

    Returns:
        bool: True on success, False on failure.
    """
    if not domain or not domain.strip():
        print("Error: empty domain name provided.", file=sys.stderr)
        return False

    try:
        # Create a TCP socket and use a 'with' statement for automatic cleanup.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10) # Set a 10-second connection/read timeout
            s.connect((server, port))
            
            # Send the domain query, encoded to bytes, with a CRLF terminator.
            s.sendall(f"{domain}\r\n".encode('utf-8'))
            
            # Receive the response in a loop until the connection is closed.
            response = b''
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data
            
            # Print the decoded response.
            # We use errors='ignore' in case of non-UTF-8 characters in the reply.
            print(response.decode('utf-8', errors='ignore'), end='')
            return True

    except socket.gaierror:
        print(f"Error: Could not resolve host: {server}", file=sys.stderr)
    except socket.timeout:
        print(f"Error: Connection to {server} timed out.", file=sys.stderr)
    except socket.error as e:
        print(f"Error: A socket error occurred: {e}", file=sys.stderr)
