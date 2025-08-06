#!/usr/bin/env python3

"""
Name: robots
Description: fight off villainous robots
Author: John C. Siracusa, siracusa@mindspring.com
License: perl
"""

import sys
import os
import re
import random
import time
import signal
import curses
import argparse
from collections import defaultdict, deque

# Constants
ALIVE = 1
DEAD = 0

SIDEBAR_WIDTH = 19
REAL_TIME_STEP = 3
INITIAL_ROBOTS = 10
ROBOT_SCORE = 10
ROBOT_INCREMENT = 10
ADVANCE_LEVEL = 4
ADVANCE_BONUS = (60 * ROBOT_SCORE)

HIGH_SCORE_X = 15
MAX_LEVELS = 4
MAX_ROBOTS = (MAX_LEVELS * ROBOT_INCREMENT)
MAX_SCORES = 200
MAX_SCORES_PER_USER = 5

ROBOT_CHR = '+'
HEAP_CHR = '*'
PLAYER_CHR = '@'
PLAYER_WAIL = 'AARRrrgghhhh....'

MIN_LINES = 24
MIN_COLS = 80
VERSION = '0.50'

# File-scoped lexicals
score_file = '/var/games/robots_roll'
win = None
arena = {}

# Flag variables
real_time = False
real_time_move = False
pattern_roll = False
stand_still = False
new_score = False
just_suspended = False
ask_quit = False
another_game = False
cheater = False

# Miscellaneous settings and structures
initial_level = 1
robot_increment = ROBOT_INCREMENT
real_time_step = REAL_TIME_STEP
high_scores = defaultdict(list)
my_score = None
old_sig = {}

# Movement keys
movement = ['h', 'l', 'k', 'j', 'y', 'u', 'b', 'n', '.']
key_l, key_r, key_u, key_d, key_ul, key_ur, key_dl, key_dr, key_nop = movement
key_w, key_t, key_q, key_safe_wait, key_nop_alt, key_redraw = 'w', 't', 'q', '>', ' ', '\x0c'

move_list = [c.upper() for c in (key_ul, key_l, key_dl, key_d, key_dr, key_r, key_ur, key_u)]
key_move_re = '[' + ''.join(movement) + key_nop_alt + ']'
key_u_re = f'[{key_ul}{key_u}{key_ur}]'
key_d_re = f'[{key_dl}{key_d}{key_dr}]'
key_l_re = f'[{key_ul}{key_l}{key_dl}]'
key_r_re = f'[{key_ur}{key_r}{key_dr}]'

def usage(exit_code=0):
    """Displays usage message and exits."""
    if win:
        win.endwin()
    sys.stderr.write(f"""Usage: robots -hjstv [-a [level]] [-i num] [-r [secs]] [scorefile]
 -a <level>  Advance to higher levels directly (default: {ADVANCE_LEVEL})
 -h          Show this help screen
 -i <num>    Increment robots by <num> after each level
 -j          Jump movement (don't show intermediate positions)
 -r          Play in real time
 -s          Don't play, just show score file
 -t          Auto-teleport when in danger
 --manual    Show documentation
 --version   Show version
""")
    sys.exit(exit_code)

def version():
    """Displays version number and exits."""
    sys.stderr.write(f"robots version {VERSION}\n")
    sys.exit(0)

def manual():
    """Displays the manual page."""
    os.execvp('pydoc', ['pydoc', 'robots'])

def sanity_check():
    """Performs sanity checks on options and terminal size."""
    global score_file
    
    if hasattr(curses, 'LINES') and hasattr(curses, 'COLS'):
        if curses.COLS < MIN_COLS or curses.LINES < MIN_LINES:
            sys.exit(f"Need at least a {MIN_COLS}x{MIN_LINES} screen")
    else:
        sys.exit("Cannot determine screen size!")

    if score_file:
        if os.path.isfile(score_file):
            if not os.access(score_file, os.R_OK | os.W_OK):
                sys.stderr.write(f"{score_file}: no scores will be saved\n")
                score_file = None
        else:
            score_file = None

