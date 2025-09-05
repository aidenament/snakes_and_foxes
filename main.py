#!/usr/bin/env python3
"""
Snakes and Foxes Game - Main Entry Point

This game implements a board with concentric circles where players start at the center,
need to reach the outer circle, and then return to the center to win.
"""
import pygame
import sys
import argparse
from game import Game
from pygame_utils import init_pygame_no_audio

def parse_arguments():
    """
    Parse command line arguments for customizing the game.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Snakes and Foxes Game')
    parser.add_argument('--circles', type=int, default=6,
                        help='Number of concentric circles on the board (default: 6)')
    parser.add_argument('--nodes', type=int, default=10,
                        help='Number of nodes per circle (default: 10)')
    
    return parser.parse_args()

def main():
    """
    Main function to initialize and run the game.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Initialize pygame modules individually to avoid audio/ALSA errors
    init_pygame_no_audio()
    
    # Create game instance with customizable parameters
    game = Game(num_circles=args.circles, nodes_per_circle=args.nodes)
    
    # Create a clock for controlling frame rate
    clock = pygame.time.Clock()
    
    # Main game loop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Handle game events
            game.handle_event(event)
        
        # Update game state
        game.update()
        
        # Render the game
        game.render()
        
        # Update the display
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(60)

if __name__ == "__main__":
    main()
