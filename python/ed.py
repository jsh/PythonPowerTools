#!/usr/bin/env python3

"""
Name: ed
Description: text editor
Author: George M Jones, gmj@infinet.com
License: gpl
"""

import sys
import os
import re
import tempfile
import atexit
from collections import deque

# Constants for addressing modes
A_NOMATCH = -1
A_NOPAT = -2
A_PATTERN = -3
A_NOMARK = -4
A_RANGE = -5

# Error messages
E_ADDREXT = 'unexpected address'
E_ADDRBAD = 'invalid address'
E_ARGEXT = 'extra arguments detected'
E_SUFFBAD = 'invalid command suffix'
E_CLOSE = 'cannot close file'
E_OPEN = 'cannot open file'
E_READ = 'cannot read file'
E_NOFILE = 'no current filename'
E_FNAME = 'invalid filename'
E_UNSAVED = 'buffer modified'
E_CMDBAD = 'unknown command'
E_PATTERN = 'invalid pattern delimiter'
E_NOMATCH = 'no match'
E_NOPAT = 'no previous pattern'
E_UNDO = 'nothing to undo'

# Exit codes
EX_SUCCESS = 0
EX_FAILURE = 1

# Important globals
CurrentLineNum = 0
RememberedFilename = None
NeedToSave = False
UserHasBeenWarned = False
Error = None
Prompt = None
SearchPat = None
Scripted = False
lines = [0]
command = ''
commandsuf = ''
adrs = []
args = []
marks = {}
isGlobal = False
HelpMode = False
UndoFile = None
UndoLine = None
UndoBuffer = None
UndoCurrentLineNum = None

# Escape sequences for printing
ESC = [
    '\\000', '\\001', '\\002', '\\003', '\\004', '\\005', '\\006', '\\a',
    '\\b', '\\t', "\\n", '\\v', '\\f', '\\r', '\\016', '\\017',
    '\\020', '\\021', '\\022', '\\023', '\\024', '\\025', '\\026', '\\027',
    '\\030', '\\031', '\\032', '\\033', '\\034', '\\035', '\\036', '\\037',
    ' ', '!', '"', '#', '\\$', '%', '&', q("'"),
    '(', ')', '*', '+', ',', '-', '.', '/',
    '0', '1', '2', '3', '4', '5', '6', '7',
    '8', '9', ':', ';', '<', '=', '>', '?',
    '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
    'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
    'X', 'Y', 'Z', '[', '\\\\', ']', '^', '_',
    '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
    'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
    'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
    'x', 'y', 'z', '{', '|', '}', '~', '\\177',
    '\\200', '\\201', '\\202', '\\203', '\\204', '\\205', '\\206', '\\207',
    '\\210', '\\211', '\\212', '\\213', '\\214', '\\215', '\\216', '\\217',
    '\\220', '\\221', '\\222', '\\223', '\\224', '\\225', '\\226', '\\227',
    '\\230', '\\231', '\\232', '\\233', '\\234', '\\235', '\\236', '\\237',
    '\\240', '\\241', '\\242', '\\243', '\\244', '\\245', '\\246', '\\247',
    '\\250', '\\251', '\\252', '\\253', '\\254', '\\255', '\\256', '\\257',
    '\\260', '\\261', '\\262', '\\263', '\\264', '\\265', '\\266', '\\267',
    '\\270', '\\271', '\\272', '\\273', '\\274', '\\275', '\\276', '\\277',
    '\\300', '\\301', '\\302', '\\303', '\\304', '\\305', '\\306', '\\307',
    '\\310', '\\311', '\\312', '\\313', '\\314', '\\315', '\\316', '\\317',
    '\\320', '\\321', '\\322', '\\323', '\\324', '\\325', '\\326', '\\327',
    '\\330', '\\331', '\\332', '\\333', '\\334', '\\335', '\\336', '\\337',
    '\\340', '\\341', '\\342', '\\343', '\\344', '\\345', '\\346', '\\347',
    '\\350', '\\351', '\\352', '\\353', '\\354', '\\355', '\\356', '\\357',
    '\\360', '\\361', '\\362', '\\363', '\\364', '\\365', '\\366', '\\367',
    '\\370', '\\371', '\\372', '\\373', '\\374', '\\375', '\\376', '\\377'
]