def parse_args(args):
    """Parses command-line arguments and sets global options."""
    global score_file, pattern_roll, stand_still, cheater
    
    parser = argparse.ArgumentParser(add_help=False, usage=argparse.SUPPRESS)
    parser.add_argument('-a', nargs='?', type=int, const=ADVANCE_LEVEL)
    parser.add_argument('-h', action='store_true')
    parser.add_argument('-i', type=int, default=ROBOT_INCREMENT)
    parser.add_argument('-j', action='store_true')
    parser.add_argument('-r', nargs='?', type=int, const=REAL_TIME_STEP)
    parser.add_argument('-s', action='store_true')
    parser.add_argument('-t', action='store_true')
    parser.add_argument('--help', action='store_true')
    parser.add_argument('--manual', action='store_true')
    parser.add_argument('--version', action='store_true')
    parser.add_argument('scorefile', nargs='?', default=score_file)
    
    opts = parser.parse_args(args)
    
    if opts.help or opts.h: usage()
    if opts.version: version()
    if opts.manual: manual()

    if opts.scorefile:
        score_file = opts.scorefile
        if score_file.endswith('pattern_roll'): pattern_roll = True
        elif score_file.endswith('stand_still'): stand_still = True

    opts.t = (pattern_roll or stand_still) or opts.t
    
    if (opts.i < ROBOT_INCREMENT) or (opts.a and opts.a < ADVANCE_LEVEL):
        cheater = True

    return opts

def init_arena(opts):
    """Initializes the game arena and global state."""
    global arena, initial_level, robot_increment, real_time, real_time_step
    
    initial_level = opts.a if opts.a else 1
    robot_increment = opts.i
    real_time = opts.r is not None
    real_time_step = opts.r if real_time else 0
    
    num_robots = INITIAL_ROBOTS + ((initial_level - 1) * robot_increment)

    arena = {
        'MIN_X': 1,
        'MAX_X': curses.COLS - SIDEBAR_WIDTH - 2,
        'MIN_Y': 1,
        'MAX_Y': curses.LINES - 2,

        'SCORE_X': curses.COLS - SIDEBAR_WIDTH + 8,
        'SCORE_Y': 21,
        'PROMPT_X': curses.COLS - SIDEBAR_WIDTH + 1,
        'PROMPT_Y': 22,

        'LEVEL': initial_level,
        'PLAYER': {
            'X': 0, 'Y': 0, 'STATUS': ALIVE, 'SCORE': 0, 'BONUS': 0, 'ADV_BONUS': 0,
        },
        'ROBOTS': [],
        'MAX_ROBOTS': MAX_ROBOTS,
        'HEAP_AT': {},
        'ROBOT_AT': {},
    }
    arena['ROBOTS'] = build_robots(num_robots)

def build_robots(num_robots):
    """Creates a list of robot dictionaries."""
    num_robots = min(num_robots, arena['MAX_ROBOTS'])
    return [{'X': 0, 'Y': 0, 'STATUS': ALIVE} for _ in range(num_robots)]

def starting_positions():
    """Sets initial positions for the player and robots."""
    num_robots = INITIAL_ROBOTS + ((arena['LEVEL'] - 1) * robot_increment)
    arena['ROBOTS'] = build_robots(num_robots)
    arena['HEAP_AT'] = {}
    arena['ROBOT_AT'] = {}
    
    seen = {}
    min_x, min_y = arena['MIN_X'], arena['MIN_Y']
    rng_x, rng_y = arena['MAX_X'] - min_x, arena['MAX_Y'] - min_y
    
    for robot in arena['ROBOTS']:
        while True:
            x = random.randrange(rng_x) + min_x
            y = random.randrange(rng_y) + min_y
            if not seen.get(f"{x}:{y}"):
                seen[f"{x}:{y}"] = 1
                robot['X'], robot['Y'], robot['STATUS'] = x, y, ALIVE
                arena['ROBOT_AT'][f"{x}:{y}"] = 1
                break
    
    while True:
        x = random.randrange(rng_x) + min_x
        y = random.randrange(rng_y) + min_y
        if not seen.get(f"{x}:{y}"):
            arena['PLAYER']['X'], arena['PLAYER']['Y'] = x, y
            break
            
    arena['PLAYER']['STATUS'] = ALIVE

