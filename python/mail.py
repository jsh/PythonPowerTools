#!/usr/bin/env python3

"""
Name: mail
Description: send and receive mail
Author: Clinton Pierce, clintp@geeksalad.org
License: perl
"""

import sys
import os
import re
import socket
import getpass
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from collections import deque
import tempfile
import atexit
import argparse

VERSION = '0.06'
ROWS = 23
COLS = 80
BUFFERL = 2

# Global instance of the mailbox
box = None

class MailProg:
    """Base class for mail-related objects."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        if name.startswith('get_'):
            attr = name[4:]
            return self.__dict__.get(attr)
        if name.startswith('set_'):
            attr = name[4:]
            return lambda val: self.__dict__.setdefault(attr, val)

class Mailer(MailProg):
    """Handles sending mail via SMTP."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Find user and hostname
        user = self.get_user() or os.environ.get('USER') or os.environ.get('LOGNAME')
        if not user:
            raise ValueError("Your username is not defined. $USER or $LOGNAME must be set.")
        self.set_user(user)

        if os.environ.get('REPLYADDR'):
            self.set_replyaddr(os.environ['REPLYADDR'])
        else:
            hostname = os.environ.get('HOSTNAME') or socket.gethostname()
            if not hostname:
                raise ValueError("Unable to find a reasonable hostname. Use $HOSTNAME.")
            self.set_hostname(hostname)
            self.set_replyaddr(f"{user}@{hostname}")
        
        relayhost = os.environ.get('RELAYHOST') or 'localhost'
        self.set_relayhost(relayhost)
        
        try:
            sock = socket.create_connection((self.get_relayhost(), 25), timeout=15)
            # Read the initial SMTP header
            _ = sock.recv(1024)
            self.set_socket(sock)
        except (socket.error, socket.timeout) as e:
            raise IOError(f"Unable to connect to the specified relay host ({relayhost}): {e}")

    def send(self, message):
        """Sends a message object."""
        sock = self.get_socket()
        
        debug(f"Mailed from {self.get_replyaddr()}")
        sock.sendall(f"mail from: <{self.get_replyaddr()}>\n".encode())
        _ = sock.recv(1024)
        
        for recipient_list in [message.get_to(), message.get_cc(), message.get_bcc()]:
            if recipient_list:
                for recipient in recipient_list:
                    debug(f"Sending to recipient {recipient}")
                    sock.sendall(f"rcpt to: <{recipient}>\n".encode())
                    _ = sock.recv(1024)
        
        sock.sendall(b"data\n")
        _ = sock.recv(1024)
        
        headers = []
        if message.get_to():
            headers.append(f"To: {', '.join(message.get_to())}")
        if message.get_cc():
            headers.append(f"Cc: {', '.join(message.get_cc())}")
        if message.get_subject():
            headers.append(f"Subject: {message.get_subject()}")
        
        headers.append(f"X-Mailer: Perl Power Tools mail v{VERSION}")
        
        sock.sendall('\n'.join(headers).encode())
        sock.sendall(b"\n\n")
        
        sock.sendall(message.body().encode())
        sock.sendall(b"\n.\n")
        
        _ = sock.recv(1024)
        
    def __del__(self):
        sock = self.get_socket()
        if sock:
            try:
                sock.sendall(b"quit\n")
            except (socket.error, BrokenPipeError):
                pass
            sock.close()

