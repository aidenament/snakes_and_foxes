"""
Board module for Snakes and Foxes game
"""
import pygame
import math
from typing import List, Tuple, Dict, Optional

class BoardNode:
    """
    Represents a single node on the game board.
    """
    def __init__(self, x: int, y: int, circle_idx: int, node_idx: int):
        """
        Initialize a board node.
        
        Args:
            x: X coordinate on screen
            y: Y coordinate on screen
            circle_idx: Index of the circle this node belongs to (0 = innermost)
            node_idx: Index of the node within its circle (0 to nodes_per_circle-1)
        """
        self.x = x
        self.y = y
        self.circle_idx = circle_idx
        self.node_idx = node_idx
        self.is_snake = False
        self.is_fox = False
        self.snake_target = None
        self.fox_target = None
    
    def __eq__(self, other):
        """
        Check if two nodes are equal based on their coordinates and indices.
        
        Args:
            other: The other node to compare with
            
        Returns:
            True if the nodes have the same coordinates and indices, False otherwise
        """
        if not isinstance(other, BoardNode):
            return False
        return (self.x == other.x and 
                self.y == other.y and 
                self.circle_idx == other.circle_idx and 
                self.node_idx == other.node_idx)
    
    def __hash__(self):
        """
        Generate a hash value for the node based on its coordinates and indices.
        
        Returns:
            A hash value for the node
        """
        return hash((self.x, self.y, self.circle_idx, self.node_idx))
        
    def get_position(self) -> Tuple[int, int]:
        """Get the screen coordinates of this node."""
        return (self.x, self.y)