def draw_arena():
    """Draws the game board and legend."""
    win.clear()
    
    # Top and bottom borders
    border_str = '+' + '-' * arena['MAX_X'] + '+'
    win.addstr(0, 0, border_str)
    win.addstr(arena['MAX_Y'] + 1, 0, border_str)

    # Side borders
    for line in range(1, arena['MAX_Y'] + 1):
        win.addch(line, arena['MIN_X'] - 1, '|')
        win.addch(line, arena['MAX_X'] + 1, '|')

    # Legend
    legend = """Directions:

y k u
\\|/
h- -l
/|\\
b j n

Commands:

w:  wait for end
t:  teleport
q:  quit
^L: redraw screen

Legend:

+:  robot
*:  junk heap
@:  you

Score:
"""
    x_off = arena['MAX_X'] + 2
    y = 0
    for line in legend.splitlines():
        win.addstr(y, x_off, ' ' + line)
        win.clrtoeol()
        y += 1

    update_score()
    update_bonus()
    
    # Draw robots and player
    for robot in arena['ROBOTS']:
        win.addch(robot['Y'], robot['X'], ROBOT_CHR)
    win.addch(arena['PLAYER']['Y'], arena['PLAYER']['X'], PLAYER_CHR)
    win.move(arena['PLAYER']['Y'], arena['PLAYER']['X'])

    if arena['PLAYER']['STATUS'] == DEAD:
        kill_player_wail()

    if ask_quit: quit_prompt()
    elif another_game: another_game_prompt()
    
    win.refresh()

def play():
    """Main game loop."""
    global pattern_roll, stand_still, Real_Time_Move
    
    won = False
    move_index = 0
    repeat = 0
    
    while True:
        chr_in = ''
        if pattern_roll and len(arena['ROBOT_AT']) > 1:
            chr_in = move_list[move_index]
            win.addstr(0, 0, f"{chr_in}{'-' * arena['MAX_X']}+")
            move_index = (move_index + 1) % len(move_list)
        elif stand_still and len(arena['ROBOT_AT']) > 1:
            chr_in = key_safe_wait
        else:
            chr_in = get_command()

        if chr_in.isdigit() and chr_in not in movement:
            repeat = int(chr_in)
            continue

        if won and chr_in != key_redraw:
            arena['PLAYER']['BONUS'] = arena['PLAYER']['ADV_BONUS'] = 0
            update_bonus()
            won = False
        
        while repeat > 0 or repeat == 0:
            if chr_in in movement:
                if chr_in.isupper() and chr_in.upper() == chr_in and chr_in not in [key_nop_alt, key_nop]:
                    while move_player(chr_in): pass
                    repeat = 0
                else:
                    if not move_player(chr_in):
                        repeat = 0
            elif chr_in == key_t:
                teleport()
            elif chr_in == key_w:
                wait()
            elif chr_in == key_safe_wait:
                wait()
                if stand_still: teleport()
            elif chr_in == key_q:
                if quit_game():
                    return
            elif chr_in == key_redraw:
                redraw()
                break
            else:
                break
                
            if arena['PLAYER']['STATUS'] == DEAD:
                if not kill_player(): return
                
            won = not len(arena['ROBOT_AT'])
            if won: break
            
            if repeat > 0:
                repeat -= 1
        
        if won:
            arena['PLAYER']['SCORE'] += arena['PLAYER']['BONUS']
            if arena['LEVEL'] == initial_level and initial_level >= ADVANCE_LEVEL:
                arena['PLAYER']['ADV_BONUS'] = ADVANCE_BONUS
                arena['PLAYER']['SCORE'] += arena['PLAYER']['ADV_BONUS']
            
            arena['LEVEL'] += 1
            clear_arena()
            starting_positions()
            draw_arena()

        win.refresh()

