#!/usr/bin/env python3

"""
Name: ching
Description: the Book of Changes
Author: Albert Dvornik, bert@genscan.com
License: bsd
"""

import sys
import os
import re
import random
import subprocess
from pathlib import Path

# Traditional numeric values for the lines
# 6 --- "old yin": broken (yin) moving to solid (yang)
# 7 --- "young yang": solid (yang)
# 8 --- "young yin": broken (yin)
# 9 --- "old yang": solid (yang) moving to broken (yin)

# Traditional ordering of the hexagrams
hex_lines = [
    '777777', '888888', '788878', '878887', '777878', '878777', '878888', '888878',
    '777877', '778777', '777888', '888777', '787777', '777787', '887888', '888788',
    '788778', '877887', '778888', '888877', '788787', '787887', '888887', '788888',
    '788777', '777887', '788887', '877778', '878878', '787787', '887778', '877788',
    '887777', '777788', '888787', '787888', '787877', '778787', '887878', '878788',
    '778887', '788877', '777778', '877777', '888778', '877888', '878778', '877878',
    '787778', '877787', '788788', '887887', '887877', '778788', '787788', '887787',
    '877877', '778778', '878877', '778878', '778877', '887788', '787878', '878787',
]

hexagram_map = {lines: i + 1 for i, lines in enumerate(hex_lines)}

def usage():
    """Prints usage message and exits."""
    sys.stderr.write("usage: ching [-nrh] [-p pager] [hexagram-lines]\n")
    sys.exit(1)

def ask_and_toss():
    """Simulates coin tosses to generate a hexagram line string."""
    question_hash = sum(ord(c) for c in os.environ.get('CHING_QUESTION', ''))
    random.seed(int(time.time()) + (31 * question_hash) + os.getuid() + os.getgid() + os.getpid())

    hexagram_lines = ""
    for _ in range(6):
        line_value = 6
        for _ in range(3):
            line_value += random.randint(0, 1)
        hexagram_lines += str(line_value)
    return hexagram_lines

def first_hex(change):
    """Gets the first hexagram number from a change line string."""
    return hexagram_map.get(change.replace('6', '8').replace('9', '7'))

def second_hex(change):
    """Gets the second hexagram number from a change line string."""
    return hexagram_map.get(change.replace('6', '7').replace('9', '8'))

def hexagram(change, data_lines):
    """
    Extracts and formats the hexagram text from the data block.
    """
    hex1 = first_hex(change)
    hex2 = second_hex(change)
    
    macros = get_macros(data_lines)
    
    text1, text2 = '', ''
    
    # Read text for hexagrams.
    for i in range(2):
        hex_num_to_find = hex1 if i == 0 else hex2
        
        while data_lines and not re.match(fr'^\.H\s+({hex_num_to_find})\s', data_lines[0]):
            data_lines.pop(0)

        if not data_lines:
            raise ValueError(f"ching: Hexagram {hex_num_to_find} missing!")
        
        if data_lines[0].split()[1] == str(hex1):
            text1 = get_hex_body(change, hex1, data_lines)
        else:
            text2 = get_hex_body('', hex2, data_lines)
            
    if hex1 == hex2:
        return macros, text1
    
    if not text1 or not text2:
        raise ValueError("ching: Hexagram text was repeated!")
    
    return macros, text1, text2

