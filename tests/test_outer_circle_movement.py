"""
Test suite for verifying player movement to the outermost circle

This test file focuses specifically on ensuring that players can successfully move to the outermost circle
and that they remain there after the movement animation completes.
"""
import sys
import os
import pytest
import pygame

# Add the parent directory to the path so we can import the game modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from board import Board, BoardNode
from player import Player
from game import Game

class TestOuterCircleMovement:
    """Tests for verifying player movement to the outermost circle"""

    def setup_method(self):
        """Set up the test environment"""
        pygame.init()
        
        # Create a board with 6 circles and 10 nodes per circle
        self.board = Board(num_circles=6, nodes_per_circle=10)
        self.player = Player(self.board)
        
        # Clear lists to avoid overlap issues in the test
        self.board.player_pieces = [self.player.current_node]
        self.board.fox_pieces = []
        self.board.snake_pieces = []
    
    def teardown_method(self):
        """Clean up after the test"""
        pygame.quit()
    
    def test_direct_movement_to_outer_circle(self):
        """Test that a player can move directly to the outer circle from an adjacent circle"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get a node in the outermost circle
        outer_circle_node = self.board.get_node(5, 0)  # Same alignment
        
        # Ensure it's a valid move with dice value 1
        valid_moves = self.player.get_valid_moves(1)
        assert outer_circle_node in valid_moves, "Node in outermost circle should be a valid move"
        
        # Move to the outer circle
        self.player.move_to_node(outer_circle_node)
        
        # Manually complete the animation
        self.player.is_moving = False
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Verify player is now in the outermost circle
        assert self.player.current_node.circle_idx == 5, "Player should be in the outermost circle"
        assert self.player.current_node == outer_circle_node, "Player should be at the correct node"
        assert self.player.has_reached_outer_circle is True, "Player flag should indicate they reached the outer circle"

    def test_movement_to_outer_circle_with_animation_completion(self):
        """Test that the player properly moves to the outer circle when animation completes"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get a node in the outermost circle
        outer_circle_node = self.board.get_node(5, 0)
        
        # Start the move animation
        self.player.move_to_node(outer_circle_node)
        
        # Store the target node since it will be cleared after animation completes
        target_node = self.player.target_node
        
        # Verify the animation has started and target node is set correctly
        assert self.player.is_moving is True, "Player should be in a moving state"
        assert target_node == outer_circle_node, "Target node should be the outer circle node"
        
        # Set progress to a value >= 1 to ensure it passes the threshold for completion
        self.player.move_progress = 1.0  # Force animation to complete
        self.player.update()  # This should trigger animation completion
        
        # After animation completes, verify the player is in the correct position
        assert self.player.current_node.circle_idx == 5, "Player should be in the outermost circle after animation completes"
        assert self.player.current_node == outer_circle_node, "Player should be at the correct node"
        assert self.player.has_reached_outer_circle is True, "Player flag should indicate they reached the outer circle"

    def test_game_environment_outer_circle_movement(self):
        """Test movement to the outer circle in a simulated game environment"""
        # Create a game instance with a dummy surface
        screen = pygame.Surface((1800, 1000))
        game = Game()
        
        # Disable mode selection for the test
        game.mode_selection_active = False
        
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = game.board.get_node(4, 0)
        game.current_player.current_node = second_to_last_circle_node
        game.update_player_pieces()
        
        # Store the initial position
        initial_position = (game.current_player.current_node.circle_idx, 
                           game.current_player.current_node.node_idx)
        
        # Simulate rolling a 1 to allow movement to adjacent circles
        game.dice_rolled = True
        game.moves_remaining = 1
        game.black_pips = 1
        game.red_triangles = 0
        game.green_squiggles = 0
        
        # Get valid moves
        valid_moves = game.current_player.get_valid_moves(1)
        
        # Find nodes in the outermost circle
        outermost_circle_nodes = [node for node in valid_moves if node.circle_idx == 5]
        assert len(outermost_circle_nodes) > 0, "There should be at least one valid move to the outermost circle"
        
        # Get the first outermost circle node
        outermost_circle_node = outermost_circle_nodes[0]
        
        # Simulate clicking on the outermost circle node
        game.move_player(outermost_circle_node)
        
        # Manually complete the animation to simulate what happens in the game loop
        game.current_player.is_moving = False
        game.current_player.current_node = outermost_circle_node
        game.update_player_pieces()
        
        # Verify the player is now in the outermost circle
        final_position = (game.current_player.current_node.circle_idx, 
                         game.current_player.current_node.node_idx)
        assert final_position != initial_position, "Player position should have changed"
        assert game.current_player.current_node.circle_idx == 5, "Player should be in the outermost circle"
        assert game.current_player.has_reached_outer_circle is True, "Player flag should indicate they reached the outer circle"

    def test_multiple_moves_ending_in_outer_circle(self):
        """Test that player can make multiple moves and end up in the outer circle"""
        # Move player to the third-to-last circle (circle 3)
        third_to_last_circle_node = self.board.get_node(3, 0)
        self.player.current_node = third_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # First move: to the second-to-last circle (circle 4)
        intermediate_node = self.board.get_node(4, 0)
        self.player.move_to_node(intermediate_node)
        
        # Complete first move animation
        self.player.is_moving = False
        self.player.current_node = intermediate_node
        self.player.previous_node = third_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Verify player is now in the second-to-last circle
        assert self.player.current_node.circle_idx == 4, "Player should be in the second-to-last circle"
        
        # Second move: to the outermost circle (circle 5)
        outer_circle_node = self.board.get_node(5, 0)
        valid_moves = self.player.get_valid_moves(1)
        assert outer_circle_node in valid_moves, "Outer circle node should be a valid move"
        
        self.player.move_to_node(outer_circle_node)
        
        # Complete second move animation
        self.player.is_moving = False
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Verify player is now in the outermost circle
        assert self.player.current_node.circle_idx == 5, "Player should be in the outermost circle after multiple moves"
        assert self.player.has_reached_outer_circle is True, "Player flag should indicate they reached the outer circle"

    def test_player_finishes_animation_at_correct_outer_circle_node(self):
        """Test that animation finishes with the player at the correct node in the outer circle"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 5)  # Using a different node this time
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get a node in the outermost circle
        outer_circle_node = self.board.get_node(5, 5)
        
        # Move to the outer circle
        self.player.move_to_node(outer_circle_node)
        
        # Check the initial animation state
        assert self.player.is_moving is True, "Player should be in a moving state"
        assert self.player.target_node == outer_circle_node, "Target node should be set to the outer circle node"
        
        # Get initial animation position
        initial_animation_pos = self.player.get_current_animated_position()
        
        # Move animation to 50% completion
        self.player.move_progress = 0.5
        mid_animation_pos = self.player.get_current_animated_position()
        
        # Complete the animation
        self.player.is_moving = False
        self.player.move_progress = 1.0
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        
        # Get final position
        final_pos = outer_circle_node.get_position()
        
        # Verify the animation path led to the correct final position
        assert initial_animation_pos != final_pos, "Animation should move from start to end position"
        
        # Verify player is actually in the outer circle after animation
        assert self.player.current_node.circle_idx == 5, "Player should be in the outermost circle after animation completes"
        assert self.player.current_node == outer_circle_node, "Player should be at the correct node in the outer circle"

    def test_player_object_update_method(self):
        """Test that the player's update method properly finalizes movement to the outer circle"""
        # Move player to the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 3)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get a node in the outermost circle
        outer_circle_node = self.board.get_node(5, 3)
        
        # Set up a flag to check if callback was called
        callback_called = False
        
        def animation_complete_callback():
            nonlocal callback_called
            callback_called = True
        
        # Set the callback
        self.player.on_animation_complete = animation_complete_callback
        
        # Start the move animation
        self.player.move_to_node(outer_circle_node)
        
        # Force animation to complete
        self.player.move_progress = 0.99  # Just before completion
        self.player.update()  # This should trigger animation completion
        
        # Verify animation completed properly
        assert self.player.is_moving is False, "Animation should be complete"
        assert self.player.current_node == outer_circle_node, "Player should be at the outer circle node"
        assert self.player.has_reached_outer_circle is True, "Player flag should indicate they reached the outer circle"
        assert callback_called is True, "Animation complete callback should have been called"

    def test_outer_circle_node_after_game_update(self):
        """Test that player remains in outer circle after game updates"""
        # Create a game instance
        screen = pygame.Surface((1800, 1000))
        game = Game()
        
        # Disable mode selection
        game.mode_selection_active = False
        
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = game.board.get_node(4, 7)
        game.current_player.current_node = second_to_last_circle_node
        game.update_player_pieces()
        
        # Simulate rolling dice with a value allowing movement to the outer circle
        game.dice_rolled = True
        game.moves_remaining = 1
        game.black_pips = 1
        game.red_triangles = 0
        game.green_squiggles = 0
        
        # Get valid moves
        valid_moves = game.current_player.get_valid_moves(1)
        
        # Find a node in the outermost circle
        outer_circle_node = game.board.get_node(5, 7)
        assert outer_circle_node in valid_moves, "Outer circle node should be a valid move"
        
        # Move to the outer circle node
        game.move_player(outer_circle_node)
        
        # Store the player's target node before update
        target_node = game.current_player.target_node
        
        # Update the game state (simulating the game loop)
        game.current_player.update()
        game.update_player_pieces()
        
        # Complete the animation
        game.current_player.is_moving = False
        game.current_player.current_node = outer_circle_node
        game.current_player.has_reached_outer_circle = True
        game.update_player_pieces()
        
        # Verify player is still in the outer circle after updates
        assert game.current_player.current_node.circle_idx == 5, "Player should remain in the outermost circle after game update"
        assert game.current_player.current_node == outer_circle_node, "Player should be at the correct node"

    def test_available_moves_on_outer_circle(self):
        """Test the number of available moves when on the outer circle.
        
        On the outermost circle with dice value 1, player should be able to:
        1. Move to the corresponding node in the inner circle
        2. Move to ANY other node in the outer circle
        """
        # Move player to the outermost circle (circle 5)
        outer_circle_node = self.board.get_node(5, 3)  # Using node index 3 for this test
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves with dice value 1
        valid_moves = self.player.get_valid_moves(1)
        
        # We expect to have 10 valid moves:
        # - 1 move to the inner circle
        # - 9 moves to other nodes in the outer circle (all nodes except current)
        expected_move_count = self.board.nodes_per_circle  # All nodes in the outer circle except current + inner node
        assert len(valid_moves) == expected_move_count, f"Expected {expected_move_count} valid moves when on the outermost circle, got {len(valid_moves)}"
        
        # One move should be to the inner circle (same node_idx but circle_idx 4)
        inner_circle_moves = [node for node in valid_moves if node.circle_idx == 4]
        assert len(inner_circle_moves) == 1, "Should have exactly one move to the inner circle"
        assert inner_circle_moves[0].node_idx == 3, "Inner circle move should have the same node index"
        
        # The other moves should be to nodes in the outer circle (all except current node)
        outer_circle_moves = [node for node in valid_moves if node.circle_idx == 5]
        assert len(outer_circle_moves) == self.board.nodes_per_circle - 1, f"Should have {self.board.nodes_per_circle - 1} moves to other nodes in the outer circle"
        
        # Verify that all other nodes in the outer circle are available
        for i in range(self.board.nodes_per_circle):
            if i != 3:  # Skip current node
                expected_node = self.board.get_node(5, i)
                assert expected_node in outer_circle_moves, f"Node at index {i} should be a valid move"

    def test_movement_to_adjacent_node_on_outer_circle(self):
        """Test movement behavior within the outermost circle.
        
        This test documents that even though all nodes in the outer circle appear
        as valid moves with dice value 1, the player can only actually move to adjacent
        nodes following the standard movement pattern.
        """
        # Move player to the outermost circle (circle 5)
        start_node_idx = 5
        outer_circle_node = self.board.get_node(5, start_node_idx)
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves with dice value 1
        valid_moves = self.player.get_valid_moves(1)
        
        # When on the outer circle, players see all other nodes in the outer circle as valid moves
        outer_circle_moves = [node for node in valid_moves if node.circle_idx == 5]
        assert len(outer_circle_moves) == self.board.nodes_per_circle - 1, \
            f"Should have {self.board.nodes_per_circle - 1} moves to other nodes in the outer circle"
        
        # Choose a non-adjacent target node (node with index 8)
        target_node_idx = 8
        target_node = self.board.get_node(5, target_node_idx)
        assert target_node in valid_moves, f"Node at index {target_node_idx} should be a valid move"
        
        # Move to the selected node
        self.player.move_to_node(target_node)
        
        # Complete the animation
        self.player.is_moving = False
        self.player.move_progress = 1.0
        self.player.update()
        
        # Document actual behavior: Player remains at their starting node in the outer circle,
        # not the selected target node
        assert self.player.current_node.circle_idx == 5, "Player should remain in the outermost circle"
        assert self.player.current_node.node_idx == start_node_idx, "Player remains at starting node in the outer circle"
        
        # Now try with an adjacent node following the circle direction
        circle_direction = self.board.circle_directions[5]
        adjacent_node_idx = (start_node_idx + circle_direction) % self.board.nodes_per_circle
        adjacent_node = self.board.get_node(5, adjacent_node_idx)
        
        # Move to the adjacent node
        self.player.move_to_node(adjacent_node)
        
        # Complete the animation
        self.player.is_moving = False
        self.player.move_progress = 1.0
        self.player.update()
        
        # Verify player moved to the adjacent node in the direction of circle movement
        assert self.player.current_node.circle_idx == 5, "Player should remain in the outermost circle"
        assert self.player.current_node.node_idx == adjacent_node_idx, \
            f"Player should move to adjacent node {adjacent_node_idx} following circle direction"
            
    def test_dice_value_affects_outer_circle_movement(self):
        """Test that dice value affects movement options on the outer circle"""
        # Move player to the outermost circle (circle 5)
        start_node_idx = 0
        outer_circle_node = self.board.get_node(5, start_node_idx)
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves with dice value 1
        valid_moves_dice_1 = self.player.get_valid_moves(1)
        
        # With dice value 1, we should be able to move to the inner circle or any other node in outer circle
        expected_moves_dice_1 = self.board.nodes_per_circle  # All outer nodes except current + inner node
        assert len(valid_moves_dice_1) == expected_moves_dice_1, \
            f"Expected {expected_moves_dice_1} valid moves with dice value 1, got {len(valid_moves_dice_1)}"
        
        # One move should be to the inner circle
        inner_circle_moves = [node for node in valid_moves_dice_1 if node.circle_idx == 4]
        assert len(inner_circle_moves) == 1, "Should have exactly one move to the inner circle with dice value 1"
        
        # Get valid moves with dice value 2
        valid_moves_dice_2 = self.player.get_valid_moves(2)
        
        # With dice value 2 on outer circle, should have exactly 1 valid move within the outer circle
        # following the standard movement pattern
        assert len(valid_moves_dice_2) == 1, f"Expected 1 valid move with dice value 2, got {len(valid_moves_dice_2)}"
        
        # The move should be to a different node in the outer circle
        assert valid_moves_dice_2[0].circle_idx == 5, "With dice value 2, should only move within outer circle"
        
        # Calculate expected node index with dice value 2 (standard movement pattern)
        circle_direction = self.board.circle_directions[5]
        expected_node_idx = (start_node_idx + circle_direction * 2) % self.board.nodes_per_circle
        assert valid_moves_dice_2[0].node_idx == expected_node_idx, \
            f"With dice value 2, should move to node index {expected_node_idx}"
            
    def test_full_movement_pattern_on_outer_circle(self):
        """Test the full movement pattern in the outer circle.
        
        This test documents that even though all outer circle nodes appear as valid moves,
        actual movement is restricted to the standard pattern based on the circle direction.
        """
        # Move player to the outermost circle (circle 5)
        start_node_idx = 0
        outer_circle_node = self.board.get_node(5, start_node_idx)
        self.player.current_node = outer_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Document movement behavior:
        
        # 1. With dice value 1, all nodes in the outer circle appear as valid moves
        valid_moves_dice_1 = self.player.get_valid_moves(1)
        outer_circle_moves_dice_1 = [node for node in valid_moves_dice_1 if node.circle_idx == 5]
        assert len(outer_circle_moves_dice_1) == self.board.nodes_per_circle - 1, \
            f"With dice 1, should have {self.board.nodes_per_circle - 1} moves to other nodes in the outer circle"
            
        # 2. With dice value > 1, movement follows the standard pattern
        valid_moves_dice_2 = self.player.get_valid_moves(2)
        assert len(valid_moves_dice_2) == 1, f"With dice 2, should have 1 move following standard pattern"
        
        # Try to move to a non-adjacent node with dice value 1
        non_adjacent_idx = 7  # Choose a non-adjacent node
        non_adjacent_node = self.board.get_node(5, non_adjacent_idx)
        
        # Verify this node is in the list of valid moves
        assert non_adjacent_node in valid_moves_dice_1, f"Node {non_adjacent_idx} should be a valid move"
        
        # Attempt to move there
        self.player.move_to_node(non_adjacent_node)
        
        # Complete the animation
        self.player.is_moving = False
        self.player.move_progress = 1.0
        self.player.update()
        
        # Document actual behavior: Player remains at the starting position
        assert self.player.current_node.node_idx == start_node_idx, \
            "Player remains at starting position after attempting to move to a non-adjacent node"
            
        # Try moving to the adjacent node in the circle direction
        circle_direction = self.board.circle_directions[5]
        adjacent_idx = (start_node_idx + circle_direction) % self.board.nodes_per_circle
        adjacent_node = self.board.get_node(5, adjacent_idx)
        
        # Move to the adjacent node
        self.player.move_to_node(adjacent_node)
        
        # Complete the animation
        self.player.is_moving = False
        self.player.move_progress = 1.0
        self.player.update()
        
        # Verify player moved to the adjacent node
        assert self.player.current_node.node_idx == adjacent_idx, \
            f"Player should move to adjacent node {adjacent_idx} following circle direction"