def get_command():
    """Gets a character from the keyboard, handling real-time and signals."""
    global real_time_move, just_suspended
    
    old_sig_alrm = signal.getsignal(signal.SIGALRM)
    old_sig_tstp = signal.getsignal(signal.SIGTSTP)

    chr_in = ''
    try:
        if real_time:
            signal.signal(signal.SIGALRM, lambda s,f: (_ for _ in ()).throw(KeyboardInterrupt))
            signal.alarm(real_time_step)
        
        signal.signal(signal.SIGTSTP, lambda s,f: (_ for _ in ()).throw(InterruptedError))

        chr_in = win.getch()
        if real_time:
            signal.alarm(0)
    except KeyboardInterrupt:
        chr_in = key_nop
        real_time_move = True
    except InterruptedError:
        real_time_move = False
        just_suspended = True
        
        win.clear()
        win.refresh()
        win.endwin()
        
        os.kill(os.getpid(), signal.SIGTSTP)
        
        win.refresh()
        win.refresh()
        
        chr_in = key_redraw

    finally:
        signal.signal(signal.SIGALRM, old_sig_alrm)
        signal.signal(signal.SIGTSTP, old_sig_tstp)
        
    return chr_in

def move_player(chr_in, waiting=False, allow_kill=False):
    """Moves the player and handles collisions."""
    old_x, old_y = arena['PLAYER']['X'], arena['PLAYER']['Y']
    
    if chr_in in (key_ul, key_u, key_ur) and arena['PLAYER']['Y'] == arena['MIN_Y']: return False
    if chr_in in (key_dl, key_d, key_dr) and arena['PLAYER']['Y'] == arena['MAX_Y']: return False
    if chr_in in (key_ul, key_l, key_dl) and arena['PLAYER']['X'] == arena['MIN_X']: return False
    if chr_in in (key_ur, key_r, key_dr) and arena['PLAYER']['X'] == arena['MAX_X']: return False

    if chr_in in (key_ul, key_u, key_ur): arena['PLAYER']['Y'] -= 1
    if chr_in in (key_dl, key_d, key_dr): arena['PLAYER']['Y'] += 1
    if chr_in in (key_ul, key_l, key_dl): arena['PLAYER']['X'] -= 1
    if chr_in in (key_ur, key_r, key_dr): arena['PLAYER']['X'] += 1
    
    if arena['HEAP_AT'].get(f"{arena['PLAYER']['X']}:{arena['PLAYER']['Y']}"):
        arena['PLAYER']['X'], arena['PLAYER']['Y'] = old_x, old_y
        return False

    is_unsafe = False
    for robot in arena['ROBOTS']:
        if robot['STATUS'] == ALIVE and abs(robot['X'] - arena['PLAYER']['X']) < 2 and abs(robot['Y'] - arena['PLAYER']['Y']) < 2:
            is_unsafe = True
            break
    
    if is_unsafe:
        arena['PLAYER']['X'], arena['PLAYER']['Y'] = old_x, old_y
        return False
        
    win.addch(old_y, old_x, ' ')
    win.addch(arena['PLAYER']['Y'], arena['PLAYER']['X'], PLAYER_CHR)

    move_robots(waiting, allow_kill)
    
    if not (waiting and opts.j):
        update_score()
        win.refresh()
        
    if opts.t and not waiting and must_teleport():
        while must_teleport():
            teleport()
        return True

    return True