class Message(MailProg):
    """Represents a single email message."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.headers = []
        self.body_lines = []

    def load_from_array(self, lines):
        """Loads a message from an array of lines."""
        self.set_lines(len(lines))
        self.set_bytes(sum(len(l) for l in lines) + len(lines))
        
        is_header = True
        for line in lines:
            if not line:
                is_header = False
                continue
            if is_header:
                self.headers.append(line)
            else:
                self.body_lines.append(line)
        self._extract()

    def _extract(self):
        """Parses headers to set message attributes."""
        self.set_neverseen(True)
        self.set_read(False)
        
        for line in self.headers:
            if line.startswith("Subject:"):
                self.set_subject(line[8:].strip())
            elif line.startswith("To:"):
                self.set_to(self._parse_addrs(line[3:].strip()))
            elif line.startswith("CC:"):
                self.set_cc(self._parse_addrs(line[3:].strip()))
            elif line.startswith("From "):
                match = re.match(r'From\s+(.*)\s+(\w{3}\s+\w{3}\s+\d+\s+\d+:\d+).*', line)
                if match:
                    self.set_from(match.group(1))
                    self.set_date(match.group(2))
            elif line.startswith("Status:"):
                status = line[7:].strip()
                if 'O' in status: self.set_neverseen(False)
                if 'R' in status: self.set_read(True)
        self.set_deleted(False)

    def _parse_addrs(self, addr_str):
        """Parses a string of addresses into a list."""
        addrs = []
        # Simplified parsing
        addr_str = re.sub(r'"[^"]+"', '', addr_str)
        for part in re.split(r'[, ]+', addr_str):
            part = part.strip()
            if not part: continue
            match = re.search(r'<(.*)>', part)
            if match:
                addrs.append(match.group(1))
            else:
                addrs.append(part)
        return addrs

    def add_to_body(self, lines):
        """Appends lines to the message body."""
        self.body_lines.extend(lines)

    def summary(self):
        """Returns a one-line summary of the message."""
        status_char = 'X' if self.is_deleted() else ' ' if self.is_read() else 'N' if self.neverseen() else 'U'
        
        from_str = self.get_from() or " "
        from_str = from_str[:16].ljust(16)
        
        date_str = self.get_date() or " "
        date_str = date_str[:16].ljust(16)
        
        summary = f"{status_char:2} {self.get_sequence():2} {from_str} {date_str} {self.get_lines():3}/{self.get_bytes():4} "
        
        subject = self.get_subject() or "(no subject)"
        summary += subject[:COLS - len(summary) - 1]
        
        return summary

    def printhead(self):
        """Returns the headers as a single string."""
        return '\n'.join([h for h in self.headers if not h.startswith('Status:')])

    def body(self):
        """Returns the body as a single string."""
        self.set_read(True)
        return '\n'.join(self.body_lines)

    def whole(self, nlines=None):
        """Returns the whole message (headers and body)."""
        self.set_read(True)
        content = self.printhead() + '\n\n' + self.body()
        if nlines is not None:
            return '\n'.join(content.split('\n')[:nlines])
        return content

class Mailbox(MailProg):
    """Manages a collection of messages in a mailbox file."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = [None] # Dummy first element for 1-based indexing

    def load(self):
        """Loads messages from a mailbox file."""
        print(f"Loading the mailfile {self.get_file()}")
        if not self.get_file():
            raise ValueError("No mailbox specified")
        
        if Path(self.get_file()).is_dir():
            sys.stderr.write(f"{self.get_file()}: is a directory\n")
            return False
            
        try:
            with open(self.get_file(), 'r') as f:
                self.set_size(f.seek(0, 2))
                f.seek(0)
                
                message_lines = []
                for line in f:
                    line = line.strip()
                    if message_lines and line.startswith('From '):
                        msg = Message()
                        msg.load_from_array(message_lines)
                        msg.set_sequence(len(self.messages))
                        self.messages.append(msg)
                        message_lines = [line]
                    else:
                        message_lines.append(line)
                
                if message_lines:
                    msg = Message()
                    msg.load_from_array(message_lines)
                    msg.set_sequence(len(self.messages))
                    self.messages.append(msg)
            return True
        except IOError as e:
            sys.stderr.write(f"{self.get_file()}: cannot open: {e}\n")
            return False
    
    def write(self, options=None):
        """Writes the mailbox content back to a file."""
        options = options or {}
        
        mode = 'a' if options.get('append') else 'w'
        
        try:
            with open(self.get_file(), mode) as f:
                for msg in self.messages[1:]:
                    if not msg.is_deleted():
                        f.write(msg.whole() + '\n')
                        if options.get('unread'):
                            msg.set_read(False)
            return f"{self.get_file()}: Wrote changes successfully", None
        except IOError as e:
            sys.stderr.write(f"Failed to write to {self.get_file()}: {e}\n")
            return None, e

    def messagex(self, num):
        """Retrieves a message by its sequence number."""
        if 0 < num < len(self.messages):
            return self.messages[num]
        return None
    
    def replace(self, num, message):
        """Replaces a message at a given sequence number."""
        if 0 < num < len(self.messages):
            self.messages[num] = message

    def lastmsg(self):
        """Returns the sequence number of the last message."""
        return len(self.messages) - 1

    def nextmsg(self, current):
        """Returns the next non-deleted message number."""
        for i in range(current + 1, len(self.messages)):
            if not self.messages[i].is_deleted():
                return i
        return None

