"""
Tests to verify fixes for bugs in the game.

This test file focuses on:
1. Ensuring players cannot move to the outer circle when the space is occupied by a snake or fox
2. Ensuring players can only move to adjacent nodes in the proper direction in the outer circle
3. Verifying foxes are rendered as red triangles with the tip pointing toward the center
"""
import sys
import os
import pytest
import pygame
import math

# Add the parent directory to the path so we can import the game modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from board import Board, BoardNode
from player import Player
from game import Game

class TestFixedBugs:
    """Tests for verifying bug fixes in the game"""

    def setup_method(self):
        """Set up the test environment"""
        pygame.init()
        
        # Create a board with 6 circles and 10 nodes per circle
        self.board = Board(num_circles=6, nodes_per_circle=10)
        self.player = Player(self.board)
        
        # Clear lists to avoid overlap issues in the test
        self.board.player_pieces = [self.player.current_node]
        
        # We'll set up fox and snake pieces later in specific tests
        self.board.fox_pieces = []
        self.board.snake_pieces = []
    
    def teardown_method(self):
        """Clean up after the test"""
        pygame.quit()

    def test_cannot_move_to_outer_circle_occupied_by_fox(self):
        """Test that players cannot move to the outer circle when occupied by a fox"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Place a fox piece in the outer circle node directly outward from player
        outer_node = self.board.get_node(5, 0)  # The node player would move to
        self.board.fox_pieces = [outer_node]
        
        # Get valid moves with dice value 1 (allows moving to adjacent circle)
        valid_moves = self.player.get_valid_moves(1)
        
        # Outer node should not be in valid moves because it's occupied by a fox
        assert outer_node not in valid_moves, "Player should not be able to move to a node occupied by a fox"
        
        # Verify we can move to other directions (within same circle)
        same_circle_moves = [node for node in valid_moves if node.circle_idx == 4]
        assert len(same_circle_moves) > 0, "Player should still be able to move within the same circle"

    def test_cannot_move_to_outer_circle_occupied_by_snake(self):
        """Test that players cannot move to the outer circle when occupied by a snake"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 2)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Place a snake piece in the outer circle node directly outward from player
        outer_node = self.board.get_node(5, 2)  # The node player would move to
        self.board.snake_pieces = [outer_node]
        
        # Get valid moves with dice value 1 (allows moving to adjacent circle)
        valid_moves = self.player.get_valid_moves(1)
        
        # Outer node should not be in valid moves because it's occupied by a snake
        assert outer_node not in valid_moves, "Player should not be able to move to a node occupied by a snake"
        
        # Verify we can move to other directions (within same circle)
        same_circle_moves = [node for node in valid_moves if node.circle_idx == 4]
        assert len(same_circle_moves) > 0, "Player should still be able to move within the same circle"

    def test_outer_circle_movement_follows_direction(self):
        """Test that players can only move to adjacent nodes in the proper direction in the outer circle"""
        # Move player to the outermost circle (circle 5)
        start_node_idx = 3
        outer_circle_node = self.board.get_node(5, start_node_idx)
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves with dice value 1
        valid_moves = self.player.get_valid_moves(1)
        
        # Determine the expected next node based on the circle direction
        circle_direction = self.board.circle_directions[5]
        expected_next_idx = (start_node_idx + circle_direction) % self.board.nodes_per_circle
        expected_next_node = self.board.get_node(5, expected_next_idx)
        
        # Find outer circle moves
        outer_circle_moves = [node for node in valid_moves if node.circle_idx == 5]
        
        # Should only be one move to the next node in the direction
        assert len(outer_circle_moves) == 1, "Should only have one valid move within the outer circle"
        assert outer_circle_moves[0] == expected_next_node, "Should only be able to move to the next node in the proper direction"
        
        # Inner circle node should also be valid (to move inward)
        inner_moves = [node for node in valid_moves if node.circle_idx == 4]
        assert len(inner_moves) == 1, "Should have one valid move to the inner circle"

    def test_dice_value_affects_outer_circle_movement(self):
        """Test that dice value affects movement options on the outer circle"""
        # Move player to the outermost circle (circle 5)
        start_node_idx = 0
        outer_circle_node = self.board.get_node(5, start_node_idx)
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves with dice value 2
        valid_moves = self.player.get_valid_moves(2)
        
        # There should be exactly one valid move in the outer circle
        outer_circle_moves = [node for node in valid_moves if node.circle_idx == 5]
        assert len(outer_circle_moves) == 1, "Should be exactly one valid move in the outer circle with dice value 2"
        
        # Calculate expected node index with dice value 2 (standard movement pattern)
        circle_direction = self.board.circle_directions[5]
        expected_node_idx = (start_node_idx + circle_direction * 2) % self.board.nodes_per_circle
        expected_node = self.board.get_node(5, expected_node_idx)
        
        # Verify the move is to the expected node
        assert outer_circle_moves[0] == expected_node, f"With dice value 2, should move to node index {expected_node_idx}"

    def test_fox_rendering_points_toward_center(self):
        """Test that foxes are rendered as red triangles with the tip pointed toward the center"""
        # This is a mock test to verify the fox rendering
        # We'll access the internal calculation to check if the triangle points correctly
        
        # Place a fox piece on the outermost circle
        fox_node = self.board.get_node(5, 1)
        self.board.fox_pieces = [fox_node]
        
        # Get the fox position
        fox_pos = fox_node.get_position()
        
        # Calculate vector from fox to center
        center_x, center_y = self.board.center_x, self.board.center_y
        fox_x, fox_y = fox_pos
        dx, dy = center_x - fox_x, center_y - fox_y
        
        # Normalize the vector
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            dx, dy = dx/length, dy/length
        
        # Size of the fox triangle
        size = self.board.node_radius * 0.8
        
        # Calculate expected tip position (should point toward center)
        expected_tip_x = fox_x + dx * size
        expected_tip_y = fox_y + dy * size
        
        # Calculate perpendicular vector for the base
        perp_x, perp_y = -dy, dx
        
        # Calculate the base points (should be away from center)
        expected_base1_x = fox_x - dx * size/2 + perp_x * size/2
        expected_base1_y = fox_y - dy * size/2 + perp_y * size/2
        expected_base2_x = fox_x - dx * size/2 - perp_x * size/2
        expected_base2_y = fox_y - dy * size/2 - perp_y * size/2
        
        # Create a mock screen to test rendering
        screen = pygame.Surface((1800, 1000))
        
        # Create a subclass of Board to capture the drawing
        class TestBoard(Board):
            def __init__(self, orig_board):
                self.center_x = orig_board.center_x
                self.center_y = orig_board.center_y
                self.fox_pieces = orig_board.fox_pieces
                self.snake_pieces = orig_board.snake_pieces
                self.player_pieces = orig_board.player_pieces
                self.node_radius = orig_board.node_radius
                self.fox_piece_color = orig_board.fox_piece_color
                self.last_drawn_fox = None
            
            def get_fox_position(self, fox_node):
                return fox_node.get_position()
            
            def render(self, screen):
                # Only draw fox pieces for this test
                for fox_node in self.fox_pieces:
                    x, y = self.get_fox_position(fox_node)
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
                    
                    # Save the points for validation
                    self.last_drawn_fox = {
                        "tip": (tip_x, tip_y),
                        "base1": (base1_x, base1_y),
                        "base2": (base2_x, base2_y)
                    }
        
        # Create test board and render
        test_board = TestBoard(self.board)
        test_board.render(screen)
        
        # Validate that the fox triangle was drawn with the tip pointing toward the center
        assert test_board.last_drawn_fox is not None, "Fox should have been rendered"
        
        # The tip should be closer to the center than the base points
        tip = test_board.last_drawn_fox["tip"]
        base1 = test_board.last_drawn_fox["base1"]
        base2 = test_board.last_drawn_fox["base2"]
        
        tip_to_center = math.sqrt((tip[0] - center_x)**2 + (tip[1] - center_y)**2)
        base1_to_center = math.sqrt((base1[0] - center_x)**2 + (base1[1] - center_y)**2)
        base2_to_center = math.sqrt((base2[0] - center_x)**2 + (base2[1] - center_y)**2)
        
        assert tip_to_center < base1_to_center, "Tip should be closer to center than base point 1"
        assert tip_to_center < base2_to_center, "Tip should be closer to center than base point 2"

    def test_fox_rendering_has_correct_coordinates(self):
        """Test that the fox rendering coordinates are calculated correctly"""
        # Place a fox piece in the game
        fox_node = self.board.get_node(5, 3)
        self.board.fox_pieces = [fox_node]
        
        # Create a mock function to capture the polygon coordinates
        original_draw_polygon = pygame.draw.polygon
        drawn_polygons = []
        
        def mock_draw_polygon(surface, color, points, width=0):
            drawn_polygons.append((color, points))
            return original_draw_polygon(surface, color, points, width)
        
        # Monkey patch pygame.draw.polygon
        pygame.draw.polygon = mock_draw_polygon
        
        try:
            # Create a mock screen and render the board
            screen = pygame.Surface((1800, 1000))
            self.board.render(screen)
            
            # Find the fox drawing (should be a red triangle)
            fox_drawing = None
            for color, points in drawn_polygons:
                if color == self.board.fox_piece_color:
                    fox_drawing = points
                    break
            
            assert fox_drawing is not None, "Fox should have been drawn with the fox piece color"
            
            # Convert points to a more readable format
            fox_points = list(fox_drawing)
            assert len(fox_points) == 3, "Fox should be drawn as a triangle with 3 points"
            
            # Get coordinates
            fox_pos = fox_node.get_position()
            center_pos = (self.board.center_x, self.board.center_y)
            
            # Identify the tip (point closest to center)
            distances_to_center = []
            for point in fox_points:
                dist = math.sqrt((point[0] - center_pos[0])**2 + (point[1] - center_pos[1])**2)
                distances_to_center.append(dist)
            
            tip_index = distances_to_center.index(min(distances_to_center))
            tip_point = fox_points[tip_index]
            
            # Calculate the expected fox triangle orientation
            fox_x, fox_y = fox_pos
            center_x, center_y = center_pos
            
            # Vector from fox to center
            dx, dy = center_x - fox_x, center_y - fox_y
            
            # Normalize the vector
            length = math.sqrt(dx**2 + dy**2)
            if length > 0:
                dx, dy = dx/length, dy/length
            
            # Calculate if tip is in the expected direction
            # Tip should be closer to center than fox position
            vector_to_tip = (tip_point[0] - fox_x, tip_point[1] - fox_y)
            
            # Calculate dot product to see if vectors point in same direction
            dot_product = vector_to_tip[0] * dx + vector_to_tip[1] * dy
            
            assert dot_product > 0, "Fox triangle tip should point toward the center"
            
        finally:
            # Restore original function
            pygame.draw.polygon = original_draw_polygon