# Command definitions
CMD_TAB = {
    '!': 'edPipe', '=': 'edPrintLineNum', 'f': 'edFilename', 'd': 'edDelete',
    'P': 'edPrompt', 'p': 'edPrint', 's': 'edSubstitute', 'j': 'edJoin',
    't': 'edMove', 'H': 'edSetHelp', 'h': 'edHelp', 'k': 'edMark',
    'm': 'edMoveDel', 'n': 'edPrintNum', 'l': 'edPrintBin', 'Q': 'edQuit',
    'q': 'edQuitAsk', 'i': 'edInsert', 'a': 'edAppend', 'w': 'edWrite',
    'W': 'edWriteAppend', 'c': 'edChangeLines', 'E': 'edEdit', 'e': 'edEditAsk',
    'r': 'edRead', 'u': 'edUndo', '_': 'edSetCurrentLine', 'nop': 'edNop',
}

RO_CMDS = {
    '!': True, '=': True, 'f': True, 'P': True, 'p': True, 'H': True, 'h': True,
    'k': True, 'n': True, 'l': True, 'Q': True, 'q': True, 'W': True, 'w': True,
    '_': True, 'nop': True,
}

WANT_FILE = {
    'e': True, 'E': True, 'f': True, 'r': True, 'w': True, 'W': True,
}

# --- Signal handling ---
def handle_hup(signum, frame):
    """Saves a modified buffer to 'ed.hup' on HUP signal."""
    if NeedToSave:
        try:
            with open('ed.hup', 'w') as f:
                f.write('\n'.join(lines[1:]))
        except IOError:
            pass
    sys.exit(EX_FAILURE)

# --- Main loop and initialization ---
def init_edit():
    """Initializes the editor by optionally loading a file."""
    global args
    if args[0] is not None:
        err = ed_edit(0)
        if err == E_OPEN:
            ed_warn(err)
        elif err:
            ed_warn(err)
    return

def input_loop():
    """Main interactive loop for getting user commands."""
    global command, commandsuf, adrs, args
    while True:
        command = commandsuf = ''
        adrs = []
        args = []
        
        try:
            if Prompt is not None:
                sys.stdout.write(Prompt)
                sys.stdout.flush()
            
            line = sys.stdin.readline()
            if not line:
                ed_quit_ask()
                continue
            
            line = line.rstrip('\n')
            
            if not ed_parse(line):
                ed_warn(E_CMDBAD)
                continue
            
            # Sanity check addresses
            for adr in adrs:
                if adr == A_NOMATCH:
                    ed_warn(E_NOMATCH)
                    return
                elif adr == A_NOPAT:
                    ed_warn(E_NOPAT)
                    return
                elif adr < 0:
                    ed_warn(E_ADDRBAD)
                    return
            if len(adrs) == 2 and adrs[1] < adrs[0]:
                ed_warn(E_ADDRBAD)
                continue
            
            func_name = CMD_TAB.get(command)
            if not func_name:
                ed_warn(E_CMDBAD)
                continue
                
            func = getattr(sys.modules[__name__], func_name)
            
            save_state = not RO_CMDS.get(command, False)
            if save_state:
                save_undo()
                
            err = func()
            ed_warn(err) if err else None
            
            if save_state:
                global UndoFile, UndoLine
                UndoFile = UndoBuffer
                UndoLine = UndoCurrentLineNum
                
        except (IOError, EOFError):
            ed_quit_ask()
        except KeyboardInterrupt:
            print()
            continue

# --- Command functions ---
def ed_nop():
    pass

