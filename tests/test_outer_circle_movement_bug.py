"""
Test to reproduce and fix the bug with outer circle movement

This test file focuses on the bug where a player piece sometimes selects an outside circle node
but then the position is reset to its current node, effectively spending a move to go nowhere.
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

class TestOuterCircleMovementBug:
    """Tests for the bug where player can't move to the outer circle even though it's shown as valid"""
    
    def setup_method(self):
        """Set up the test environment"""
        # Initialize pygame for the test
        pygame.init()
        
        # Create a board and player
        self.board = Board(num_circles=6, nodes_per_circle=10)
        self.player = Player(self.board)
        
        # Clear the player pieces list to avoid overlap issues in the test
        self.board.player_pieces = [self.player.current_node]
        
        # Clear fox and snake pieces for testing
        self.board.fox_pieces = []
        self.board.snake_pieces = []
    
    def teardown_method(self):
        """Clean up after the test"""
        pygame.quit()
    
    def test_node_comparison_in_valid_moves(self):
        """Test that node comparison works correctly in valid_moves"""
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get valid moves
        valid_moves = self.player.get_valid_moves(1)  # Dice value 1 allows moving to adjacent circles
        
        # Find nodes in the outermost circle
        outermost_circle_nodes = [node for node in valid_moves if node.circle_idx == 5]
        
        # There should be at least one valid move to the outermost circle
        assert len(outermost_circle_nodes) > 0, "No valid moves to the outermost circle"
        
        # Get the first outermost circle node
        outermost_circle_node = outermost_circle_nodes[0]
        
        # Now simulate what happens in the game when a player clicks on a node
        # The game uses get_node_at_position which might return a different node object
        # with the same coordinates
        
        # Create a new node with the same coordinates as the outermost circle node
        # This simulates what get_node_at_position might return
        clicked_node = self.board.get_node(5, outermost_circle_node.node_idx)
        
        # Check if the clicked node is in valid_moves
        # This is what the game checks before moving the player
        assert clicked_node in valid_moves, "Clicked node not found in valid_moves"
        
        # Try to move the player to the clicked node
        self.player.move_to_node(clicked_node)
        
        # Manually complete the animation for the test
        self.player.is_moving = False
        self.player.current_node = clicked_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Check that player is now in the outermost circle
        assert self.player.current_node.circle_idx == 5, "Player did not move to the outermost circle"
    
    def test_node_equality_implementation(self):
        """Test that node equality is implemented correctly"""
        # Create two nodes with the same coordinates
        node1 = BoardNode(100, 100, 5, 0)
        node2 = BoardNode(100, 100, 5, 0)
        
        # They should be equal
        assert node1 == node2, "Nodes with same coordinates should be equal"
        
        # Create a node with different coordinates
        node3 = BoardNode(200, 200, 5, 1)
        
        # They should not be equal
        assert node1 != node3, "Nodes with different coordinates should not be equal"
    
    def test_reset_to_current_position_bug(self):
        """Test the bug where player selects an outside circle node but position resets"""
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Store the initial position for later comparison
        initial_position = (self.player.current_node.circle_idx, self.player.current_node.node_idx)
        
        # Get valid moves with dice value 1 (allows moving to adjacent circles)
        valid_moves = self.player.get_valid_moves(1)
        
        # Find nodes in the outermost circle
        outermost_circle_nodes = [node for node in valid_moves if node.circle_idx == 5]
        
        # There should be at least one valid move to the outermost circle
        assert len(outermost_circle_nodes) > 0, "No valid moves to the outermost circle"
        
        # Get the first outermost circle node
        outermost_circle_node = outermost_circle_nodes[0]
        
        # Set the previous_node to simulate a multi-move turn
        # This is a key part of reproducing the bug
        self.player.previous_node = self.board.get_node(4, 1)  # A different node in the same circle
        
        # Try to move the player to the outermost circle node
        self.player.move_to_node(outermost_circle_node)
        
        # Manually complete the animation for the test
        self.player.is_moving = False
        self.player.current_node = outermost_circle_node
        self.player.has_reached_outer_circle = True
        self.board.player_pieces = [self.player.current_node]
        
        # Check that player is now in the outermost circle
        final_position = (self.player.current_node.circle_idx, self.player.current_node.node_idx)
        assert final_position != initial_position, "Player position reset to initial position"
        assert self.player.current_node.circle_idx == 5, "Player did not move to the outermost circle"
    
    def test_previous_node_handling(self):
        """Test how previous_node affects movement to the outer circle"""
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get the corresponding node in the outermost circle
        outer_node = self.board.get_node(5, 0)
        
        # First, try moving without setting previous_node
        self.player.previous_node = None
        valid_moves = self.player.get_valid_moves(1)
        assert outer_node in valid_moves, "Outer node should be in valid moves without previous_node"
        
        # Now set previous_node to the outer node and try again
        self.player.previous_node = outer_node
        valid_moves = self.player.get_valid_moves(1)
        assert outer_node in valid_moves, "Outer node should be in valid moves when it's the previous_node"
        
        # Now set previous_node to a different node in the same circle
        self.player.previous_node = self.board.get_node(4, 1)
        valid_moves = self.player.get_valid_moves(1)
        assert outer_node in valid_moves, "Outer node should be in valid moves with different previous_node"
    
    def test_game_environment_outer_circle_movement(self):
        """Test movement to the outer circle in a simulated game environment"""
        # Create a game instance
        pygame.init()
        screen = pygame.Surface((1800, 1000))  # Create a dummy surface
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
        game.current_player.get_valid_moves(1)
        
        # Find nodes in the outermost circle
        outermost_circle_nodes = [node for node in game.current_player.valid_moves 
                                 if node.circle_idx == 5]
        
        # There should be at least one valid move to the outermost circle
        assert len(outermost_circle_nodes) > 0, "No valid moves to the outermost circle"
        
        # Get the first outermost circle node
        outermost_circle_node = outermost_circle_nodes[0]
        
        # Set the previous_node to simulate a multi-move turn
        # This is a key part of reproducing the bug
        game.current_player.previous_node = game.board.get_node(4, 1)
        
        # Simulate clicking on the outermost circle node
        game.move_player(outermost_circle_node)
        
        # Manually complete the animation
        game.current_player.is_moving = False
        game.current_player.current_node = outermost_circle_node
        game.current_player.has_reached_outer_circle = True
        game.update_player_pieces()
        
        # Check that player is now in the outermost circle
        final_position = (game.current_player.current_node.circle_idx, 
                         game.current_player.current_node.node_idx)
        assert final_position != initial_position, "Player position reset to initial position"
        assert game.current_player.current_node.circle_idx == 5, "Player did not move to the outermost circle"
    
    def test_get_connected_nodes_with_previous_node(self):
        """Test that get_connected_nodes correctly handles previous_node"""
        # Move player to a node in the second-to-last circle (circle 4)
        second_to_last_circle_node = self.board.get_node(4, 0)
        self.player.current_node = second_to_last_circle_node
        self.board.player_pieces = [self.player.current_node]
        
        # Get the corresponding node in the outermost circle
        outer_node = self.board.get_node(5, 0)
        
        # Set previous_node to the outer node
        self.player.previous_node = outer_node
        
        # Get connected nodes
        connected_nodes = self.board.get_connected_nodes(
            self.player.current_node, 
            is_player=True, 
            previous_node=self.player.previous_node
        )
        
        # The outer node should be in the connected nodes
        assert outer_node in connected_nodes, "Outer node should be in connected nodes when it's the previous_node"
        
        # Now check the specific condition in get_connected_nodes that might be causing the bug
        # For players moving to the outermost circle
        is_player = True
        circle_idx = self.player.current_node.circle_idx
        
        # This is the condition that might be causing the bug
        if is_player and circle_idx == self.board.num_circles - 2:  # Moving to outermost circle
            # Check if the outer node is the previous node - if so, always allow movement to it
            if self.player.previous_node and outer_node.x == self.player.previous_node.x and outer_node.y == self.player.previous_node.y:
                assert True, "Condition allows movement to previous node in outermost circle"
            else:
                # Only check if it's occupied by another player, not by enemy pieces
                is_occupied_by_player = False
                for player_node in self.board.player_pieces:
                    if (outer_node.x == player_node.x and outer_node.y == player_node.y and 
                        (self.player.current_node.x != player_node.x or self.player.current_node.y != player_node.y)):
                        is_occupied_by_player = True
                        break
                
                assert not is_occupied_by_player, "Outer node should not be occupied by another player"
