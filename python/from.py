#!/usr/bin/env python3
"""
Name: from
Description: print names of those who have sent mail
Author: Johan Vromans, jvromans@squirrel.nl (Original Perl Author)
License: public domain
"""

import sys
import os
import argparse
import getpass
import mailbox
from email.utils import parsedate_to_datetime, formatdate

def find_default_mailbox():
    """
    Tries to find the current user's system mailbox in common locations.
    Returns the path to the mailbox or None if not found.
    """
    try:
        user = getpass.getuser()
    except Exception:
        return None

    # Common locations for system mailboxes
    possible_paths = [
        f"/var/mail/{user}",
        f"/var/spool/mail/{user}",
        f"/usr/mail/{user}",
    ]

    for path in possible_paths:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            return path
            
    return None

def process_mailbox(filepath, show_numbers):
    """
    Opens and processes a single mailbox file, printing a summary of its contents.
    """
    try:
        # mailbox.mbox is designed to parse standard mbox files.
        mbox = mailbox.mbox(filepath)
    except Exception as e:
        print(f"Error opening or parsing mailbox '{filepath}': {e}", file=sys.stderr)
        return

    for i, msg in enumerate(mbox, 1):
        # Extract headers from the message object.
        # The 'From' header is often more descriptive than the mbox "From_" line.
        sender = msg.get('From', 'No Sender')
        subject = msg.get('