def ed_change_lines():
    err = ed_delete()
    if not err:
        global adrs
        adrs[1] = None
        ed_insert()
    return err

def ed_prompt():
    global Prompt
    if len(adrs) > 0 or len(args) > 0:
        return E_ADDREXT if len(adrs)>0 else E_ARGEXT
    
    if Prompt is None:
        Prompt = '*'
    else:
        Prompt = None
    return

def ed_set_help():
    global HelpMode
    if len(adrs) > 0 or len(args) > 0:
        return E_ADDREXT if len(adrs)>0 else E_ARGEXT
    
    HelpMode = not HelpMode
    if HelpMode and Error:
        print(Error)
    return

def ed_help():
    if len(adrs) > 0 or len(args) > 0:
        return E_ADDREXT if len(adrs)>0 else E_ARGEXT
    if Error:
        print(Error)
    return

def ed_mark():
    global marks
    if not args or not re.match(r'^[a-z]$', args[0]):
        return E_SUFFBAD
    
    adr = adrs[1] if len(adrs) > 1 else adrs[0] if len(adrs)>0 else CurrentLineNum
    if adr <= 0:
        return E_ADDRBAD
    
    marks[args[0]] = adr
    return

def ed_print(mode=0):
    do_bin = mode == 2
    do_num = mode == 1
    
    if args:
        if re.match(r'^[lnp]+$', args[0]):
            do_bin = 'l' in args[0]
            do_num = 'n' in args[0]
            if len(args[0]) > 0:
                args[0] = args[0][1:]
            else:
                args.clear()
        
    global CurrentLineNum
    
    if not isGlobal:
        if not adrs:
            adrs.append(CurrentLineNum)
        if len(adrs) == 1:
            adrs.append(adrs[0])
            
    if adrs[0] <= 0 or adrs[1] <= 0:
        return E_ADDRBAD
        
    for i in range(adrs[0], adrs[1] + 1):
        if do_num:
            print(f"{i}\t", end='')
        if do_bin:
            print(escape_line(i), end='')
        else:
            print(lines[i])
            
    CurrentLineNum = adrs[-1]
    return

def ed_print_num():
    return ed_print(1)
    
def ed_print_bin():
    return ed_print(2)

def ed_pipe():
    if adrs: return E_ADDREXT
    if not args: return E_ARGEXT
    
    cmd = args[0].strip()
    if not cmd: return E_ARGEXT
    
    print("!")
    subprocess.run(shlex.split(cmd), check=False)
    return

def ed_join():
    global NeedToSave, UserHasBeenWarned, CurrentLineNum
    
    if args: return E_ARGEXT
    
    if not adrs:
        if CurrentLineNum == maxline(): return E_ADDRBAD
        adrs.append(CurrentLineNum)
        adrs.append(CurrentLineNum + 1)
    elif len(adrs) == 1:
        return
    
    if adrs[0] == adrs[1]:
        return
        
    joined_line = ''.join(lines[adrs[0]:adrs[1]+1])
    lines[adrs[0]] = joined_line
    del lines[adrs[0]+1:adrs[1]+1]
    
    NeedToSave = True
    UserHasBeenWarned = False
    CurrentLineNum = adrs[0]
    return

def ed_move(delete=False):
    global NeedToSave, UserHasBeenWarned, CurrentLineNum
    
    start = adrs[0] if adrs else CurrentLineNum
    end = adrs[1] if len(adrs)>1 else start
    
    if start<=0 or end<=0: return E_ADDRBAD
    
    dst_str = args[0] if args else '.'
    dst = get_addr(dst_str)
    
    if dst == A_NOMATCH: return E_NOMATCH
    if dst == A_NOPAT: return E_NOPAT
    if dst < 0: return E_ADDRBAD

    if delete and start <= dst <= end:
        return E_ADDRBAD
        
    moved_lines = lines[start:end+1]
    del lines[start:end+1]
    
    if dst > start:
        dst -= len(moved_lines)
    
    lines[dst+1:dst+1] = moved_lines
    
    NeedToSave = True
    UserHasBeenWarned = False
    CurrentLineNum = dst + len(moved_lines)
    return