def get_hex_body(change, hex_num, data_lines):
    """Parses and formats a hexagram's body text."""
    body = []
    
    # Header
    match = re.match(r'^\.H (\d+) "(.*?)" "(.*?)"', data_lines.pop(0))
    if not match or int(match.group(1)) != hex_num:
        raise ValueError(f"ching: Hexagram header (.H) is corrupt for hexagram {hex_num}")
    body.append(handle_hex(match.group(1), match.group(2), match.group(3)))
    
    # Trigrams
    match = re.match(r'^\.X (\d+) (\d+)', data_lines.pop(0))
    if not match:
        raise ValueError(f"ching: Trigrams (.X) are missing for hexagram {hex_num}")
    body.append(handle_trigrams(match.group(1), match.group(2)))

    # Judgement
    if not re.match(r'^\.J$', data_lines.pop(0)):
        raise ValueError(f"ching: Judgement (.J) is missing for hexagram {hex_num}")
    judgement_lines = []
    while data_lines and not data_lines[0].startswith('.'):
        judgement_lines.append(data_lines.pop(0).strip())
    body.append(handle_judgement(judgement_lines))
    
    # Image
    if not re.match(r'^\.I$', data_lines.pop(0)):
        raise ValueError(f"ching: Image (.I) is missing for hexagram {hex_num}")
    image_lines = []
    while data_lines and not data_lines[0].startswith('.'):
        image_lines.append(data_lines.pop(0).strip())
    body.append(handle_image(image_lines))
    
    return "".join(body)

def get_macros(data_lines):
    """Extracts macro definitions from the data block."""
    macros = []
    while data_lines:
        line = data_lines.pop(0)
        if re.match(r'^__HEXAGRAM_TEXT__', line):
            break
        macros.append(line)
    return "".join(macros)

def handle_hex(num, chinese, local):
    """Formats the hexagram header."""
    return f"\n      {num}.  {chinese} / {local}\n\n"

def handle_trigrams(top, bot):
    """Formats the trigrams."""
    trigram_names = {
        '1': 'The Creative, Heaven', '2': 'The Gentle, Wind', '3': 'The Clinging, Flame',
        '4': 'Keeping Still, Mountain', '5': 'The Joyous, Lake', '6': 'The Abysmal, Water',
        '7': 'The Arousing, Thunder', '8': 'The Receptive, Earth',
    }
    top_name = trigram_names.get(top)
    bot_name = trigram_names.get(bot)
    return f"      Trigrams: Above - {top_name}, Below - {bot_name}\n"

def handle_judgement(lines):
    """Formats the judgement block."""
    return f"\n      The Judgement\n\n      {' '.join(lines)}\n\n"

def handle_image(lines):
    """Formats the image block."""
    return f"\n      The Image\n\n      {' '.join(lines)}\n\n"

# Command line parsing and main execution logic
def main():
    """Main function to run the ching oracle."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-n', action='store_true', help='Pipe to nroff.')
    parser.add_argument('-r', action='store_true', help='Spew roff commands.')
    parser.add_argument('-h', action='store_true', help='Show hexagram lines.')
    parser.add_argument('-p', type=str, help='Pager command.')
    parser.add_argument('hex_lines', nargs='?', default=None, help='Hexagram line values.')
    
    args = parser.parse_args()

    if args.hex_lines:
        if not re.fullmatch(r'[6789]{6}', args.hex_lines):
            usage()
        change = args.hex_lines
    else:
        change = ask_and_toss()

    if args.h:
        print(change)
        sys.exit(0)

    # Read the data block from the script file
    script_path = Path(__file__)
    with open(script_path, 'r') as f:
        data_block = f.read()
    
    # Find the start of the hexagram text
    hex_text_start = re.search(r'__HEXAGRAM_TEXT__', data_block).end()
    hexagram_text = data_block[hex_text_start:].strip().splitlines()

    try:
        macros, *hex_texts = hexagram(change, hexagram_text)
        
        if args.n or args.r:
            # Re-assemble the roff macros and hexagram text
            output = macros + "".join(hex_texts)
        else:
            # Simple text formatting
            output = "".join(hex_texts)

        if args.n and shutil.which('nroff'):
            p = subprocess.Popen(['nroff', '-'], stdin=subprocess.PIPE, text=True)
            p.communicate(output)
        elif args.p:
            p = subprocess.Popen(args.p.split(), stdin=subprocess.PIPE, text=True)
            p.communicate(output)
        else:
            print(output)
            
    except (ValueError, IndexError) as e:
        sys.stderr.write(f"ching: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