def move_robots(waiting, allow_kill):
    """Moves robots towards the player and handles collisions."""
    robot_at = defaultdict(list)
    
    for robot in arena['ROBOTS']:
        if robot['STATUS'] == DEAD: continue
        
        win.addch(robot['Y'], robot['X'], ' ')
        
        if arena['PLAYER']['X'] > robot['X']: robot['X'] += 1
        elif arena['PLAYER']['X'] < robot['X']: robot['X'] -= 1
        
        if arena['PLAYER']['Y'] > robot['Y']: robot['Y'] += 1
        elif arena['PLAYER']['Y'] < robot['Y']: robot['Y'] -= 1
        
        if arena['HEAP_AT'].get(f"{robot['X']}:{robot['Y']}"):
            arena['PLAYER']['SCORE'] += ROBOT_SCORE
            if waiting and allow_kill: arena['PLAYER']['BONUS'] += 1
            robot['STATUS'] = DEAD
        else:
            robot_at[f"{robot['X']}:{robot['Y']}"].append(robot)

    arena['ROBOT_AT'].clear()
    
    for coords, robots in robot_at.items():
        if len(robots) > 1:
            x, y = map(int, coords.split(':'))
            arena['HEAP_AT'][coords] = 1
            win.addch(y, x, HEAP_CHR)
            
            for robot in robots:
                arena['PLAYER']['SCORE'] += ROBOT_SCORE
                if waiting and allow_kill: arena['PLAYER']['BONUS'] += 1
                robot['STATUS'] = DEAD
        else:
            robot = robots[0]
            arena['ROBOT_AT'][coords] = 1
            win.addch(robot['Y'], robot['X'], ROBOT_CHR)

    if real_time:
        if arena['ROBOT_AT'].get(f"{arena['PLAYER']['X']}:{arena['PLAYER']['Y']}") or arena['HEAP_AT'].get(f"{arena['PLAYER']['X']}:{arena['PLAYER']['Y']}"):
            arena['PLAYER']['STATUS'] = DEAD
            return

        win.move(arena['PLAYER']['Y'], arena['PLAYER']['X'])
        win.refresh()
        signal.alarm(real_time_step)

def teleport():
    """Teleports the player to a random safe location."""
    old_x, old_y = arena['PLAYER']['X'], arena['PLAYER']['Y']
    win.addch(old_y, old_x, ' ')

    min_x, min_y = arena['MIN_X'], arena['MIN_Y']
    rng_x, rng_y = arena['MAX_X'] - min_x, arena['MAX_Y'] - min_y
    
    while True:
        x = random.randrange(rng_x) + min_x
        y = random.randrange(rng_y) + min_y
        if not arena['HEAP_AT'].get(f"{x}:{y}"):
            arena['PLAYER']['X'], arena['PLAYER']['Y'] = x, y
            break
            
    is_unsafe = False
    for robot in arena['ROBOTS']:
        if robot['STATUS'] == ALIVE and abs(robot['X'] - arena['PLAYER']['X']) < 2 and abs(robot['Y'] - arena['PLAYER']['Y']) < 2:
            is_unsafe = True
            break
            
    if is_unsafe:
        arena['PLAYER']['STATUS'] = DEAD
        return

    win.addch(arena['PLAYER']['Y'], arena['PLAYER']['X'], PLAYER_CHR)
    move_robots(False, False)
    win.move(arena['PLAYER']['Y'], arena['PLAYER']['X'])

def kill_player_wail():
    """Displays the player's death message."""
    win.addstr(arena['PLAYER']['Y'], arena['PLAYER']['X'], PLAYER_WAIL)

def kill_player():
    """Handles the player's death."""
    if real_time: signal.alarm(0)
    kill_player_wail()
    record_score()
    if new_score: show_scores_in_game()
    
    arena['PLAYER']['SCORE'] = arena['PLAYER']['BONUS'] = 0
    arena['LEVEL'] = initial_level
    
    return another_game_prompt()

