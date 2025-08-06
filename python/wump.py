#!/usr/bin/env python3
"""
Name: wump
Description: play a game of "Hunt the Wumpus"
Author: Amir Karger, karger@post.harvard.edu (Original Perl Author)
License: perl
"""

import sys
import random
import textwrap

# --- Constants and Game Data ---

INSTRUCTIONS = """
WELCOME TO 'HUNT THE WUMPUS'
THE WUMPUS LIVES IN A CAVE OF 20 ROOMS. EACH ROOM
HAS 3 TUNNELS LEADING TO OTHER ROOMS. (LOOK AT A
DODECAHEDRON TO SEE HOW THIS WORKS-IF YOU DON'T KNOW
WHAT A DODECAHEDRON IS, ASK SOMEONE)

  HAZARDS:
  BOTTOMLESS PITS - TWO ROOMS HAVE BOTTOMLESS PITS IN THEM
  IF YOU GO THERE, YOU FALL INTO THE PIT (& LOSE!)
  SUPER BATS - TWO OTHER ROOMS HAVE SUPER BATS. IF YOU
  GO THERE, A BAT GRABS YOU AND TAKES YOU TO SOME OTHER
  ROOM AT RANDOM. (WHICH MAY BE TROUBLESOME)

PRESS <ENTER> TO CONTINUE
"""

INSTRUCTIONS_PART_2 = """
  WUMPUS:
  THE WUMPUS IS NOT BOTHERED BY HAZARDS (HE HAS SUCKER
  FEET AND IS TOO BIG FOR A BAT TO LIFT). USUALLY
  HE IS ASLEEP. TWO THINGS WAKE HIM UP: YOU SHOOTING AN
  ARROW OR YOU ENTERING HIS ROOM.
  IF THE WUMPUS WAKES HE MOVES (P=.75) ONE ROOM
  OR STAYS STILL (P=.25). AFTER THAT, IF HE IS WHERE YOU
  ARE, HE EATS YOU UP AND YOU LOSE!

  YOU:
  EACH TURN YOU MAY MOVE OR SHOOT A CROOKED ARROW
  MOVING: YOU CAN MOVE ONE ROOM (THRU ONE TUNNEL)
  ARROWS: YOU HAVE 5 ARROWS. YOU LOSE WHEN YOU RUN OUT.
  EACH ARROW CAN GO FROM 1 TO 5 ROOMS. YOU AIM BY
  TELLING THE COMPUTER THE ROOM#S YOU WANT THE ARROW TO GO TO.
  IF THE ARROW CAN'T GO THAT WAY (I.E. NO TUNNEL) IT MOVES
  AT RANDOM TO THE NEXT ROOM.
  IF THE ARROW HITS THE WUMPUS, YOU WIN.
  IF THE ARROW HITS YOU, YOU LOSE.

PRESS <ENTER> TO CONTINUE
"""

INSTRUCTIONS_PART_3 = """
  WARNINGS:
  WHEN YOU ARE ONE ROOM AWAY FROM A WUMPUS OR HAZARD,
  THE COMPUTER SAYS:
  WUMPUS:  'I SMELL A WUMPUS'
  BAT   :  'BATS NEARBY'
  PIT   :  'I FEEL A DRAFT'
"""

# The cave is a dodecahedron. This list represents the connections.
# CAVE[room_num] -> [connected_room_1, connected_room_2, connected_room_3]
CAVE_MAP = [
    [], # Index 0 is unused
    [2, 5, 8], [1, 3, 10], [2, 4, 12], [3, 5, 14], [1, 4, 6],
    [5, 7, 15], [6, 8, 17], [1, 7, 9], [8, 10, 18], [2, 9, 11],
    [11, 12, 19], [3, 11, 13], [12, 14, 20], [4, 13, 15], [6, 14, 16],
    [15, 17, 20], [7, 16, 18], [9, 17, 19], [11, 18, 20], [13, 16, 19]
]

