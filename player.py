"""
Player module for Snakes and Foxes game
"""
import pygame
import math
from typing import Tuple, List, Optional
from board import BoardNode, Board

class Player:
    """
    Represents a player in the Snakes and Foxes game.
    
    Handles player position, movement, and rendering.
    Each player has two pieces that can be captured by foxes.
    """
    
    def __init__(self, board: Board, player_num: int = 1):
        """
        Initialize the player at the starting position.
        
        Args:
            board: The game board
            player_num: Player number (1 or 2)
        """
        self.board = board
        self.current_node = board.center_node  # Start at the center (innermost circle)
        self.previous_node = None  # Track the previous node for multi-move turns
        self.player_num = player_num
        
        # Set color based on player number (1=white, 2=black)
        if player_num == 1:
            self.color = (255, 255, 255)  # White
        else:
            self.color = (0, 0, 0)        # Black
            
        self.radius = 10
        
        # Game state
        self.turn_count = 0
        self.has_reached_outer_circle = False
        
        # Valid moves after dice roll
        self.valid_moves = []
        
        # Player pieces
        self.pieces = 2  # Start with 2 pieces
        self.active = True  # Player is active in the game
        
        # Animation properties
        self.is_moving = False
        self.move_start_pos = (0, 0)
        self.move_end_pos = (0, 0)
        self.move_progress = 0
        self.move_speed = 0.05  # Progress increment per frame (slower for smoother animation)
        self.animation_path = []  # List of points defining the animation path
        self.target_node = None  # The node we're moving to
        
        # Callback function to notify the game when animation completes
        self.on_animation_complete = None
        
    def reset(self):
        """Reset the player to the starting position."""
        self.current_node = self.board.center_node
        self.previous_node = None
        self.turn_count = 0
        self.has_reached_outer_circle = False
        self.valid_moves = []
        self.is_moving = False
        self.pieces = 2  # Reset to 2 pieces
        self.active = True  # Player is active again
    
    def get_valid_moves(self, dice_value: int) -> List[BoardNode]:
        """
        Get valid moves based on the dice roll.
        
        Args:
            dice_value: The dice roll value
            
        Returns:
            List of valid destination nodes
        """
        # Always set is_player=True for player movement
        self.valid_moves = self.board.get_valid_moves(self.current_node, dice_value, is_player=True, previous_node=self.previous_node)
        return self.valid_moves
    
    def get_connected_nodes(self) -> List[BoardNode]:
        """
        Get all nodes that have a directed edge connecting to the current node.
        
        Returns:
            List of connected nodes
        """
        # Always set is_player=True for player movement
        self.valid_moves = self.board.get_connected_nodes(self.current_node, is_player=True, previous_node=self.previous_node)
        return self.valid_moves
    
    def move_to_node(self, target_node: BoardNode) -> None:
        """
        Move the player to a specific node and apply any special effects.
        
        Args:
            target_node: The node to move to
        """
        # Make sure the node is in valid moves or make it valid for testing purposes
        if target_node not in self.valid_moves:
            self.valid_moves.append(target_node)
        
        # Store the current node as the previous node before moving
        self.previous_node = self.current_node
        
        # Check immediately if this is an outer circle node
        if target_node.circle_idx == self.board.num_circles - 1:
            self.has_reached_outer_circle = True
        
        # Start animation
        self.start_move_animation(target_node)
        
        # The actual position update will happen when the animation completes
        # in the update method
    
    def can_win(self) -> bool:
        """
        Check if the player can win (has reached outer circle and is now back at center).
        
        Returns:
            True if the player can win, False otherwise
        """
        # Player can win if they've reached any node in the outermost circle
        # and are now back at the center node
        return (self.has_reached_outer_circle and 
                self.current_node == self.board.center_node)
    
    def lose_piece(self) -> bool:
        """
        Remove one piece from the player.
        
        Returns:
            True if the player has no pieces left, False otherwise
        """
        self.pieces -= 1
        # When a player loses a piece, they become inactive (removed from the board)
        self.active = False
        # Return True if all pieces are lost, False otherwise
        return self.pieces <= 0
    
    def get_position_description(self) -> str:
        """
        Get a description of the player's current position.
        
        Returns:
            A string describing the player's position
        """
        circle_idx = self.current_node.circle_idx
        node_idx = self.current_node.node_idx
        
        if self.current_node == self.board.center_node:
            return "Center (Start)"
        elif self.current_node == self.board.goal_node:
            return "Goal"
        else:
            return f"Circle {circle_idx}, Node {node_idx}"
    
    def start_move_animation(self, target_node: BoardNode) -> None:
        """
        Start the animation for moving to a target node.
        
        Args:
            target_node: The node to move to
        """
        self.is_moving = True
        self.move_progress = 0
        self.target_node = target_node
        
        # Store start position
        start_x, start_y = self.current_node.get_position()
        if self.current_node == self.board.center_node:
            # Apply offset for center node
            offset = -15 if self.player_num == 1 else 15
            start_x += offset
        self.move_start_pos = (start_x, start_y)
        
        # Calculate the animation path
        self.calculate_animation_path(target_node)
    
    def calculate_animation_path(self, target_node: BoardNode) -> None:
        """
        Calculate the path for the animation based on the movement type.
        
        Args:
            target_node: The node to move to
        """
        start_node = self.current_node
        
        # Clear the current path
        self.animation_path = []
        
        # Case 1: Moving within the same circle (arc path)
        if start_node.circle_idx == target_node.circle_idx and start_node.circle_idx > 0:
            self.calculate_arc_path(start_node, target_node)
        
        # Case 2: Moving between circles (straight line)
        else:
            self.calculate_straight_path(start_node, target_node)
    
    def calculate_arc_path(self, start_node: BoardNode, target_node: BoardNode) -> None:
        """
        Calculate an arc path for movement within the same circle.
        
        Args:
            start_node: The starting node
            target_node: The target node
        """
        # Get the center of the board
        center_x, center_y = self.board.center_x, self.board.center_y
        
        # Get the circle radius
        circle_radius = (start_node.circle_idx + 1) * self.board.circle_spacing
        
        # Get start and end positions
        start_pos = start_node.get_position()
        end_pos = target_node.get_position()
        
        # Calculate node indices
        start_idx = start_node.node_idx
        end_idx = target_node.node_idx
        
        # Calculate the rotation angle (pi/5 per node as there are 10 nodes in a full rotation)
        angle_per_node = math.pi / 5
        
        # Calculate the number of nodes to rotate (shortest path)
        nodes_diff = (end_idx - start_idx) % self.board.nodes_per_circle
        if nodes_diff > self.board.nodes_per_circle / 2:
            nodes_diff = nodes_diff - self.board.nodes_per_circle
        
        # Calculate the total rotation angle
        rotation_angle = nodes_diff * angle_per_node
        
        # Get the starting angle in radians
        start_vector = pygame.math.Vector2(start_pos[0] - center_x, start_pos[1] - center_y)
        start_angle_rad = math.atan2(start_vector.y, start_vector.x)
        
        # Create points along the arc
        num_points = 20  # Number of points in the path
        
        for i in range(num_points + 1):
            # Interpolate angle
            t = i / num_points
            angle = start_angle_rad + rotation_angle * t
            
            # Calculate position
            x = center_x + circle_radius * math.cos(angle)
            y = center_y + circle_radius * math.sin(angle)
            
            self.animation_path.append((x, y))
    
    def calculate_straight_path(self, start_node: BoardNode, target_node: BoardNode) -> None:
        """
        Calculate a straight path for movement between circles.
        
        Args:
            start_node: The starting node
            target_node: The target node
        """
        # Get start and end positions
        start_x, start_y = self.move_start_pos
        end_x, end_y = target_node.get_position()
        
        # Create points along the straight line
        num_points = 20  # Number of points in the path
        
        for i in range(num_points + 1):
            # Interpolate position
            t = i / num_points
            x = start_x + (end_x - start_x) * t
            y = start_y + (end_y - start_y) * t
            
            self.animation_path.append((x, y))
    
    def update(self) -> None:
        """Update the player's animation state."""
        if self.is_moving:
            # Update animation progress
            self.move_progress += self.move_speed
            
            # Check if animation is complete
            if self.move_progress >= 1:
                self.is_moving = False
                
                # Store the target node before any special effects are applied
                original_target = self.target_node
                
                # Update position to the target node
                self.current_node = self.target_node
                
                # Check if player has reached the outermost circle and set the flag
                if self.current_node.circle_idx == self.board.num_circles - 1:
                    self.has_reached_outer_circle = True
                
                # Apply special effects (snakes or foxes)
                effect_node = self.board.apply_special_effect(self.current_node)
                
                # Only update the current node if applying a special effect doesn't
                # move the player from the outer circle to a non-outer circle
                if not (self.current_node.circle_idx == self.board.num_circles - 1 and 
                        effect_node.circle_idx != self.board.num_circles - 1):
                    self.current_node = effect_node
                
                # Increment turn count
                self.turn_count += 1
                
                # Update valid moves from the new position
                # This ensures the player can move again if they have more moves left
                self.get_connected_nodes()
                
                # Clear target node
                self.target_node = None
                
                # Call the callback function if it exists
                if self.on_animation_complete:
                    self.on_animation_complete()
    
    def get_current_animated_position(self) -> Tuple[int, int]:
        """
        Get the current position during animation.
        
        Returns:
            The current (x, y) position
        """
        if not self.is_moving or not self.animation_path:
            # If not moving or no path, return the current node position
            x, y = self.current_node.get_position()
            
            # Apply offset for center node
            if self.current_node == self.board.center_node:
                offset = -15 if self.player_num == 1 else 15
                x += offset
                
            return (x, y)
        
        # Calculate the index in the animation path
        path_index = min(int(self.move_progress * len(self.animation_path)), len(self.animation_path) - 1)
        
        # Return the position at that index
        return self.animation_path[path_index]
    
    def render(self, screen: pygame.Surface) -> None:
        """
        Render the player on the screen.
        
        Args:
            screen: The pygame surface to render on
        """
        # Only render if the player is active
        if not self.active:
            return
        
        # Get the current position (either animated or static)
        x, y = self.get_current_animated_position()
        
        # Draw the player as a simple circle without numbers
        pygame.draw.circle(screen, self.color, (x, y), self.radius)
        pygame.draw.circle(screen, (0, 0, 0), (x, y), self.radius, 1)  # Border