class Editor(MailProg):
    """Provides a line-mode editor for composing messages."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def edit(self, args=None):
        """Starts the editing loop."""
        msg = self.get_message()
        
        if args and args.get('subject'):
            subj = input("Subject: ")
            msg.set_subject(subj)
        
        print("Enter message body, end with a '.' on a line by itself:")
        
        body = []
        while True:
            line = sys.stdin.readline()
            if not line or line.strip() == '.':
                break
            
            if line.startswith('~'):
                cmd = line[1:].strip()
                if cmd.startswith('q'):
                    print("Aborted.")
                    return None
                elif cmd.startswith('v'):
                    vipath = get_vipath()
                    if vipath:
                        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
                            tmp_file.write('\n'.join(body))
                            tmp_file.close()
                            
                            try:
                                subprocess.run([vipath, tmp_file.name], check=True)
                                with open(tmp_file.name, 'r') as f:
                                    body = f.read().splitlines()
                            except (subprocess.CalledProcessError, IOError) as e:
                                sys.stderr.write(f"Failed to run editor: {e}\n")
                                pass
                            os.remove(tmp_file.name)
                            print("(Continued)")
                else:
                    sys.stderr.write("Unknown editor command.\n")
                continue
            
            body.append(line.strip())
            
        msg.add_to_body(body)
        self.set_message(msg)
        return msg

# Main functions
def get_vipath():
    """Returns the path to the visual editor."""
    return os.environ.get('VISUAL') or os.environ.get('EDITOR') or 'vi'

def shell():
    """Starts an interactive shell."""
    os.system(os.environ.get('SHELL', '/bin/sh'))

def mail(addrs, mesgno=None):
    """Sends a new message."""
    msg = Message()
    msg.set_to(addrs)
    editor_instance = Editor()
    editor_instance.set_mesgno(mesgno)
    editor_instance.set_message(msg)
    
    try:
        msg = editor_instance.edit({'subject': True})
        if msg:
            mailer = Mailer()
            mailer.send(msg)
    except (ValueError, IOError) as e:
        sys.stderr.write(f"Mail failed: {e}\n")

def replyCC(msgs):
    """Replies to the sender and CCs all recipients."""
    replies, cc_addrs = [], []
    subj = None
    
    for msg_no in msgs:
        original = box.messagex(msg_no)
        if not original: continue
        
        if not subj:
            subj = original.get_subject()
            if not subj.lower().startswith('re:'):
                subj = f"Re: {subj}"
        
        replies.append(original.get_from())
        if original.get_cc():
            cc_addrs.extend(original.get_cc())

    msg = Message()
    msg.set_to(replies)
    msg.set_cc(list(set(cc_addrs))) # Remove duplicates
    msg.set_subject(subj)
    
    editor_instance = Editor()
    editor_instance.set_mesgno(msgs[0])
    editor_instance.set_message(msg)
    
    print(f"To: {', '.join(replies)}")
    if cc_addrs:
        print(f"Cc: {', '.join(cc_addrs)}")
    print(f"Subject: {subj}")
    
    try:
        msg = editor_instance.edit()
        if msg:
            mailer = Mailer()
            mailer.send(msg)
    except (ValueError, IOError) as e:
        sys.stderr.write(f"Mail failed: {e}\n")

def reply(msgs):
    """Replies only to the sender."""
    # Simplified version
    replyCC(msgs)
    
def quit_cmd():
    """Quits the program, saving changes."""
    box.write()
    sys.exit()

def visual(msgs):
    """Edits messages in a visual editor."""
    for msg_no in msgs:
        message = box.messagex(msg_no)
        if not message:
            sys.stderr.write(f"Invalid message number: {msg_no}\n")
            continue
            
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write(message.whole())
            tmp_file.close()

            try:
                subprocess.run([get_vipath(), tmp_file.name], check=True)
                with open(tmp_file.name, 'r') as f:
                    lines = f.read().splitlines()
                new_msg = Message()
                new_msg.load_from_array(lines)
                box.replace(msg_no, new_msg)
            except (subprocess.CalledProcessError, IOError) as e:
                sys.stderr.write(f"Failed to execute editor: {e}\n")
            finally:
                os.remove(tmp_file.name)

def listing(msg_list, current):
    """Displays a list of message headers."""
    first = msg_list[0] if msg_list else current
    for i in range(first, min(first + ROWS - BUFFERL, box.lastmsg() + 1)):
        msg = box.messagex(i)
        if msg:
            print(msg.summary())
    return first

def msg_print(msgs, nlines=None):
    """Prints a message or part of it."""
    last_good = None
    for msg_no in msgs:
        message = box.messagex(msg_no)
        if not message:
            sys.stderr.write(f"Invalid message number: {msg_no}\n")
            continue
        print(f"Message: {message.get_sequence()}")
        print(message.whole(nlines))
        last_good = msg_no
    return last_good

def toggle(msgs, option):
    """Toggles read/deleted status for messages."""
    for msg_no in msgs:
        message = box.messagex(msg_no)
        if not message:
            sys.stderr.write(f"Invalid message number: {msg_no}\n")
            continue
        if option == 'unread':
            message.set_read(False)
        elif option == 'undelete':
            message.set_deleted(False)
        elif option == 'delete':
            message.set_deleted(True)

def msg_store(msgs, file_path, options):
    """Saves messages to a file."""
    print(f"Saving message... to {file_path}")
    tempbox = Mailbox(file=file_path)
    for msg_no in msgs:
        message = box.messagex(msg_no)
        if not message:
            sys.stderr.write(f"Invalid message number: {msg_no}\n")
            continue
        tempbox.messages.append(message)
    tempbox.write(options)
    print(f"Messages saved to {file_path}")

def parse_msg_list(arg_str, current_msg_no):
    """Parses a message list string."""
    arg_str = arg_str.strip()
    if not arg_str:
        return [current_msg_no]

    last_msg_no = box.lastmsg()
    arg_str = arg_str.replace('$', str(last_msg_no))
    arg_str = arg_str.replace('*', f'1-{last_msg_no}')
    
    msg_list = []
    for item in re.split(r'[, ]+', arg_str):
        if not item: continue
        if '-' in item:
            start, end = map(int, item.split('-'))
            msg_list.extend(range(start, end + 1))
        else:
            msg_list.append(int(item))
    return msg_list

def interactive():
    """Runs the interactive mail client loop."""
    global box, current_msg_no
    
    mailbox_path = os.environ.get('MAIL') or Path.home() / 'mbox'
    box = Mailbox(file=mailbox_path)
    
    if not box.load():
        print("You have no mail")
        sys.exit(0)
    
    current_msg_no = 1
    
    while True:
        try:
            cmd = input(f"> ")
            if not cmd:
                cmd = 'p'
            
            cmd = cmd.strip()
            
            if cmd == 'q' or cmd == 'quit':
                quit_cmd()
            
            parts = shlex.split(cmd)
            if not parts: continue
            
            command = parts[0]
            args = parts[1:]
            
            if command == '!':
                subprocess.run(args, check=False)
            else:
                msg_list = parse_msg_list(args[0] if args else '', current_msg_no)
                
                # A simple dispatcher based on command name
                if command in ['h', 'headers']:
                    current_msg_no = listing(msg_list, current_msg_no)
                elif command in ['p', 'print']:
                    current_msg_no = msg_print(msg_list)
                else:
                    sys.stderr.write(f"Command '{command}' not implemented.\n")
                    
        except (IOError, EOFError):
            quit_cmd()
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

def main():
    """Entry point for the script."""
    
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('-f', type=str, help='Mailbox file.')
    parser.add_argument('-s', type=str, help='Subject.')
    parser.add_argument('-c', type=str, help='CC addresses.')
    parser.add_argument('-b', type=str, help='BCC addresses.')
    parser.add_argument('to_addrs', nargs='*')

    args = parser.parse_args()
    
    if args.to_addrs:
        if args.f:
            sys.stderr.write("mail: to-addr may not be specified with a mailbox\n")
            sys.exit(1)
        
        msg = Message()
        msg.set_to(args.to_addrs)
        msg.set_cc(args.c.split(',')) if args.c else None
        msg.set_bcc(args.b.split(',')) if args.b else None
        msg.set_subject(args.s) if args.s else None
        
        print("Enter message body, end with Ctrl+D or '.' on a line by itself:")
        body_lines = sys.stdin.readlines()
        msg.add_to_body([l.strip() for l in body_lines])
        
        try:
            mailer = Mailer()
            mailer.send(msg)
            print("Message sent.")
        except (ValueError, IOError) as e:
            sys.stderr.write(f"Failed to send mail: {e}\n")
            sys.exit(1)
    else:
        interactive()

def debug(msg):
    """Prints debug messages if verbose mode is enabled."""
    pass # No verbose option in the Python script's parser

if __name__ == '__main__':
    main()