def ed_move_del():
    return ed_move(delete=True)

def ed_quit(force=False):
    if len(adrs)>0 or len(args)>0: return E_ADDREXT if len(adrs)>0 else E_ARGEXT
    if not force and NeedToSave and not UserHasBeenWarned and not Scripted:
        global UserHasBeenWarned
        UserHasBeenWarned = True
        return E_UNSAVED
    sys.exit(EX_SUCCESS)

def ed_quit_ask():
    return ed_quit(False)

def ed_append():
    return ed_insert(append=True)

def ed_write_append():
    return ed_write(append=True)

def ed_edit_ask():
    return ed_edit(ask=True)

def ed_substitute():
    global NeedToSave, UserHasBeenWarned, CurrentLineNum
    
    if not args or not args[0]: return E_PATTERN
    
    # Simple s/// parser
    parts = args[0].split(args[0][0])
    if len(parts) < 3: return E_PATTERN
    
    pattern = parts[1]
    replacement = parts[2]
    
    if not adrs: adrs.append(CurrentLineNum)
    if len(adrs) == 1: adrs.append(adrs[0])
    
    found_match = False
    for i in range(adrs[0], adrs[1]+1):
        try:
            new_line, num_subs = re.subn(pattern, replacement, lines[i])
            if num_subs > 0:
                lines[i] = new_line
                found_match = True
                NeedToSave = True
                UserHasBeenWarned = False
                CurrentLineNum = i
        except re.error:
            return E_PATTERN
    
    if not found_match:
        return E_NOMATCH
    return

def ed_delete():
    global NeedToSave, UserHasBeenWarned, CurrentLineNum
    if args: return E_ARGEXT
    if not adrs:
        if CurrentLineNum == 0: return E_ADDRBAD
        adrs.append(CurrentLineNum)
        adrs.append(CurrentLineNum)
        
    del lines[adrs[0]:adrs[1]+1]
    
    NeedToSave = True
    UserHasBeenWarned = False
    CurrentLineNum = adrs[0]
    if CurrentLineNum > maxline():
        CurrentLineNum = maxline()
    return

def ed_filename():
    global RememberedFilename
    if adrs: return E_ADDREXT
    if args:
        if not illegal_file(args[0]):
            RememberedFilename = args[0]
        else:
            return E_FNAME
    if RememberedFilename:
        print(RememberedFilename)
    else:
        return E_NOFILE
    return

def illegal_file(name):
    return not name or name in ['.', '..'] or name.startswith('!') or name.endswith('/')

def ed_write(append=False):
    global NeedToSave, UserHasBeenWarned
    mode = 'a' if append else 'w'
    
    if not adrs:
        adrs.append(1)
        adrs.append(maxline())
    elif len(adrs)==1:
        adrs.append(adrs[0])
    
    filename = args[0] if args else RememberedFilename
    if not filename: return E_NOFILE
    if illegal_file(filename): return E_FNAME
    
    try:
        with open(filename, mode) as f:
            for i in range(adrs[0], adrs[1]+1):
                f.write(lines[i] + '\n')
        
        if adrs[0] == 1 and adrs[1] == maxline():
            NeedToSave = UserHasBeenWarned = False
        
    except IOError:
        return E_OPEN
        
    print(f"{sum(len(lines[i])+1 for i in range(adrs[0], adrs[1]+1))}")
    return