class Board:
    """
    Represents the game board with concentric circles of nodes.
    
    The board contains special spaces (snakes and foxes) that affect player movement.
    It also contains fox pieces that can move and capture player pieces.
    """
    
    # List of player pieces on the board (will be set by the Game class)
    player_pieces = []
    
    # Animation properties for fox and snake pieces
    fox_animations = {}  # Dictionary mapping fox node to animation data
    snake_animations = {}  # Dictionary mapping snake node to animation data
    
    def is_node_occupied(self, node: BoardNode, current_player_node: Optional[BoardNode] = None) -> bool:
        """
        Check if a node is occupied by any piece (player, fox, or snake).
        
        Args:
            node: The node to check
            current_player_node: The current player's node (to allow capture)
            
        Returns:
            True if the node is occupied, False otherwise
        """
        # Center node is special - allows multiple players but not if a fox or snake is there
        if node == self.center_node:
            # Check if center node is occupied by a fox or snake piece
            for fox_node in self.fox_pieces:
                if fox_node.x == node.x and fox_node.y == node.y:
                    return True
            
            for snake_node in self.snake_pieces:
                if snake_node.x == node.x and snake_node.y == node.y:
                    return True
            
            # Center node is not occupied by a fox or snake, so it's available
            return False
        
        # Check if node is occupied by a fox piece
        if node in self.fox_pieces:
            # If this is the current player's node, allow capture
            return current_player_node != node
        
        # Check if node is occupied by a snake piece
        if node in self.snake_pieces:
            # If this is the current player's node, allow capture
            return current_player_node != node
        
        # Check if node is occupied by a player piece
        for player_node in self.player_pieces:
            if node.x == player_node.x and node.y == player_node.y:
                # If this is the current player's node, allow movement
                if current_player_node and node.x == current_player_node.x and node.y == current_player_node.y:
                    return False
                return True
        
        # Node is not occupied
        return False
    
    def __init__(self, num_circles: int = 6, nodes_per_circle: int = 10):
        """
        Initialize the board with spaces and special elements.
        
        Args:
            num_circles: Number of concentric circles on the board
            nodes_per_circle: Number of nodes per circle
        """
        # Animation properties
        self.animation_speed = 0.05  # Progress increment per frame
        # Board dimensions and properties
        self.center_x = 900  # Centered in the 50% wider window (1800/2)
        self.center_y = 500  # Centered vertically (1000/2)
        self.circle_spacing = 80  # Increased spacing between circles
        self.node_radius = 20     # Increased radius of each node
        self.center_node_radius = 40  # Increased radius of the center node
        
        # Board structure
        self.num_circles = num_circles
        self.nodes_per_circle = nodes_per_circle
        
        # Generate the board nodes
        self.nodes = self._generate_board()
        
        # Define the center node (starting position)
        self.center_node = self.nodes[0][0]  # The only node in the innermost "circle"
        
        # The outermost circle has multiple nodes, any of which can be a goal
        self.outermost_circle_idx = self.num_circles - 1
        
        # Define movement directions for each circle (alternating)
        self.circle_directions = []
        for i in range(num_circles):
            # Even circles go counter-clockwise, odd circles go clockwise
            # Switched from the original pattern
            self.circle_directions.append(-1 if i % 2 == 0 else 1)
        
        # Define snakes and foxes (special nodes)
        self._setup_special_nodes()
        
        # Fox and snake pieces that can move and capture players
        self.fox_pieces = []
        self.snake_pieces = []
        self._setup_fox_pieces()
        self._setup_snake_pieces()
        
        # Colors
        self.normal_color = (200, 200, 200)
        self.snake_color = (0, 200, 0)     # Green for snakes
        self.fox_color = (255, 0, 0)       # Red for foxes
        self.fox_piece_color = (255, 0, 0) # Red for fox pieces
        self.snake_piece_color = (0, 200, 0) # Green for snake pieces
        self.center_color = (255, 215, 0)  # Gold for the center
        self.goal_color = (0, 0, 255)      # Blue for the goal
        self.circle_colors = [
            (220, 220, 220),  # Light gray
            (200, 200, 200),  # Gray
            (180, 180, 180),  # Darker gray
            (160, 160, 160),  # Even darker gray
            (140, 140, 140),  # Very dark gray
            (120, 120, 120),  # Almost black
        ]
    
    def _generate_board(self) -> List[List[BoardNode]]:
        """
        Generate the board with concentric circles of nodes.
        The innermost circle is a single node, while other circles have multiple nodes.
        
        Returns:
            A 2D list of BoardNode objects organized by [circle_idx][node_idx]
        """
        nodes = []
        
        # Generate nodes for each circle
        for circle_idx in range(self.num_circles):
            circle_nodes = []
            
            # Calculate the radius for this circle
            circle_radius = (circle_idx + 1) * self.circle_spacing
            
            # Innermost circle (circle_idx = 0) is a single node at the center
            if circle_idx == 0:
                # Create a single center node
                center_node = BoardNode(self.center_x, self.center_y, 0, 0)
                circle_nodes.append(center_node)
            else:
                # Other circles have multiple nodes
                for node_idx in range(self.nodes_per_circle):
                    # Calculate angle for this node
                    angle = 2 * math.pi * node_idx / self.nodes_per_circle
                    
                    # Calculate coordinates
                    x = self.center_x + circle_radius * math.cos(angle)
                    y = self.center_y + circle_radius * math.sin(angle)
                    
                    # Create the node
                    node = BoardNode(int(x), int(y), circle_idx, node_idx)
                    circle_nodes.append(node)
            
            nodes.append(circle_nodes)
        
        return nodes
    
    def _setup_special_nodes(self):
        """Set up snakes and foxes (special nodes) on the board."""
        # Only add snakes and foxes to the outermost circle
        circle_idx = self.num_circles - 1  # Outermost circle
        
        # Alternate between snakes and foxes around the outermost circle
        for node_idx in range(self.nodes_per_circle):
            node = self.get_node(circle_idx, node_idx)
            
            # Even positions are snakes, odd positions are foxes
            if node_idx % 2 == 0:
                # Snake - sends player back to previous circle
                node.is_snake = True
                node.snake_target = self.get_node(circle_idx - 1, node_idx)
            else:
                # Fox - sends player forward (in this case, wraps around to the same position)
                # Since we're already at the outermost circle, we'll just keep the player in the same position
                # This is a placeholder - foxes don't do anything on the outermost circle
                node.is_fox = True
                node.fox_target = node  # Stay in the same position
    
    def _setup_fox_pieces(self):
        """Set up fox pieces on the board."""
        # Add fox pieces to the outermost circle at positions with red triangles
        circle_idx = self.num_circles - 1  # Outermost circle
        
        # Place fox pieces at positions with red triangles (odd positions)
        for node_idx in range(self.nodes_per_circle):
            if node_idx % 2 == 1:  # Odd positions (where fox special nodes are)
                node = self.get_node(circle_idx, node_idx)
                self.fox_pieces.append(node)
    
    def _setup_snake_pieces(self):
        """Set up snake pieces on the board."""
        # Add snake pieces to the outermost circle at positions with green snakes
        circle_idx = self.num_circles - 1  # Outermost circle
        
        # Place snake pieces at positions with green snakes (even positions)
        for node_idx in range(self.nodes_per_circle):
            if node_idx % 2 == 0:  # Even positions (where snake special nodes are)
                node = self.get_node(circle_idx, node_idx)
                self.snake_pieces.append(node)
    
    def get_node(self, circle_idx: int, node_idx: int) -> Optional[BoardNode]:
        """
        Get a node by its circle and node indices.
        
        Args:
            circle_idx: Index of the circle (0 = innermost)
            node_idx: Index of the node within the circle
            
        Returns:
            The BoardNode at the specified position, or None if invalid
        """
        if 0 <= circle_idx < self.num_circles:
            # Normalize node_idx to wrap around the circle
            node_idx = node_idx % self.nodes_per_circle
            return self.nodes[circle_idx][node_idx]
        return None
    
    def get_node_color(self, node: BoardNode) -> Tuple[int, int, int]:
        """
        Get the color for a given node based on its type.
        
        Args:
            node: The BoardNode to get the color for
            
        Returns:
            RGB color tuple
        """
        # Use normal color for all nodes
        return self.normal_color
    
    def get_valid_moves(self, current_node: BoardNode, dice_value: int, is_player: bool = True, previous_node: Optional[BoardNode] = None) -> List[BoardNode]:
        """
        Get valid moves from the current node based on dice value.
        
        Args:
            current_node: The current node
            dice_value: The dice roll value
            is_player: Whether the current node is a player node
            previous_node: The previous node the player was on (for multi-move turns)
            
        Returns:
            List of valid destination nodes
        """
        valid_moves = []
        
        # Get current circle and node indices
        circle_idx = current_node.circle_idx
        node_idx = current_node.node_idx
        
        # Special case for center node (innermost circle)
        if circle_idx == 0:
            # From center, can only move to first circle with dice value 1
            if dice_value == 1:
                # Can move to any node in the first circle with a roll of 1
                for first_circle_node in self.nodes[1]:
                    # Check if the node is not occupied or is the previous node
                    if not self.is_node_occupied(first_circle_node, current_node) or (previous_node and first_circle_node.x == previous_node.x and first_circle_node.y == previous_node.y):
                        valid_moves.append(first_circle_node)
            return valid_moves
        
        # Special case for outermost circle - allow movement to any node in the circle
        if is_player and circle_idx == self.num_circles - 1:
            # For dice value > 1, use the standard movement within the circle
            if dice_value > 1:
                direction = self.circle_directions[circle_idx]
                new_node_idx = (node_idx + direction * dice_value) % len(self.nodes[circle_idx])
                same_circle_node = self.get_node(circle_idx, new_node_idx)
                
                if same_circle_node and (not self.is_node_occupied(same_circle_node, current_node) or 
                                      (previous_node and same_circle_node.x == previous_node.x and same_circle_node.y == previous_node.y)):
                    valid_moves.append(same_circle_node)
                return valid_moves
            
            # For dice value 1, allow movement ONLY to adjacent nodes in the proper direction
            direction = self.circle_directions[circle_idx]
            adj_node_idx = (node_idx + direction) % self.nodes_per_circle
            adj_node = self.get_node(circle_idx, adj_node_idx)
            
            # Check if the adjacent node is the previous node or not occupied
            if adj_node and (not self.is_node_occupied(adj_node, current_node) or 
                           (previous_node and adj_node.x == previous_node.x and adj_node.y == previous_node.y)):
                valid_moves.append(adj_node)
            
            # Also add the previous node if it exists and is not already in valid_moves
            if previous_node and previous_node not in valid_moves:
                valid_moves.append(previous_node)
            
            # Add inner circle node (for moving inward)
            if circle_idx > 0:
                inner_node = self.get_node(circle_idx - 1, node_idx)
                if inner_node and (not self.is_node_occupied(inner_node, current_node) or 
                                  (previous_node and inner_node.x == previous_node.x and inner_node.y == previous_node.y)):
                    valid_moves.append(inner_node)
            
            return valid_moves
        # For all other circles (not outermost):
        
        # 1. Move within the same circle
        direction = self.circle_directions[circle_idx]
        new_node_idx = (node_idx + direction * dice_value) % len(self.nodes[circle_idx])
        same_circle_node = self.get_node(circle_idx, new_node_idx)
        
        if same_circle_node and (not self.is_node_occupied(same_circle_node, current_node) or 
                               (previous_node and same_circle_node.x == previous_node.x and same_circle_node.y == previous_node.y)):
            valid_moves.append(same_circle_node)
        
        # 2. Move to adjacent circle (if dice value matches)
        if dice_value == 1:
            # Move inward (if not at innermost circle)
            if circle_idx > 0:
                # If moving to center (innermost), there's only one node there
                if circle_idx == 1:
                    inner_node = self.center_node
                else:
                    inner_node = self.get_node(circle_idx - 1, node_idx)
                
                # Check if the node is not occupied or is the previous node
                if inner_node and (not self.is_node_occupied(inner_node, current_node) or 
                                 (previous_node and inner_node.x == previous_node.x and inner_node.y == previous_node.y)):
                    valid_moves.append(inner_node)
            
            # Move outward (if not at outermost circle)
            if circle_idx < self.num_circles - 1:
                outer_node = self.get_node(circle_idx + 1, node_idx)
                
                # For players, allow movement to the outermost circle even if occupied by enemy pieces
                if is_player and circle_idx == self.num_circles - 2:  # Moving to outermost circle
                    # Check if the outer node is the previous node - if so, always allow movement to it
                    if previous_node and outer_node.x == previous_node.x and outer_node.y == previous_node.y:
                        valid_moves.append(outer_node)
                    else:
                        # Check if it's occupied by another player, snake, or fox
                        is_occupied_by_player = False
                        for player_node in self.player_pieces:
                            if (outer_node.x == player_node.x and outer_node.y == player_node.y and 
                                (current_node.x != player_node.x or current_node.y != player_node.y)):
                                is_occupied_by_player = True
                                break
                        
                        # Check if the node is occupied by a fox or snake
                        is_occupied_by_enemy = False
                        for fox_node in self.fox_pieces:
                            if outer_node.x == fox_node.x and outer_node.y == fox_node.y:
                                is_occupied_by_enemy = True
                                break
                        
                        for snake_node in self.snake_pieces:
                            if outer_node.x == snake_node.x and outer_node.y == snake_node.y:
                                is_occupied_by_enemy = True
                                break
                        
                        if not is_occupied_by_player and not is_occupied_by_enemy:
                            valid_moves.append(outer_node)
        
        return valid_moves
    
    def get_connected_nodes(self, current_node: BoardNode, is_player: bool = False, previous_node: Optional[BoardNode] = None) -> List[BoardNode]:
        """
        Get all nodes that have a directed edge connecting to the current node.
        
        Args:
            current_node: The current node
            is_player: Whether the current node is a player node
            previous_node: The previous node the player was on (for multi-move turns)
            
        Returns:
            List of connected nodes
        """
        connected_nodes = []
        
        # Get current circle and node indices
        circle_idx = current_node.circle_idx
        node_idx = current_node.node_idx
        
        # Special case for center node (innermost circle)
        if circle_idx == 0:
            # From center, can move to any node in the first circle
            for first_circle_node in self.nodes[1]:
                # Check if the node is not occupied or is the previous node
                if not self.is_node_occupied(first_circle_node, current_node) or (previous_node and first_circle_node.x == previous_node.x and first_circle_node.y == previous_node.y):
                    connected_nodes.append(first_circle_node)
            return connected_nodes
        
        # Special case for outermost circle
        if is_player and circle_idx == self.num_circles - 1:
            # Only allow movement to the adjacent node in the direction of rotation
            direction = self.circle_directions[circle_idx]
            adj_node_idx = (node_idx + direction) % self.nodes_per_circle
            adj_node = self.get_node(circle_idx, adj_node_idx)
            
            # Check if the adjacent node is not occupied by a player or enemy
            if adj_node:
                is_occupied_by_player = False
                for player_node in self.player_pieces:
                    if (adj_node.x == player_node.x and adj_node.y == player_node.y and 
                        (current_node.x != player_node.x or current_node.y != player_node.y)):
                        is_occupied_by_player = True
                        break
                
                is_occupied_by_enemy = False
                for fox_node in self.fox_pieces:
                    if adj_node.x == fox_node.x and adj_node.y == fox_node.y:
                        is_occupied_by_enemy = True
                        break
                
                for snake_node in self.snake_pieces:
                    if adj_node.x == snake_node.x and adj_node.y == snake_node.y:
                        is_occupied_by_enemy = True
                        break
                
                if not is_occupied_by_player and not is_occupied_by_enemy:
                    connected_nodes.append(adj_node)
            
            # Also add the previous node if it exists and is not already in connected_nodes
            if previous_node and previous_node not in connected_nodes:
                connected_nodes.append(previous_node)
            
            # Add inner circle node (for moving inward)
            if circle_idx > 0:
                inner_node = self.get_node(circle_idx - 1, node_idx)
                if inner_node and (not self.is_node_occupied(inner_node, current_node) or 
                                  (previous_node and inner_node.x == previous_node.x and inner_node.y == previous_node.y)):
                    connected_nodes.append(inner_node)
            
            return connected_nodes
        
        # For all other circles (not outermost):
        
        # 1. Move within the same circle (only in the direction of the arrows)
        direction = self.circle_directions[circle_idx]
        
        # Only allow movement in the direction of the arrows
        next_node_idx = (node_idx + direction) % len(self.nodes[circle_idx])
        next_node = self.get_node(circle_idx, next_node_idx)
        
        if next_node and (not self.is_node_occupied(next_node, current_node) or 
                         (previous_node and next_node.x == previous_node.x and next_node.y == previous_node.y)):
            connected_nodes.append(next_node)
        
        # 2. Move to adjacent circles
        
        # Move inward (if not at innermost circle)
        if circle_idx > 0:
            # If moving to center (innermost), there's only one node there
            if circle_idx == 1:
                inner_node = self.center_node
            else:
                inner_node = self.get_node(circle_idx - 1, node_idx)
            
            if inner_node and (not self.is_node_occupied(inner_node, current_node) or 
                              (previous_node and inner_node.x == previous_node.x and inner_node.y == previous_node.y)):
                connected_nodes.append(inner_node)
        
        # Move outward (if not at outermost circle)
        if circle_idx < self.num_circles - 1:
            outer_node = self.get_node(circle_idx + 1, node_idx)
            
            # For players, allow movement to the outermost circle even if occupied by enemy pieces
            if is_player and circle_idx == self.num_circles - 2:  # Moving to outermost circle
                # Check if the outer node is the previous node - if so, always allow movement to it
                if previous_node and outer_node.x == previous_node.x and outer_node.y == previous_node.y:
                    connected_nodes.append(outer_node)
                else:
                    # Only check if it's occupied by another player, not by enemy pieces
                    is_occupied_by_player = False
                    for player_node in self.player_pieces:
                        if (player_node == outer_node and 
                            current_node != player_node):
                            is_occupied_by_player = True
                            break
                    
                    # Check if the node is occupied by a fox or snake
                    is_occupied_by_enemy = False
                    for fox_node in self.fox_pieces:
                        if outer_node.x == fox_node.x and outer_node.y == fox_node.y:
                            is_occupied_by_enemy = True
                            break
                    
                    for snake_node in self.snake_pieces:
                        if outer_node.x == snake_node.x and outer_node.y == snake_node.y:
                            is_occupied_by_enemy = True
                            break
                    
                    if not is_occupied_by_player and not is_occupied_by_enemy:
                        connected_nodes.append(outer_node)
            # For all other cases
            elif outer_node and (not self.is_node_occupied(outer_node, current_node) or 
                               (previous_node and outer_node.x == previous_node.x and outer_node.y == previous_node.y)):
                connected_nodes.append(outer_node)
        
        return connected_nodes
    
    def apply_special_effect(self, node: BoardNode) -> BoardNode:
        """
        Apply special effects (snakes or foxes) based on the node.
        
        Args:
            node: The current node
            
        Returns:
            The new node after applying any special effects
        """
        if node.is_snake and node.snake_target:
            return node.snake_target
        elif node.is_fox and node.fox_target:
            return node.fox_target
        return node
    
    def find_closest_pieces(self, pieces, target_node):
        """
        Find pieces sorted by distance to the target node.
        
        Args:
            pieces: List of piece nodes to sort
            target_node: The node to measure distance from
            
        Returns:
            List of piece nodes sorted by distance (closest first)
        """
        # Calculate distances from each piece to the target node
        piece_distances = []
        for piece_node in pieces:
            # Calculate Euclidean distance between piece and target
            piece_x, piece_y = piece_node.get_position()
            target_x, target_y = target_node.get_position()
            distance = ((piece_x - target_x) ** 2 + (piece_y - target_y) ** 2) ** 0.5
            piece_distances.append((piece_node, distance))
        
        # Sort pieces by distance (closest first)
        piece_distances.sort(key=lambda x: x[1])
        
        # Return just the piece nodes in order of distance
        return [piece[0] for piece in piece_distances]
    
    def find_closest_foxes(self, target_node):
        """
        Find fox pieces sorted by distance to the target node.
        
        Args:
            target_node: The node to measure distance from
            
        Returns:
            List of fox piece nodes sorted by distance (closest first)
        """
        return self.find_closest_pieces(self.fox_pieces, target_node)
    
    def find_closest_snakes(self, target_node):
        """
        Find snake pieces sorted by distance to the target node.
        
        Args:
            target_node: The node to measure distance from
            
        Returns:
            List of snake piece nodes sorted by distance (closest first)
        """
        return self.find_closest_pieces(self.snake_pieces, target_node)
    
    def move_piece_toward_player(self, piece_node, player_node, piece_list):
        """
        Move a piece one step toward the player.
        
        Args:
            piece_node: The piece node to move
            player_node: The player node to move toward
            piece_list: The list containing the piece (fox_pieces or snake_pieces)
            
        Returns:
            The new node position of the piece
        """
        # First check if the player is in a directly connected node
        # If so, prioritize capturing the player
        
        # Get all possible connected nodes without occupation check
        # This is important for capture mechanics
        connected_nodes_raw = []
        
        # Get current circle and node indices
        circle_idx = piece_node.circle_idx
        node_idx = piece_node.node_idx
        
        # Add node in the same circle
        direction = self.circle_directions[circle_idx]
        next_node_idx = (node_idx + direction) % len(self.nodes[circle_idx])
        next_node = self.get_node(circle_idx, next_node_idx)
        if next_node:
            connected_nodes_raw.append(next_node)
        
        # Add nodes in adjacent circles
        if circle_idx > 0:
            # If moving to center (innermost), there's only one node there
            if circle_idx == 1:
                inner_node = self.center_node
            else:
                inner_node = self.get_node(circle_idx - 1, node_idx)
            
            if inner_node:
                connected_nodes_raw.append(inner_node)
        
        if circle_idx < self.num_circles - 1:
            outer_node = self.get_node(circle_idx + 1, node_idx)
            if outer_node:
                connected_nodes_raw.append(outer_node)
        
        # Check if player is in a directly connected node
        for node in connected_nodes_raw:
            if node.x == player_node.x and node.y == player_node.y:
                # Found the player! Move to capture
                piece_index = piece_list.index(piece_node)
                piece_list[piece_index] = node
                return node
        
        # If we can't capture directly, move toward the player
        # Get all connected nodes from the piece's current position
        # We need to temporarily remove the piece from its current position
        # to avoid it blocking itself when calculating connected nodes
        piece_index = piece_list.index(piece_node)
        piece_list.pop(piece_index)
        
        # Now get connected nodes (this will consider other occupied nodes)
        connected_nodes = self.get_connected_nodes(piece_node)
        
        # Put the piece back in its original position
        piece_list.insert(piece_index, piece_node)
        
        if not connected_nodes:
            return piece_node  # No valid moves, stay in place
        
        # Find the connected node that's closest to the player
        closest_node = None
        min_distance = float('inf')
        
        for node in connected_nodes:
            # Calculate distance from this node to the player
            node_x, node_y = node.get_position()
            player_x, player_y = player_node.get_position()
            distance = ((node_x - player_x) ** 2 + (node_y - player_y) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_node = node
        
        # Move the piece to the closest node
        if closest_node:
            # Update piece position in the list
            piece_list[piece_index] = closest_node
            return closest_node
        
        return piece_node  # No valid moves, stay in place
    
    def move_fox_toward_player(self, fox_node, player_node):
        """
        Move a fox piece one step toward the player.
        
        Args:
            fox_node: The fox piece node to move
            player_node: The player node to move toward
            
        Returns:
            The new node position of the fox
        """
        target_node = self.move_piece_toward_player(fox_node, player_node, self.fox_pieces)
        
        # Start animation for the fox piece
        if target_node != fox_node:
            self.start_piece_animation(fox_node, target_node, is_fox=True)
        
        return target_node
    
    def move_snake_toward_player(self, snake_node, player_node):
        """
        Move a snake piece one step toward the player.
        
        Args:
            snake_node: The snake piece node to move
            player_node: The player node to move toward
            
        Returns:
            The new node position of the snake
        """
        target_node = self.move_piece_toward_player(snake_node, player_node, self.snake_pieces)
        
        # Start animation for the snake piece
        if target_node != snake_node:
            self.start_piece_animation(snake_node, target_node, is_fox=False)
        
        return target_node
    
    def start_piece_animation(self, start_node, target_node, is_fox=True):
        """
        Start an animation for a piece moving from start_node to target_node.
        
        Args:
            start_node: The starting node
            target_node: The target node
            is_fox: True if this is a fox piece, False if it's a snake piece
        """
        # Calculate the animation path
        animation_path = self.calculate_piece_animation_path(start_node, target_node)
        
        # Store the animation data
        animation_data = {
            'start_node': start_node,
            'target_node': target_node,
            'path': animation_path,
            'progress': 0.0
        }
        
        # Add to the appropriate animation dictionary
        if is_fox:
            self.fox_animations[target_node] = animation_data
        else:
            self.snake_animations[target_node] = animation_data
    
    def calculate_piece_animation_path(self, start_node, target_node):
        """
        Calculate the path for a piece animation.
        
        Args:
            start_node: The starting node
            target_node: The target node
            
        Returns:
            List of points defining the animation path
        """
        animation_path = []
        
        # Case 1: Moving within the same circle (arc path)
        if start_node.circle_idx == target_node.circle_idx and start_node.circle_idx > 0:
            # Get the center of the board
            center_x, center_y = self.center_x, self.center_y
            
            # Get the circle radius
            circle_radius = (start_node.circle_idx + 1) * self.circle_spacing
            
            # Get start and end positions
            start_pos = start_node.get_position()
            end_pos = target_node.get_position()
            
            # Calculate node indices
            start_idx = start_node.node_idx
            end_idx = target_node.node_idx
            
            # Calculate the rotation angle (pi/5 per node as there are 10 nodes in a full rotation)
            angle_per_node = math.pi / 5
            
            # Calculate the number of nodes to rotate (shortest path)
            nodes_diff = (end_idx - start_idx) % self.nodes_per_circle
            if nodes_diff > self.nodes_per_circle / 2:
                nodes_diff = nodes_diff - self.nodes_per_circle
            
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
                
                animation_path.append((x, y))
        
        # Case 2: Moving between circles (straight line)
        else:
            # Get start and end positions
            start_x, start_y = start_node.get_position()
            end_x, end_y = target_node.get_position()
            
            # Create points along the straight line
            num_points = 20  # Number of points in the path
            
            for i in range(num_points + 1):
                # Interpolate position
                t = i / num_points
                x = start_x + (end_x - start_x) * t
                y = start_y + (end_y - start_y) * t
                
                animation_path.append((x, y))
        
        return animation_path
    
    def update_animations(self):
        """Update all piece animations."""
        # Update fox animations
        completed_fox_animations = []
        for target_node, animation_data in self.fox_animations.items():
            animation_data['progress'] += self.animation_speed
            if animation_data['progress'] >= 1.0:
                completed_fox_animations.append(target_node)
        
        # Remove completed fox animations
        for target_node in completed_fox_animations:
            self.fox_animations.pop(target_node)
        
        # Update snake animations
        completed_snake_animations = []
        for target_node, animation_data in self.snake_animations.items():
            animation_data['progress'] += self.animation_speed
            if animation_data['progress'] >= 1.0:
                completed_snake_animations.append(target_node)
        
        # Remove completed snake animations
        for target_node in completed_snake_animations:
            self.snake_animations.pop(target_node)
    
    def get_fox_position(self, fox_node):
        """
        Get the current position of a fox piece, considering animations.
        
        Args:
            fox_node: The fox node
            
        Returns:
            The current (x, y) position
        """
        # Check if this fox is being animated
        for target_node, animation_data in self.fox_animations.items():
            if target_node == fox_node:
                # Get the position from the animation path
                path = animation_data['path']
                progress = animation_data['progress']
                
                # Calculate the index in the animation path
                path_index = min(int(progress * len(path)), len(path) - 1)
                
                # Return the position at that index
                return path[path_index]
        
        # If not being animated, return the node's position
        x, y = fox_node.get_position()
        
        # Apply offset for center node to prevent overlap with other pieces
        if fox_node == self.center_node:
            # Check if there are other pieces on the center node
            other_pieces = 0
            
            # Count player pieces on center
            for player_node in self.player_pieces:
                if player_node.x == self.center_node.x and player_node.y == self.center_node.y:
                    other_pieces += 1
            
            # Count snake pieces on center
            for snake_node in self.snake_pieces:
                if snake_node.x == self.center_node.x and snake_node.y == self.center_node.y:
                    other_pieces += 1
            
            # Apply offset based on the number of other pieces
            # Position fox at the top of the center node
            x += 0
            y -= 15
        
        return (x, y)
    
    def get_snake_position(self, snake_node):
        """
        Get the current position of a snake piece, considering animations.
        
        Args:
            snake_node: The snake node
            
        Returns:
            The current (x, y) position
        """
        # Check if this snake is being animated
        for target_node, animation_data in self.snake_animations.items():
            if target_node == snake_node:
                # Get the position from the animation path
                path = animation_data['path']
                progress = animation_data['progress']
                
                # Calculate the index in the animation path
                path_index = min(int(progress * len(path)), len(path) - 1)
                
                # Return the position at that index
                return path[path_index]
        
        # If not being animated, return the node's position
        x, y = snake_node.get_position()
        
        # Apply offset for center node to prevent overlap with other pieces
        if snake_node == self.center_node:
            # Check if there are other pieces on the center node
            other_pieces = 0
            
            # Count player pieces on center
            for player_node in self.player_pieces:
                if player_node.x == self.center_node.x and player_node.y == self.center_node.y:
                    other_pieces += 1
            
            # Count fox pieces on center
            for fox_node in self.fox_pieces:
                if fox_node.x == self.center_node.x and fox_node.y == self.center_node.y:
                    other_pieces += 1
            
            # Apply offset based on the number of other pieces
            # Position snake at the bottom of the center node
            x += 0
            y += 15
        
        return (x, y)
    
    def render(self, screen: pygame.Surface) -> None:
        """
        Render the board on the screen.
        
        Args:
            screen: The pygame surface to render on
        """
        # Draw circles
        for circle_idx in range(1, self.num_circles):  # Skip innermost circle (it's just a node)
            circle_radius = (circle_idx + 1) * self.circle_spacing
            pygame.draw.circle(
                screen,
                (0, 0, 0),  # Black
                (self.center_x, self.center_y),
                circle_radius,
                1  # Line width
            )
            
            # Add text around the outermost circle
            if circle_idx == self.num_circles - 1:
                # Define the four phrases to display
                phrases = [
                    "Curage to strengthen",
                    "Iron to bind",
                    "Music to dazzle",
                    "Fire to blind"
                ]
                
                # Create font for the text - increased font size
                text_font = pygame.font.SysFont(None, 30)
                
                # Position the text at top-left, top-right, bottom-right, bottom-left positions around the circle
                # Exact corner angles (in radians)
                corner_angles = [
                    math.pi * 5 / 4,  # top-left (135 degrees)
                    math.pi * 7 / 4,  # top-right (315 degrees)
                    math.pi / 4,      # bottom-right (45 degrees)
                    math.pi * 3 / 4   # bottom-left (225 degrees)
                ]
                
                # Add more distance from the circle
                text_radius = circle_radius + 40  # Increased from 25 to 40
                
                for i, phrase in enumerate(phrases):
                    # Calculate the total angle span for the phrase
                    # Use a fixed angle span to ensure consistent spacing
                    total_angle_span = math.pi / 6  # 30 degrees
                    
                    # Calculate the start angle (so the middle of the phrase is at the corner)
                    center_angle = corner_angles[i]
                    start_angle = center_angle - total_angle_span / 2
                    
                    # Ensure consistent character spacing by using the same spacing for all phrases
                    char_angle = total_angle_span / max(len(phrases[0]), len(phrases[1]), len(phrases[2]), len(phrases[3]))
                    
                    # Adjust start angle to center the phrase
                    start_angle = center_angle - (char_angle * len(phrase)) / 2
                    
                    # Render each character separately
                    for j, char in enumerate(phrase):
                        # Calculate the angle for this character - use consistent spacing
                        angle = start_angle + char_angle * j
                        
                        # Render the character
                        char_surface = text_font.render(char, True, (50, 50, 50))
                        
                        # Calculate position for the character
                        char_x = self.center_x + text_radius * math.cos(angle)
                        char_y = self.center_y + text_radius * math.sin(angle)
                        
                        # Calculate rotation angle for radial text
                        rotation_angle = angle + math.pi/2
                        
                        # Rotate the character so the bottom points toward the center
                        rotated_surface = pygame.transform.rotate(
                            char_surface, 
                            -rotation_angle * 180 / math.pi  # Convert to degrees and negate for pygame rotation
                        )
                        
                        # Position the rotated text correctly (centered at the calculated position)
                        screen.blit(rotated_surface, (
                            char_x - rotated_surface.get_width() / 2,
                            char_y - rotated_surface.get_height() / 2
                        ))
        
        # Draw connecting arcs between adjacent nodes in the same circle (skip innermost)
        for circle_idx in range(1, self.num_circles):
            circle_nodes = self.nodes[circle_idx]
            direction = self.circle_directions[circle_idx]
            
            for i in range(len(circle_nodes)):
                start_node = circle_nodes[i]
                end_node = circle_nodes[(i + 1) % len(circle_nodes)]
                
                # Get start and end positions
                start_pos = start_node.get_position()
                end_pos = end_node.get_position()
                
                # Calculate center point of the circle
                center = (self.center_x, self.center_y)
                
                # Calculate radius of this circle
                radius = (circle_idx + 1) * self.circle_spacing
                
                # Calculate angles for the arc
                start_angle = math.atan2(start_pos[1] - center[1], start_pos[0] - center[0])
                end_angle = math.atan2(end_pos[1] - center[1], end_pos[0] - center[0])
                
                # Ensure we draw the arc in the correct direction
                if direction == 1:  # Clockwise
                    if end_angle > start_angle:
                        end_angle -= 2 * math.pi
                else:  # Counter-clockwise
                    if start_angle > end_angle:
                        start_angle -= 2 * math.pi
                
                # We don't draw arcs between nodes anymore - the plain circles are sufficient
                
                # Draw direction triangle at the midpoint of the arc
                if direction == 1:  # Clockwise
                    mid_angle = (start_angle + end_angle) / 2
                else:  # Counter-clockwise
                    mid_angle = (end_angle + start_angle) / 2
                
                # Calculate position for the triangle
                mid_point = (center[0] + radius * math.cos(mid_angle), 
                             center[1] + radius * math.sin(mid_angle))
                
                # Calculate direction tangent to the circle (in the direction of movement)
                if direction == 1:  # Clockwise
                    dir_angle = mid_angle + math.pi / 2  # Tangent in clockwise direction
                else:  # Counter-clockwise
                    dir_angle = mid_angle - math.pi / 2  # Tangent in counter-clockwise direction
                
                # Calculate triangle points
                triangle_size = 5
                triangle_tip = (mid_point[0] + triangle_size * math.cos(dir_angle),
                                mid_point[1] + triangle_size * math.sin(dir_angle))
                
                side_angle1 = dir_angle + 2.5
                side_angle2 = dir_angle - 2.5
                triangle_side1 = (mid_point[0] + triangle_size * math.cos(side_angle1),
                                  mid_point[1] + triangle_size * math.sin(side_angle1))
                triangle_side2 = (mid_point[0] + triangle_size * math.cos(side_angle2),
                                  mid_point[1] + triangle_size * math.sin(side_angle2))
                
                # Draw the triangle
                pygame.draw.polygon(screen, (0, 0, 0), [triangle_tip, triangle_side1, triangle_side2])
        
        # Draw connecting lines between center node and first circle with direction triangles
        center_node = self.center_node
        for node_idx, node in enumerate(self.nodes[1]):  # Nodes in the first circle
            # Draw line
            start_pos = center_node.get_position()
            end_pos = node.get_position()
            pygame.draw.line(
                screen,
                (0, 0, 0),  # Black
                start_pos,
                end_pos,
                1
            )
            
            # Draw diamond to indicate bidirectional movement
            # Calculate midpoint of the line
            mid_x = (start_pos[0] + end_pos[0]) / 2
            mid_y = (start_pos[1] + end_pos[1]) / 2
            
            # Calculate direction vector
            dir_x = end_pos[0] - start_pos[0]
            dir_y = end_pos[1] - start_pos[1]
            
            # Normalize direction vector
            length = math.sqrt(dir_x**2 + dir_y**2)
            if length > 0:
                dir_x /= length
                dir_y /= length
            
            # Calculate perpendicular vector
            perp_x = -dir_y
            perp_y = dir_x
            
            # Calculate diamond points - make it more skinny by reducing perpendicular size
            diamond_size_long = 7  # Longer in the direction of the line
            diamond_size_short = 3  # Shorter in the perpendicular direction
            diamond_point1 = (mid_x + diamond_size_long * dir_x, mid_y + diamond_size_long * dir_y)
            diamond_point2 = (mid_x + diamond_size_short * perp_x, mid_y + diamond_size_short * perp_y)
            diamond_point3 = (mid_x - diamond_size_long * dir_x, mid_y - diamond_size_long * dir_y)
            diamond_point4 = (mid_x - diamond_size_short * perp_x, mid_y - diamond_size_short * perp_y)
            
            # Draw the diamond
            pygame.draw.polygon(screen, (0, 0, 0), [diamond_point1, diamond_point2, diamond_point3, diamond_point4])
        
        # Draw connecting lines between other circles with direction triangles
        for circle_idx in range(1, self.num_circles - 1):
            for node_idx in range(len(self.nodes[circle_idx])):
                inner_node = self.nodes[circle_idx][node_idx]
                # Find the corresponding node in the next circle
                outer_node_idx = node_idx % len(self.nodes[circle_idx + 1])
                outer_node = self.nodes[circle_idx + 1][outer_node_idx]
                
                # Draw line
                start_pos = inner_node.get_position()
                end_pos = outer_node.get_position()
                pygame.draw.line(
                    screen,
                    (0, 0, 0),  # Black
                    start_pos,
                    end_pos,
                    1
                )
                
                # Draw diamond to indicate bidirectional movement
                # Calculate midpoint of the line
                mid_x = (start_pos[0] + end_pos[0]) / 2
                mid_y = (start_pos[1] + end_pos[1]) / 2
                
                # Calculate direction vector
                dir_x = end_pos[0] - start_pos[0]
                dir_y = end_pos[1] - start_pos[1]
                
                # Normalize direction vector
                length = math.sqrt(dir_x**2 + dir_y**2)
                if length > 0:
                    dir_x /= length
                    dir_y /= length
                
                # Calculate perpendicular vector
                perp_x = -dir_y
                perp_y = dir_x
                
                # Calculate diamond points - make it more skinny by reducing perpendicular size
                diamond_size_long = 7  # Longer in the direction of the line
                diamond_size_short = 3  # Shorter in the perpendicular direction
                diamond_point1 = (mid_x + diamond_size_long * dir_x, mid_y + diamond_size_long * dir_y)
                diamond_point2 = (mid_x + diamond_size_short * perp_x, mid_y + diamond_size_short * perp_y)
                diamond_point3 = (mid_x - diamond_size_long * dir_x, mid_y - diamond_size_long * dir_y)
                diamond_point4 = (mid_x - diamond_size_short * perp_x, mid_y - diamond_size_short * perp_y)
                
                # Draw the diamond
                pygame.draw.polygon(screen, (0, 0, 0), [diamond_point1, diamond_point2, diamond_point3, diamond_point4])
        
        # Draw each node
        for circle_idx in range(self.num_circles):
            for node_idx in range(len(self.nodes[circle_idx])):
                node = self.nodes[circle_idx][node_idx]
                
                # Use the same color for all nodes
                color = self.normal_color
                
                # Draw node circle - center node is bigger
                radius = self.center_node_radius if node == self.center_node else self.node_radius
                pygame.draw.circle(screen, color, node.get_position(), radius)
                pygame.draw.circle(screen, (0, 0, 0), node.get_position(), radius, 1)  # Border
        
        # Draw fox pieces
        for fox_node in self.fox_pieces:
            # Get the current position (either animated or static)
            x, y = self.get_fox_position(fox_node)
            
            # Draw fox piece as a red triangle pointing toward the center
            size = self.node_radius * 0.8
            
            # Calculate vector from this node to the center
            center_x, center_y = self.center_x, self.center_y
            dx, dy = center_x - x, center_y - y
            
            # Normalize the vector
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                dx, dy = dx/length, dy/length
            
            # Calculate triangle points with the tip pointing toward center
            tip_x = x + dx * size
            tip_y = y + dy * size
            
            # Calculate perpendicular vector for the base
            perp_x, perp_y = -dy, dx
            
            # Calculate the base points
            base1_x = x - dx * size/2 + perp_x * size/2
            base1_y = y - dy * size/2 + perp_y * size/2
            base2_x = x - dx * size/2 - perp_x * size/2
            base2_y = y - dy * size/2 - perp_y * size/2
            
            # Draw the triangle
            pygame.draw.polygon(
                screen, 
                self.fox_piece_color, 
                [(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)]
            )
            # Draw border
            pygame.draw.polygon(
                screen, 
                (0, 0, 0), 
                [(tip_x, tip_y), (base1_x, base1_y), (base2_x, base2_y)],
                1
            )
        
        # Draw snake pieces
        for snake_node in self.snake_pieces:
            # Get the current position (either animated or static)
            x, y = self.get_snake_position(snake_node)
            
            # Draw snake piece as a green squiggle like in the dice, but rotated to face center
            
            # Calculate vector from this node to the center
            center_x, center_y = self.center_x, self.center_y
            dx, dy = center_x - x, center_y - y
            
            # Normalize the vector
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                dx, dy = dx/length, dy/length
            
            # Calculate perpendicular vector for the sine wave
            perp_x, perp_y = -dy, dx
            
            # Draw the squiggle as a series of connected points
            points = []
            num_segments = 10
            amplitude = self.node_radius * 0.4
            squiggle_length = self.node_radius * 1.6
            
            # Calculate start and end points along the vector to center
            start_x = x - dx * squiggle_length/2  # Start away from center
            start_y = y - dy * squiggle_length/2
            end_x = x + dx * squiggle_length/2    # End toward center (head)
            end_y = y + dy * squiggle_length/2
            
            for i in range(num_segments + 1):
                # Interpolate position along the line from start to end
                segment_x = start_x + (end_x - start_x) * i / num_segments
                segment_y = start_y + (end_y - start_y) * i / num_segments
                
                # Add sine wave perpendicular to the direction
                offset_x = amplitude * math.sin(i * math.pi / 2) * perp_x
                offset_y = amplitude * math.sin(i * math.pi / 2) * perp_y
                
                points.append((segment_x + offset_x, segment_y + offset_y))
            
            # Draw the squiggle
            if len(points) >= 2:
                pygame.draw.lines(screen, self.snake_piece_color, False, points, 3)