def another_game_prompt():
    """Prompts the user to play another game."""
    global another_game
    
    if (pattern_roll or stand_still) and not new_score:
        clear_arena()
        clear_legend()
        starting_positions()
        draw_arena()
        return True
        
    another_game = True
    win.addstr(22, arena['MAX_X'] + 3, 'Another game?')
    win.clrtoeol()
    win.move(22, arena['MAX_X'] + 16)
    win.refresh()

    chr_in = get_command()
    another_game = False

    if chr_in.lower() != 'y':
        return False

    arena['PLAYER']['BONUS'] = arena['PLAYER']['ADV_BONUS'] = arena['PLAYER']['SCORE'] = 0
    clear_arena()
    clear_legend()
    starting_positions()
    draw_arena()
    return True

def record_score():
    """Records the player's score to the score file if it's a high score."""
    global high_scores, new_score, my_score, score_file
    
    if cheater or not score_file: return
    
    try:
        with open(score_file, 'r+') as f:
            # Lock the file
            fcntl.flock(f, fcntl.LOCK_EX)
            
            f.seek(0)
            for line in f:
                uid, score, name = line.strip().split('\t')
                high_scores[int(score)].append([int(uid), int(score), name])

            record = False
            if len(f) < MAX_SCORES:
                record = True
            else:
                for score in high_scores.keys():
                    if arena['PLAYER']['SCORE'] >= score:
                        record = True
                        break
            
            if not record:
                fcntl.flock(f, fcntl.LOCK_UN)
                return

            uid = os.getuid()
            score = arena['PLAYER']['SCORE']
            name = getpass.getuser()
            
            high_scores[score].insert(0, [uid, score, name])
            
            # Clear and rewrite the file
            f.seek(0)
            f.truncate()

            count = 0
            i = 1
            
            for score_val in sorted(high_scores.keys(), reverse=True):
                for info in high_scores[score_val]:
                    if info[0] == uid:
                        count += 1
                        if count >= MAX_SCORES_PER_USER: continue
                    
                    f.write('\t'.join(map(str, info)) + '\n')
                    if score_val == arena['PLAYER']['SCORE']:
                        my_score = info
                        new_score = True
                    
                    i += 1
                    if i > MAX_SCORES: break
                if i > MAX_SCORES: break
                
            fcntl.flock(f, fcntl.LOCK_UN)

    except IOError as e:
        sys.stderr.write(f"{score_file}: {e}; no scores will be saved\n")
        score_file = None

