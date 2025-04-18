"""
Game Engine for Snakes and Foxes
"""
import pygame
import math
from typing import Optional, Tuple, List
from board import Board, BoardNode
from player import Player
from dice import Dice, FaceType

class Game:
    """
    Main game class that manages the game state, logic, and rendering.
    
    This class coordinates all game components and handles the game loop.
    """
    
    def __init__(self, num_circles: int = 6, nodes_per_circle: int = 10):
        """
        Initialize the game with all necessary components.
        
        Args:
            num_circles: Number of concentric circles on the board
            nodes_per_circle: Number of nodes per circle
        """
        # Set up the display
        self.width = 1800  # 50% wider (1200 * 1.5 = 1800)
        self.height = 1000  # Increased height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Snakes and Foxes")
        
        # Initialize game components
        self.board = Board(num_circles=num_circles, nodes_per_circle=nodes_per_circle)
        self.player1 = Player(self.board, player_num=1)  # White player
        self.player2 = Player(self.board, player_num=2)  # Black player
        self.current_player = self.player1  # Start with player 1
        self.dice = Dice()
        
        # Initialize player pieces list in the board
        self.update_player_pieces()
        
        # Game state variables
        self.max_turns = 100
        self.game_over = False
        self.winner = None
        self.dice_rolled = False
        self.selected_move = None
        self.moves_remaining = 0  # Number of moves remaining after dice roll
        
        # Fox and snake movement variables
        self.fox_movement_active = False
        self.snake_movement_active = False
        self.fox_movement_timer = 0
        self.snake_movement_timer = 0
        self.movement_delay = 50  # Frames between movements (increased from 30 to 90)
        self.foxes_to_move = []  # List of foxes to move (in order)
        self.snakes_to_move = []  # List of snakes to move (in order)
        self.current_fox_index = 0  # Index of the current fox being moved
        self.current_snake_index = 0  # Index of the current snake being moved
        
        # Turn tracking
        self.current_turn = "White"  # "White", "Black", "Foxes", or "Snakes"
        
        # UI elements
        self.font = pygame.font.SysFont(None, 36)
        
    def handle_event(self, event):
        """
        Handle pygame events.
        
        Args:
            event: The pygame event to handle.
        """
        if self.game_over:
            # If game is over, only handle restart
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_game()
            return
        
        # Handle dice roll
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and not self.dice_rolled:
            self.roll_dice()
            self.dice_rolled = True
        
        # Handle player move after dice roll
        if self.dice_rolled and event.type == pygame.MOUSEBUTTONDOWN and not self.current_player.is_moving:
            mouse_pos = pygame.mouse.get_pos()
            selected_node = self.get_node_at_position(mouse_pos)
            
            if selected_node in self.current_player.valid_moves:
                self.move_player(selected_node)
                
                # Decrement moves remaining
                self.moves_remaining -= 1
                
                # Check game conditions after each move
                self.check_game_conditions()
                
                # If game is over, don't continue
                if self.game_over:
                    self.dice_rolled = False
                    return
                
                # If no more moves remaining, activate fox movement
                if self.moves_remaining <= 0:
                    # Activate fox movement if there are red triangles
                    if self.red_triangles > 0:
                        self.activate_fox_movement()
                    elif self.green_squiggles > 0:
                        # No red triangles but green squiggles, activate snake movement
                        self.activate_snake_movement()
                    else:
                        # No red triangles or green squiggles, switch to the other player
                        self.dice_rolled = False
                        self.switch_player()
    
    def get_node_at_position(self, pos: Tuple[int, int]) -> Optional[BoardNode]:
        """
        Get the node at the given screen position.
        
        Args:
            pos: The (x, y) screen coordinates
            
        Returns:
            The node at the position, or None if no node is there
        """
        x, y = pos
        
        # First check the center node (special case)
        center_node = self.board.center_node
        center_x, center_y = center_node.get_position()
        distance = math.sqrt((center_x - x) ** 2 + (center_y - y) ** 2)
        if distance <= self.board.center_node_radius:
            return center_node
        
        # Check all other nodes
        for circle_idx in range(1, self.board.num_circles):  # Start from circle 1 (not center)
            for node in self.board.nodes[circle_idx]:
                node_x, node_y = node.get_position()
                
                # Calculate distance from click to node center
                distance = math.sqrt((node_x - x) ** 2 + (node_y - y) ** 2)
                
                # If click is within node radius, return this node
                if distance <= self.board.node_radius:
                    return node
        
        return None
    
    def switch_player(self):
        """Switch to the other player."""
        if self.current_player == self.player1:
            # Switch to player 2 only if they are active
            if self.player2.active:
                self.current_player = self.player2
                self.current_turn = "Black"
            # If player 2 is not active, stay with player 1
        else:
            # Switch to player 1 only if they are active
            if self.player1.active:
                self.current_player = self.player1
                self.current_turn = "White"
            # If player 1 is not active, stay with player 2
        
        # Update player pieces list in the board
        self.update_player_pieces()
    
    def roll_dice(self):
        """Roll all six dice at once."""
        dice_values = self.dice.roll()
        
        # Count the number of each face type
        self.black_pips = dice_values.count(FaceType.BLACK_PIP)
        self.red_triangles = dice_values.count(FaceType.RED_TRIANGLE)
        self.green_squiggles = dice_values.count(FaceType.GREEN_SQUIGGLE)
        
        # Store the black pip count as the number of moves the player can make
        self.moves_remaining = self.black_pips
        
        # If no black pips are rolled, player doesn't get to move
        if self.black_pips == 0:
            # Set a flag to show a message before switching
            self.show_no_pips_message = True
            self.message_timer = 60  # Show message for 60 frames (about 1 second)
            
            # We'll switch players in the update method after showing the message
        else:
            # Get all connected nodes as valid moves
            self.current_player.get_connected_nodes()
    
    def update_player_pieces(self):
        """Update the player pieces list in the board."""
        # Clear the current list
        self.board.player_pieces = []
        
        # Add active player pieces
        if self.player1.active:
            self.board.player_pieces.append(self.player1.current_node)
        if self.player2.active:
            self.board.player_pieces.append(self.player2.current_node)
            
        # Check if both players are inactive (all pieces captured)
        if not self.player1.active and not self.player2.active:
            self.game_over = True
            self.winner = None  # No winner (both players lost)
    
    def move_player(self, target_node: BoardNode):
        """
        Move the player to the target node.
        
        Args:
            target_node: The node to move to
        """
        self.current_player.move_to_node(target_node)
        
        # Update player pieces list in the board
        self.update_player_pieces()
        
        # We'll update valid moves after the animation completes in the player's update method
    
    def check_game_conditions(self):
        """Check if the game has been won or lost."""
        # Check win condition - player reached the center after visiting outer circle
        if self.current_player.can_win():
            self.game_over = True
            self.winner = self.current_player
        
        # Check lose condition - exceeded max turns
        total_turns = self.player1.turn_count + self.player2.turn_count
        if total_turns >= self.max_turns:
            self.game_over = True
            self.winner = None
    
    def reset_game(self):
        """Reset the game to its initial state."""
        self.player1.reset()
        self.player2.reset()
        self.current_player = self.player1  # Start with player 1
        self.game_over = False
        self.winner = None
        self.dice_rolled = False
        self.selected_move = None
        self.moves_remaining = 0  # Reset moves remaining
        
        # Reset dice-related variables
        if hasattr(self, 'black_pips'):
            self.black_pips = 0
        if hasattr(self, 'red_triangles'):
            self.red_triangles = 0
        if hasattr(self, 'green_squiggles'):
            self.green_squiggles = 0
        
        # Reset fox and snake movement variables
        self.fox_movement_active = False
        self.snake_movement_active = False
        self.fox_movement_timer = 0
        self.snake_movement_timer = 0
        self.foxes_to_move = []
        self.snakes_to_move = []
        self.current_fox_index = 0
        self.current_snake_index = 0
        
        # Reset turn tracking
        self.current_turn = "White"
        
        # Reset message flags
        if hasattr(self, 'show_no_pips_message'):
            self.show_no_pips_message = False
        if hasattr(self, 'show_capture_message'):
            self.show_capture_message = False
        
        # Reset snakes and foxes to their initial positions
        self.board.fox_pieces = []
        self.board.snake_pieces = []
        self.board._setup_fox_pieces()
        self.board._setup_snake_pieces()
        
        # Update player pieces list in the board
        self.update_player_pieces()
    
    def activate_fox_movement(self):
        """Activate fox movement toward the current player."""
        # Find the closest foxes to the current player
        self.foxes_to_move = self.board.find_closest_foxes(self.current_player.current_node)
        
        # Limit the number of foxes to move based on the number of red triangles rolled
        self.foxes_to_move = self.foxes_to_move[:self.red_triangles]
        
        if self.foxes_to_move:
            self.fox_movement_active = True
            self.fox_movement_timer = self.movement_delay
            self.current_fox_index = 0
            self.current_turn = "Foxes"
        else:
            # No foxes to move, check if we should activate snake movement
            if self.green_squiggles > 0:
                self.activate_snake_movement()
            else:
                # No foxes or snakes to move, switch to the other player
                self.dice_rolled = False
                self.switch_player()
    
    def activate_snake_movement(self):
        """Activate snake movement toward the current player."""
        # Find the closest snakes to the current player
        self.snakes_to_move = self.board.find_closest_snakes(self.current_player.current_node)
        
        # Limit the number of snakes to move based on the number of green squiggles rolled
        self.snakes_to_move = self.snakes_to_move[:self.green_squiggles]
        
        if self.snakes_to_move:
            self.snake_movement_active = True
            self.snake_movement_timer = self.movement_delay
            self.current_snake_index = 0
            self.current_turn = "Snakes"
        else:
            # No snakes to move, switch to the other player
            self.dice_rolled = False
            self.switch_player()
    
    def move_next_fox(self):
        """Move the next fox in the queue toward the current player."""
        if self.current_fox_index < len(self.foxes_to_move):
            fox_node = self.foxes_to_move[self.current_fox_index]
            
            # Store the player's current position before moving the fox
            player_node = self.current_player.current_node
            
            # Move the fox toward the player
            new_fox_node = self.board.move_fox_toward_player(fox_node, player_node)
            
            # Check if the fox landed on the player
            if (new_fox_node.x == player_node.x and 
                new_fox_node.y == player_node.y):
                # Fox captured a player piece
                all_pieces_lost = self.current_player.lose_piece()
                
                # Update player pieces list in the board
                self.update_player_pieces()
                
                # Display a message about the capture
                self.show_capture_message = True
                self.capture_message = f"{self.current_turn} captured a {self.current_player.player_num} piece!"
                self.message_timer = 45  # Show message for 90 frames (about 1.5 seconds)
                
                # If all pieces are lost, player loses
                if all_pieces_lost:
                    self.game_over = True
                    self.winner = None  # No winner (player lost)
            
            # Check if the fox landed on the center node
            elif new_fox_node == self.board.center_node:
                # Fox captures all players on the center node
                players_captured = False
                
                # Check if player 1 is on the center node
                if self.player1.active and self.player1.current_node == self.board.center_node:
                    all_pieces_lost_p1 = self.player1.lose_piece()
                    players_captured = True
                    
                    # Display a message about the capture
                    self.show_capture_message = True
                    self.capture_message = f"{self.current_turn} captured a 1 piece in the center!"
                    self.message_timer = 45  # Show message for 90 frames (about 1.5 seconds)
                    
                    # If all pieces are lost, player loses
                    if all_pieces_lost_p1 and self.current_player == self.player1:
                        self.game_over = True
                        self.winner = None  # No winner (player lost)
                
                # Check if player 2 is on the center node
                if self.player2.active and self.player2.current_node == self.board.center_node:
                    all_pieces_lost_p2 = self.player2.lose_piece()
                    players_captured = True
                    
                    # Display a message about the capture
                    self.show_capture_message = True
                    self.capture_message = f"{self.current_turn} captured a 2 piece in the center!"
                    self.message_timer = 45  # Show message for 45 frames (about 1.5 seconds)
                    
                    # If all pieces are lost, player loses
                    if all_pieces_lost_p2 and self.current_player == self.player2:
                        self.game_over = True
                        self.winner = None  # No winner (player lost)
                
                # Update player pieces list in the board
                if players_captured:
                    self.update_player_pieces()
            
            # Move to the next fox
            self.current_fox_index += 1
            
            # Reset the timer for the next fox
            self.fox_movement_timer = self.movement_delay
        else:
            # All foxes have moved, check if we should activate snake movement
            self.fox_movement_active = False
            if self.green_squiggles > 0:
                self.activate_snake_movement()
            else:
                # No snakes to move, switch to the other player
                self.dice_rolled = False
                self.switch_player()
    
    def move_next_snake(self):
        """Move the next snake in the queue toward the current player."""
        if self.current_snake_index < len(self.snakes_to_move):
            snake_node = self.snakes_to_move[self.current_snake_index]
            
            # Store the player's current position before moving the snake
            player_node = self.current_player.current_node
            
            # Move the snake toward the player
            new_snake_node = self.board.move_snake_toward_player(snake_node, player_node)
            
            # Check if the snake landed on the player
            if (new_snake_node.x == player_node.x and 
                new_snake_node.y == player_node.y):
                # Snake captured a player piece
                all_pieces_lost = self.current_player.lose_piece()
                
                # Update player pieces list in the board
                self.update_player_pieces()
                
                # Display a message about the capture
                self.show_capture_message = True
                self.capture_message = f"{self.current_turn} captured a {self.current_player.player_num} piece!"
                self.message_timer = 45  # Show message for 45 frames (about 1.5 seconds)
                
                # If all pieces are lost, player loses
                if all_pieces_lost:
                    self.game_over = True
                    self.winner = None  # No winner (player lost)
            
            # Check if the snake landed on the center node
            elif new_snake_node == self.board.center_node:
                # Snake captures all players on the center node
                players_captured = False
                
                # Check if player 1 is on the center node
                if self.player1.active and self.player1.current_node == self.board.center_node:
                    all_pieces_lost_p1 = self.player1.lose_piece()
                    players_captured = True
                    
                    # Display a message about the capture
                    self.show_capture_message = True
                    self.capture_message = f"{self.current_turn} captured a 1 piece in the center!"
                    self.message_timer = 45  # Show message for 45 frames (about 1.5 seconds)
                    
                    # If all pieces are lost, player loses
                    if all_pieces_lost_p1 and self.current_player == self.player1:
                        self.game_over = True
                        self.winner = None  # No winner (player lost)
                
                # Check if player 2 is on the center node
                if self.player2.active and self.player2.current_node == self.board.center_node:
                    all_pieces_lost_p2 = self.player2.lose_piece()
                    players_captured = True
                    
                    # Display a message about the capture
                    self.show_capture_message = True
                    self.capture_message = f"{self.current_turn} captured a 2 piece in the center!"
                    self.message_timer = 45  # Show message for 45 frames (about 1.5 seconds)
                    
                    # If all pieces are lost, player loses
                    if all_pieces_lost_p2 and self.current_player == self.player2:
                        self.game_over = True
                        self.winner = None  # No winner (player lost)
                
                # Update player pieces list in the board
                if players_captured:
                    self.update_player_pieces()
            
            # Move to the next snake
            self.current_snake_index += 1
            
            # Reset the timer for the next snake
            self.snake_movement_timer = self.movement_delay
        else:
            # All snakes have moved, switch to the other player
            self.snake_movement_active = False
            self.dice_rolled = False
            self.switch_player()
    
    def update(self):
        """Update game state."""
        # Update dice animation
        self.dice.update()
        
        # Update player animations
        self.player1.update()
        self.player2.update()
        
        # Update board animations (fox and snake pieces)
        self.board.update_animations()
        
        # Handle automatic player switching when no black pips are rolled
        if hasattr(self, 'show_no_pips_message') and self.show_no_pips_message:
            self.message_timer -= 1
            if self.message_timer <= 0:
                # Remove the message
                self.show_no_pips_message = False
                
                # Check if we should activate fox or snake movement
                if self.red_triangles > 0:
                    self.activate_fox_movement()
                elif self.green_squiggles > 0:
                    self.activate_snake_movement()
                else:
                    # No red triangles or green squiggles, switch to the other player
                    self.dice_rolled = False
                    self.switch_player()
        
        # Handle fox movement
        if self.fox_movement_active and not self.game_over:
            self.fox_movement_timer -= 1
            if self.fox_movement_timer <= 0:
                self.move_next_fox()
        
        # Handle snake movement
        if self.snake_movement_active and not self.game_over:
            self.snake_movement_timer -= 1
            if self.snake_movement_timer <= 0:
                self.move_next_snake()
    
    def render(self):
        """Render the game to the screen."""
        # Clear the screen
        self.screen.fill((255, 255, 255))
        
        # Draw the board
        self.board.render(self.screen)
        
        # Highlight valid move nodes on the board for the current player only
        if self.dice_rolled and not self.fox_movement_active and not self.snake_movement_active:
            for node in self.current_player.valid_moves:
                # Draw a simple circle around valid moves
                pygame.draw.circle(
                    self.screen, 
                    (0, 0, 0),  # Black outline
                    node.get_position(), 
                    self.current_player.radius + 5,
                    2  # Line width
                )
        
        # Draw both players
        self.player1.render(self.screen)
        self.player2.render(self.screen)
        
        # Draw game over message
        if self.game_over:
            font = pygame.font.SysFont(None, 72)
            
            if self.winner is not None:
                # Player won the game
                winner_text = f"Player {self.winner.player_num} Wins!"
                game_over_text = font.render(winner_text, True, (0, 128, 0))  # Green for winning
            else:
                # Game over without a winner (players captured or max turns reached)
                if not self.current_player.active:
                    game_over_text = font.render("Game Over - All pieces captured!", True, (255, 0, 0))
                else:
                    game_over_text = font.render("Game Over!", True, (255, 0, 0))
            
            game_over_rect = game_over_text.get_rect(center=(self.width // 2, self.height // 2 - 50))
            self.screen.blit(game_over_text, game_over_rect)
            
            restart_text = font.render("Press R to restart", True, (0, 0, 0))
            restart_rect = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 50))
            self.screen.blit(restart_text, restart_rect)
        
        # Calculate dice position
        dice_x = self.width - 300
        dice_y = 50
        
        # Draw the dice
        self.dice.render(self.screen, dice_x, dice_y)
        
        # Calculate the center position of the dice display
        dice_center_x = dice_x + (self.dice.size * 1.5) + (self.dice.spacing * 0.5)
        dice_bottom_y = dice_y + (self.dice.size * 2) + self.dice.spacing + 20  # Add some padding
        
        # Show "No black pips!" message when applicable
        if hasattr(self, 'show_no_pips_message') and self.show_no_pips_message:
            no_pips_text = self.font.render("No black pips! Player's turn skipped...", True, (255, 0, 0))
            no_pips_rect = no_pips_text.get_rect(center=(dice_center_x, dice_bottom_y))
            self.screen.blit(no_pips_text, no_pips_rect)
            
        # Show capture message when applicable
        if hasattr(self, 'show_capture_message') and self.show_capture_message:
            # Determine message color based on what captured the piece
            message_color = (255, 0, 0) if "Foxes" in self.capture_message else (0, 200, 0)
            capture_text = self.font.render(self.capture_message, True, message_color)
            capture_rect = capture_text.get_rect(center=(dice_center_x, dice_bottom_y))
            self.screen.blit(capture_text, capture_rect)
            
            # Update message timer in the update method
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.show_capture_message = False
        
        # We'll handle all status text in the section below
        
        # Show "Push Space to roll" text when dice haven't been rolled
        if not self.dice_rolled and not self.fox_movement_active and not self.snake_movement_active:
            space_text = self.font.render("Push Space to roll", True, (0, 0, 255))
            space_rect = space_text.get_rect(center=(dice_center_x, dice_bottom_y))
            self.screen.blit(space_text, space_rect)
        
        # Show turn information
        turn_color = (0, 0, 0)
        if self.current_turn == "Foxes":
            turn_color = (255, 0, 0)  # Red for foxes
        elif self.current_turn == "Snakes":
            turn_color = (0, 200, 0)  # Green for snakes
        
        # Always display the active player's turn
        turn_text = self.font.render(
            f"{self.current_turn}'s turn", 
            True, 
            turn_color
        )
        turn_rect = turn_text.get_rect(center=(dice_center_x, dice_bottom_y + 40))
        self.screen.blit(turn_text, turn_rect)
        
        # Display moves remaining only after dice are rolled
        if self.dice_rolled or self.fox_movement_active or self.snake_movement_active:
            # Calculate moves remaining based on current turn
            if self.current_turn == "White" or self.current_turn == "Black":
                moves_remaining = self.moves_remaining
            elif self.current_turn == "Foxes":
                moves_remaining = len(self.foxes_to_move) - self.current_fox_index
            else:  # Snakes
                moves_remaining = len(self.snakes_to_move) - self.current_snake_index
                
            moves_text = self.font.render(
                f"Moves remaining: {moves_remaining}", 
                True, 
                turn_color
            )
            moves_rect = moves_text.get_rect(center=(dice_center_x, dice_bottom_y + 80))
            self.screen.blit(moves_text, moves_rect)