def ed_read():
    global lines, CurrentLineNum, NeedToSave, UserHasBeenWarned
    
    if len(adrs) == 1: adrs.append(adrs[0])
    targ = adrs[1] if len(adrs)>1 else maxline()
    
    filename = args[0] if args else RememberedFilename
    if not filename: return E_NOFILE
    if illegal_file(filename): return E_FNAME
    
    try:
        with open(filename, 'r') as f:
            new_lines = [l.rstrip('\n') for l in f.readlines()]
            lines[targ+1:targ+1] = new_lines
    except IOError:
        return E_OPEN
        
    print(f"{sum(len(l)+1 for l in new_lines)}")
    CurrentLineNum = targ + len(new_lines)
    NeedToSave = True
    UserHasBeenWarned = False
    return

def ed_edit(ask=False):
    global lines, CurrentLineNum, NeedToSave, UserHasBeenWarned, RememberedFilename
    
    if adrs: return E_ADDREXT
    if NeedToSave and ask and not UserHasBeenWarned and not Scripted:
        UserHasBeenWarned = True
        return E_UNSAVED

    filename = args[0] if args else RememberedFilename
    if not filename:
        CurrentLineNum = 0
        lines = [0]
        return
        
    if illegal_file(filename): return E_FNAME
    
    try:
        with open(filename, 'r') as f:
            lines = [0] + [l.rstrip('\n') for l in f.readlines()]
            RememberedFilename = filename
    except IOError:
        return E_OPEN
        
    print(f"{sum(len(l)+1 for l in lines[1:])}")
    CurrentLineNum = maxline()
    NeedToSave = UserHasBeenWarned = False
    return

def ed_insert(append=False):
    global lines, CurrentLineNum, NeedToSave, UserHasBeenWarned
    
    if args: return E_ARGEXT
    
    targ = adrs[0] if adrs else CurrentLineNum
    targ += 1 if append else 0
    
    new_lines = []
    print("Enter text. Terminate with '.' on a line by itself.")
    while True:
        line = sys.stdin.readline().rstrip('\n')
        if line == '.': break
        new_lines.append(line)
        
    lines[targ:targ] = new_lines
    CurrentLineNum = targ + len(new_lines)
    
    NeedToSave = True
    UserHasBeenWarned = False
    return

def ed_undo():
    global lines, CurrentLineNum, NeedToSave, UserHasBeenWarned
    if not UndoBuffer: return E_UNDO
    
    lines = UndoBuffer
    CurrentLineNum = UndoCurrentLineNum
    NeedToSave = True
    UserHasBeenWarned = False
    return

def ed_set_current_line():
    global CurrentLineNum
    if args: return E_ARGEXT
    
    if not adrs:
        if CurrentLineNum == maxline(): return E_ADDRBAD
        CurrentLineNum += 1
    elif len(adrs) == 1:
        CurrentLineNum = adrs[0]
    elif len(adrs) == 2:
        CurrentLineNum = adrs[1]
        
    print(lines[CurrentLineNum])
    return

def ed_print_line_num():
    if args: return E_ARGEXT
    adr = adrs[1] if len(adrs)>1 else adrs[0] if adrs else maxline()
    print(adr)
    return

def ed_parse(line):
    global command, adrs, args, SearchPat
    
    line = line.lstrip()
    
    # Addresses
    if line:
        # Check for numeric or special addresses
        pass
    
    # Global search and command
    if line.startswith('g/') or line.startswith('v/'):
        is_invert = line.startswith('v/')
        line = line[2:]
        delim = line[0]
        pattern, rest = line.split(delim, 1)
        
        found_lines = ed_search_global(pattern, is_invert)
        if not found_lines: return True
        
        command = 'nop'
        adrs = found_lines
        if rest:
            pass # TODO: handle command on rest
        return True

    # Single command
    if len(line) > 0:
        cmd = line[0]
        if cmd in CMD_TAB:
            command = cmd
            rest = line[1:].strip()
            if rest:
                args.append(rest)
            return True
        
    # Bare address
    if len(line) > 0 and (line[0].isdigit() or line[0] in '$.'):
        command = '_'
        adrs.append(get_addr(line))
        return True
    
    return False