def show_scores():
    """Shows the high scores list and exits."""
    if win: win.endwin()
    if not score_file: return

    try:
        with open(score_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= curses.LINES: break
                print(f"{i+1}\t{line}", end='')
    except IOError as e:
        sys.stderr.write(f"{score_file}: {e}\n")
    sys.exit(0)

def show_scores_in_game():
    """Displays high scores within the game interface."""
    line = 1
    for score in sorted(high_scores.keys(), reverse=True):
        for info in high_scores[score]:
            uid, score_val, name = info
            name = f"{name:<16}"
            
            win.move(line, HIGH_SCORE_X)
            if info == my_score: win.standout()
            win.addstr(f" {line}\t{score_val}\t{name} ")
            if info == my_score: win.standend()
            
            if line >= arena['MAX_Y']: break
            line += 1
        if line >= arena['MAX_Y']: break
    win.refresh()

def clear_arena():
    """Clears the main playing area."""
    empty_str = ' ' * (arena['MAX_X'] - arena['MIN_X'] + 1)
    for line in range(1, arena['MAX_Y'] + 1):
        win.addstr(line, arena['MIN_X'], empty_str)

def clear_legend():
    """Clears the game legend area."""
    update_score()
    update_bonus()
    win.addstr(22, arena['MAX_X'] + 3, ' ' * (SIDEBAR_WIDTH - 1))

def update_score():
    """Updates the score display."""
    win.move(arena['SCORE_Y'], arena['SCORE_X'])
    win.addstr(str(arena['PLAYER']['SCORE']))
    win.clrtoeol()

def update_bonus():
    """Updates the bonus display."""
    x, y = arena['PROMPT_X'] - 1, arena['PROMPT_Y']
    
    if arena['PLAYER']['ADV_BONUS']:
        win.move(y, x)
        win.addstr(f" Advance bonus: {arena['PLAYER']['ADV_BONUS']:3d}")
        y += 1
        
    win.move(y, x)
    if arena['PLAYER']['BONUS']:
        win.addstr(f" Wait bonus: {arena['PLAYER']['BONUS']}")
        
    win.clrtoeol()

    if y < arena['PROMPT_Y'] + 1:
        win.move(y + 1, x)
        win.clrtoeol()

def redraw():
    """Redraws the entire screen."""
    win.clear()
    win.refresh()
    draw_arena()
    win.refresh()

def wait(allow_kill=False):
    """Waits for robots to collide, potentially killing the player."""
    while move_player(key_nop, waiting=True, allow_kill=allow_kill):
        if not len(arena['ROBOT_AT']): break
    
    if arena['ROBOT_AT'].get(f"{arena['PLAYER']['X']}:{arena['PLAYER']['Y']}") or arena['HEAP_AT'].get(f"{arena['PLAYER']['X']}:{arena['PLAYER']['Y']}"):
        arena['PLAYER']['STATUS'] = DEAD

def must_teleport():
    """Checks if the player is in a position where teleportation is the only safe option."""
    px, py = arena['PLAYER']['X'], arena['PLAYER']['Y']
    pos_moves = defaultdict(int)

    if pattern_roll:
        for move in move_list:
            x, y = px, py
            if move in (key_ul, key_u, key_ur): y -= 1
            if move in (key_dl, key_d, key_dr): y += 1
            if move in (key_ul, key_l, key_dl): x -= 1
            if move in (key_ur, key_r, key_dr): x += 1
            pos_moves[f"{x}:{y}"] = 1
    
    if stand_still and len(arena['ROBOT_AT']) and is_unsafe_pos(px, py):
        return True

    for x1 in range(px - 1, px + 2):
        if x1 < arena['MIN_X'] or x1 > arena['MAX_X']: continue
        for y1 in range(py - 1, py + 2):
            if y1 < arena['MIN_Y'] or y1 > arena['MAX_Y']: continue
            
            if arena['ROBOT_AT'].get(f"{x1}:{y1}") or arena['HEAP_AT'].get(f"{x1}:{y1}"): continue
            
            if pattern_roll and not pos_moves.get(f"{x1}:{y1}"): continue
            
            if not is_unsafe_pos(x1, y1):
                return False
    
    return True

def is_unsafe_pos(x, y):
    """Checks if a given position is unsafe for the player."""
    for x1 in range(x - 1, x + 2):
        if x1 < arena['MIN_X'] or x1 > arena['MAX_X']: continue
        for y1 in range(y - 1, y + 2):
            if y1 < arena['MIN_Y'] or y1 > arena['MAX_Y']: continue
            if arena['ROBOT_AT'].get(f"{x1}:{y1}"):
                return True
    return False

def quit_prompt():
    """Prompts the user to quit the game."""
    win.addstr(22, arena['MAX_X'] + 3, 'Really quit?')
    win.clrtoeol()
    win.move(22, arena['MAX_X'] + 15)

def quit_game():
    """Handles the quit command."""
    global ask_quit
    ask_quit = True
    quit_prompt()
    
    chr_in = get_command()
    ask_quit = False

    if real_time: signal.alarm(real_time_step)
    
    if chr_in.lower() == 'y': return True
    
    clear_legend()
    win.move(arena['PLAYER']['Y'], arena['PLAYER']['X'])
    return False

def main():
    """Main entry point for the script."""
    global win, opts

    opts = parse_args(sys.argv[1:])
    
    if opts.s:
        show_scores()
    
    try:
        win = curses.initscr()
        curses.cbreak()
        curses.noecho()
        
        sanity_check()
        init_arena(opts)
        starting_positions()
        draw_arena()
        
        play()
        
    finally:
        if win:
            curses.nocbreak()
            curses.echo()
            curses.endwin()

if __name__ == "__main__":
    main()