class WumpusGame:
    """Manages the state and logic for a game of Hunt the Wumpus."""
    def __init__(self):
        self.locations = {} # 'player', 'wumpus', 'pit1', 'pit2', 'bat1', 'bat2'
        self.initial_locations = {}
        self.arrows = 5
        self.game_over = False
        self.message = ""

    def setup_cave(self, reuse_setup=False):
        """Places the player, wumpus, and hazards in the cave."""
        if reuse_setup and self.initial_locations:
            self.locations = self.initial_locations.copy()
        else:
            # Generate unique random locations for all items.
            rooms = random.sample(range(1, 21), k=6)
            self.locations = {
                'player': rooms[0],
                'wumpus': rooms[1],
                'pit1':   rooms[2],
                'pit2':   rooms[3],
                'bat1':   rooms[4],
                'bat2':   rooms[5],
            }
            self.initial_locations = self.locations.copy()
        
        self.arrows = 5
        self.game_over = False

    def play(self):
        """Runs the main game loop."""
        print("\nHUNT THE WUMPUS")
        while not self.game_over:
            self.print_status_and_warnings()
            self.handle_player_action()
            self.check_hazards()
        
        # After game over, print the final message
        print(self.message)

    def print_status_and_warnings(self):
        """Prints the player's current location and any hazard warnings."""
        player_loc = self.locations['player']
        neighbors = CAVE_MAP[player_loc]
        
        print()
        # Check neighbors for hazards
        if self.locations['wumpus'] in neighbors: print("I SMELL A WUMPUS!")
        if self.locations['pit1'] in neighbors or self.locations['pit2'] in neighbors: print("I FEEL A DRAFT")
        if self.locations['bat1'] in neighbors or self.locations['bat2'] in neighbors: print("BATS NEARBY!")
            
        print(f"YOU ARE IN ROOM {player_loc}")
        print(f"TUNNELS LEAD TO {' '.join(map(str, neighbors))}\n")

    def handle_player_action(self):
        """Asks the player to shoot or move and processes the action."""
        while True:
            try:
                action = input("SHOOT OR MOVE (S-M)? ").upper()
                if action == 'S':
                    self._handle_shoot()
                    return
                elif action == 'M':
                    self._handle_move()
                    return
            except (EOFError, KeyboardInterrupt):
                sys.exit("\nExiting.")

    def _handle_move(self):
        """Handles the player's move action."""
        player_loc = self.locations['player']
        neighbors = CAVE_MAP[player_loc]

        while True:
            try:
                dest_str = input("WHERE TO? ")
                if not dest_str.isdigit(): continue
                destination = int(dest_str)
                if destination in neighbors:
                    self.locations['player'] = destination
                    return
                else:
                    print("NOT POSSIBLE -")
            except (EOFError, KeyboardInterrupt):
                sys.exit("\nExiting.")
    
    def _handle_shoot(self):
        """Handles the player's shoot action."""
        path = []
        try:
            num_rooms = int(input("NO. OF ROOMS (1-5)? "))
            if not 1 <= num_rooms <= 5: return

            for i in range(num_rooms):
                room = int(input(f"ROOM #{i+1}? "))
                path.append(room)
        except (ValueError, EOFError, KeyboardInterrupt):
            return # Invalid input ends the turn

        self.arrows -= 1
        arrow_loc = self.locations['player']

        for room in path:
            # Check if there is a valid tunnel
            if room in CAVE_MAP[arrow_loc]:
                arrow_loc = room
            else:
                # If not, arrow moves to a random adjacent room
                arrow_loc = random.choice(CAVE_MAP[arrow_loc])
            
            # Check for hits
            if arrow_loc == self.locations['wumpus']:
                self.message = "AHA! YOU GOT THE WUMPUS!\nHEE HEE HEE - THE WUMPUS'LL GET YOU NEXT TIME!!"
                self.game_over = True
                return
            if arrow_loc == self.locations['player']:
                self.message = "OUCH! ARROW GOT YOU!\nHA HA HA - YOU LOSE!"
                self.game_over = True
                return
        
        # If the loop finishes, it's a miss
        print("MISSED")
        self._move_wumpus() # A shot wakes the wumpus
        if self.arrows == 0:
            self.message = "YOU RAN OUT OF ARROWS.\nHA HA HA - YOU LOSE!"
            self.game_over = True

    def _move_wumpus(self):
        """Moves the wumpus to an adjacent room (or stays put)."""
        # 75% chance to move to a random adjacent room, 25% to stay.
        new_loc = random.choice(CAVE_MAP[self.locations['wumpus']] + [self.locations['wumpus']])
        self.locations['wumpus'] = new_loc

    def check_hazards(self):
        """Checks for hazards in the player's new location and resolves them."""
        while True: # Loop to handle bats moving the player into another hazard
            player_loc = self.locations['player']

            if player_loc == self.locations['wumpus']:
                print("... OOPS! BUMPED A WUMPUS!")
                self._move_wumpus()
                # Check if the wumpus moved into our room
                if self.locations['player'] == self.locations['wumpus']:
                    self.message = "TSK TSK TSK - WUMPUS GOT YOU!\nHA HA HA - YOU LOSE!"
                    self.game_over = True
                return

            if player_loc in (self.locations['pit1'], self.locations['pit2']):
                self.message = "YYYYIIIIEEEE . . . FELL IN PIT\nHA HA HA - YOU LOSE!"
                self.game_over = True
                return

            if player_loc in (self.locations['bat1'], self.locations['bat2']):
                print("ZAP--SUPER BAT SNATCH! ELSEWHEREVILLE FOR YOU!")
                self.locations['player'] = random.randint(1, 20)
                continue # Re-run hazard checks in the new location
            
            break # No hazards in this location

def main():
    """Main function to control the game and "play again" loop."""
    try:
        show_instructions = input("INSTRUCTIONS (Y-N)? ").upper()
        if show_instructions != 'N':
            print(INSTRUCTIONS)
            input()
            print(INSTRUCTIONS_PART_2)
            input()
            print(INSTRUCTIONS_PART_3)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    game = WumpusGame()
    reuse_setup = False
    
    while True:
        game.setup_cave(reuse_setup)
        game.play()
        
        try:
            play_again = input("\nSAME SETUP (Y-N)? ").upper()
            if play_again == 'Y':
                reuse_setup = True
            else:
                reuse_setup = False
        except (EOFError, KeyboardInterrupt):
            break

if __name__ == "__main__":
    main()