def get_addr(s):
    global CurrentLineNum, SearchPat, marks
    s = s.strip()
    if s == '.': return CurrentLineNum
    if s == '$': return maxline()
    if s == '#': return maxline() # Not in original, but common
    if re.match(r'^[0-9]+$', s): return int(s)
    
    if s.startswith('/'):
        delim = s[0]
        pattern, rest = s[1:].split(delim, 1)
        if not pattern:
            if not SearchPat: return A_NOPAT
            pattern = SearchPat
        SearchPat = pattern
        return ed_search(pattern, backward=False)
        
    if s.startswith('?'):
        delim = s[0]
        pattern, rest = s[1:].split(delim, 1)
        if not pattern:
            if not SearchPat: return A_NOPAT
            pattern = SearchPat
        SearchPat = pattern
        return ed_search(pattern, backward=True)

    if s.startswith("'"):
        mark = s[1]
        return marks.get(mark, A_NOMARK)

    return A_ADDRBAD

def ed_search(pattern, backward=False):
    start = CurrentLineNum
    if backward:
        search_range = range(start - 1, 0, -1)
    else:
        search_range = range(start, maxline() + 1)
        
    for i in search_range:
        if i == 0: continue
        if re.search(pattern, lines[i]):
            return i
    
    # Loop around
    if backward:
        search_range = range(maxline(), start - 1, -1)
    else:
        search_range = range(1, start + 1)
        
    for i in search_range:
        if i == 0: continue
        if re.search(pattern, lines[i]):
            return i
            
    return A_NOMATCH

def ed_search_global(pattern, invert=False):
    global adrs
    if not adrs: adrs = [1, maxline()]
    
    found = []
    for i in range(adrs[0], adrs[1] + 1):
        is_match = bool(re.search(pattern, lines[i]))
        if is_match and not invert:
            found.append(i)
        elif not is_match and invert:
            found.append(i)
            
    return found

def maxline():
    return len(lines) - 1

def save_undo():
    global UndoBuffer, UndoCurrentLineNum, lines
    UndoBuffer = list(lines)
    UndoCurrentLineNum = CurrentLineNum

def ed_set_current_line():
    global CurrentLineNum
    if args: return E_ARGEXT
    
    adr = adrs[1] if len(adrs) > 1 else adrs[0] if adrs else CurrentLineNum
    if not adr: return E_ADDRBAD
    
    if 0 < adr <= maxline():
        CurrentLineNum = adr
        print(lines[CurrentLineNum])
    else:
        return E_ADDRBAD

def main():
    global args, Prompt, Scripted, lines, CurrentLineNum, RememberedFilename
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-p', type=str, help='Prompt string.')
    parser.add_argument('-s', action='store_true', help='Suppress diagnostics.')
    parser.add_argument('file', nargs='?', default=None, help='File to edit.')
    
    try:
        parsed_args = parser.parse_args()
    except argparse.ArgumentError:
        Usage()
        
    Prompt = parsed_args.p
    Scripted = parsed_args.s
    
    if parsed_args.file:
        args = [parsed_args.file]
    else:
        args = []
        
    # Handle the initial file load
    if args:
        if args[0] == '-':
            lines = [0] + sys.stdin.readlines()
            lines = [l.rstrip('\n') for l in lines]
            CurrentLineNum = maxline()
            print(f"{maxline()} lines read")
        else:
            try:
                with open(args[0], 'r') as f:
                    lines = [0] + [l.rstrip('\n') for l in f.readlines()]
                    CurrentLineNum = maxline()
                    RememberedFilename = args[0]
                    print(f"{maxline()} lines read")
            except IOError:
                sys.stderr.write(f"ed: {args[0]}: No such file or directory\n")
                lines = [0]
    
    input_loop()

def Usage():
    print("usage: ed [-p prompt] [-s] [file]\n")
    sys.exit(EX_FAILURE)

if __name__ == '__main__':
    # Set up HUP signal handler
    # signal.signal(signal.SIGHUP, handle_hup)
    
    main()
