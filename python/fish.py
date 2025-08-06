#!/usr/bin/env python3
"""
Name: fish
Description: plays the children's game of Go Fish
Author: Clinton Pierce, clintp@geeksalad.org (Original Perl Author)
License: perl
"""

import sys
import random
import argparse
from collections import Counter

# --- Constants ---
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
INSTRUCTIONS = """
This is the traditional children's card game "Go Fish".
The object is to collect more "books" (all four cards of a single rank)
than your opponent.

On your turn, you ask the computer for a card rank (e.g., "A", "7", "K").
You must have at least one card of that rank in your own hand to ask for it.

- If the computer has any cards of that rank, you get them all, and you go again.
- If the computer has none, they will say "GO FISH!", and you draw from the deck.
- If you draw the card you asked for, you get to go again.
- Otherwise, your turn ends.

Special commands during your turn:
- Press ENTER without typing a rank to see the game status.
- Type 'p' to toggle the computer's "professional" (smarter) mode.
- Type 'quit' to end the game.

The game ends when the deck is empty or a player runs out of cards.
Good luck!
"""

class Deck:
    """Represents the deck of cards."""
    def __init__(self):
        # A standard deck has 4 of each rank.
        self.cards = RANKS * 4
        random.shuffle(self.cards)

    def draw(self):
        """Draws a single card from the deck."""
        return self.cards.pop() if self.cards else None

class Player:
    """Represents a player in the game."""
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.books = set()

    def add_cards(self, cards):
        """Adds one or more cards to the player's hand."""
        if isinstance(cards, list):
            self.hand.extend(cards)
        else:
            self.hand.append(cards)
        self.check_for_books()

    def has_rank(self, rank):
        """Checks if the player has a card of the given rank."""
        return rank in self.hand

    def give_cards(self, rank):
        """Gives all cards of a certain rank to the opponent."""
        cards_to_give = [card for card in self.hand if card == rank]
        self.hand = [card for card in self.hand if card != rank]
        return cards_to_give

    def check_for_books(self):
        """Checks the hand for any completed books and moves them aside."""
        counts = Counter(self.hand)
        for rank, count in counts.items():
            if count == 4:
                self.books.add(rank)
                self.hand = [card for card in self.hand if card != rank]
                print(f"--- {self.name} made a book of {rank}s! ---")


class Game:
    """Manages the overall game flow and state."""
    def __init__(self, is_professional_mode=False):
        self.deck = Deck()
        self.human = Player("You")
        self.computer = Player("I")
        self.professional_mode = is_professional_mode
        self.human_ask_history = [] # For the computer's "memory"

    def deal_initial_hands(self):
        """Deals 7 cards to each player to start the game."""
        for _ in range(7):
            self.human.add_cards(self.deck.draw())
            self.computer.add_cards(self.deck.draw())
        print("Initial hands have been dealt.")

    def play(self):
        """Starts and runs the main game loop."""
        self.deal_initial_hands()
        
        # Randomly choose who starts
        turn = random.choice([self.human, self.computer])
        print(f"\n{turn.name} get to start.")

        while self.human.hand and self.computer.hand:
            print("-" * 20)
            print(f"It's {turn.name}r turn.")
            self.print_status(show_computer_hand=False)
            
            go_again = True
            while go_again:
                if not turn.hand: break

                rank_to_ask = self.get_player_ask(turn)

                if turn is self.human:
                    opponent = self.computer
                else:
                    opponent = self.human

                print(f"{turn.name} ask {opponent.name} for: {rank_to_ask}")
                
                if opponent.has_rank(rank_to_ask):
                    cards_won = opponent.give_cards(rank_to_ask)
                    print(f"{opponent.name} had {len(cards_won)} {rank_to_ask}s.")
                    turn.add_cards(cards_won)
                    go_again = True # Player gets to go again
                else:
                    print(f"{opponent.name} say \"GO FISH!\"")
                    drawn_card = self.deck.draw()
                    if drawn_card:
                        print(f"{turn.name} drew a card.")
                        turn.add_cards(drawn_card)
                        if drawn_card == rank_to_ask:
                            print(f"{turn.name} drew the card they asked for and get to go again!")
                            go_again = True
                        else:
                            go_again = False
                    else:
                        print("The deck is empty!")
                        go_again = False
            
            # Switch turns
            turn = self.computer if turn is self.human else self.human
        
        self.end_game()

    def get_player_ask(self, player):
        """Gets the rank the current player will ask for."""
        while True:
            if player is self.human:
                try:
                    ask = input("You ask me for: ").upper()
                except (EOFError, KeyboardInterrupt):
                    sys.exit("\nGame ended.")
                
                # Handle special commands
                if ask == 'QUIT': sys.exit("Game ended.")
                if ask == 'P':
                    self.professional_mode = not self.professional_mode
                    print(f"{'Entering' if self.professional_mode else 'Leaving'} professional mode.")
                    continue
                if ask == '':
                    self.print_status(show_computer_hand=True)
                    continue

                if ask not in RANKS:
                    print("That's not a valid rank! (A, 2-10, J, Q, K)")
                elif not player.has_rank(ask):
                    print(f"You don't have any {ask}s!")
                else:
                    self.human_ask_history.append(ask)
                    return ask
            else: # Computer's turn
                if not self.professional_mode:
                    # Simple AI: ask for a random rank they have.
                    return random.choice(list(set(self.computer.hand)))
                else:
                    # Professional AI: use memory
                    for rank in reversed(self.human_ask_history):
                        if self.computer.has_rank(rank):
                            return rank
                    # Fallback to simple AI if memory is empty
                    return random.choice(list(set(self.computer.hand)))

    def print_status(self, show_computer_hand=False):
        """Prints the current game status."""
        print(f"\nYour hand: {' '.join(sorted(self.human.hand))}", end='')
        if self.human.books: print(f" + Books: {' '.join(sorted(list(self.human.books)))}", end='')
        print()
        
        if show_computer_hand:
            print(f"My hand: {' '.join(sorted(self.computer.hand))}", end='')
            if self.computer.books: print(f" + Books: {' '.join(sorted(list(self.computer.books)))}", end='')
            print()
            
        print(f"Cards left in deck: {len(self.deck.cards)}")

    def end_game(self):
        """Declares the winner at the end of the game."""
        print("\n" + "="*20)
        print("GAME OVER")
        print(f"Your books: {len(self.human.books)} ({' '.join(sorted(list(self.human.books)))})")
        print(f"My books: {len(self.computer.books)} ({' '.join(sorted(list(self.computer.books)))})")
        
        if len(self.human.books) > len(self.computer.books):
            print("You win! 🥳")
        elif len(self.computer.books) > len(self.human.books):
            print("I win! 🤖")
        else:
            print("It's a tie!")

def main():
    """Parses arguments and starts the game."""
    parser = argparse.ArgumentParser(description="Play the card game Go Fish.")
    parser.add_argument('-p', '--professional', action='store_true',
                        help='Enable professional (smarter) computer AI.')
    args = parser.parse_args()
    
    try:
        show_instructions = input("Do you want to see instructions (y/n)? ")
        if show_instructions.lower().startswith('y'):
            print(INSTRUCTIONS)
            input("Press <ENTER> to continue...")
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    game = Game(is_professional_mode=args.professional)
    game.play()

if __name__ == "__main__":
    main()
