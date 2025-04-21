"""
Tests for game mode functionality in Snakes and Foxes game.
"""
import pytest
from dice import Dice, FaceType, GameMode

def test_dice_probabilities():
    """Test that dice probabilities match the expected values for each game mode."""
    # Number of rolls to perform for statistical testing
    num_rolls = 10000
    
    # Test EASY mode
    dice_easy = Dice(GameMode.EASY)
    easy_results = {
        FaceType.BLACK_PIP: 0,
        FaceType.RED_TRIANGLE: 0,
        FaceType.GREEN_SQUIGGLE: 0
    }
    
    # Roll many times to get statistical distribution
    for _ in range(num_rolls):
        results = dice_easy.roll()
        for face in results:
            easy_results[face] += 1
    
    # Calculate percentages
    total_faces = num_rolls * 6  # 6 dice per roll
    easy_percentages = {
        face: count / total_faces for face, count in easy_results.items()
    }
    
    # Check that percentages are close to expected values
    # EASY: Black pip (1/2), Red triangle (1/4), Green squiggle (1/4)
    assert 0.45 <= easy_percentages[FaceType.BLACK_PIP] <= 0.55
    assert 0.20 <= easy_percentages[FaceType.RED_TRIANGLE] <= 0.30
    assert 0.20 <= easy_percentages[FaceType.GREEN_SQUIGGLE] <= 0.30
    
    # Test MEDIUM mode
    dice_medium = Dice(GameMode.MEDIUM)
    medium_results = {
        FaceType.BLACK_PIP: 0,
        FaceType.RED_TRIANGLE: 0,
        FaceType.GREEN_SQUIGGLE: 0
    }
    
    # Roll many times to get statistical distribution
    for _ in range(num_rolls):
        results = dice_medium.roll()
        for face in results:
            medium_results[face] += 1
    
    # Calculate percentages
    medium_percentages = {
        face: count / total_faces for face, count in medium_results.items()
    }
    
    # Check that percentages are close to expected values
    # MEDIUM: Equal probability (1/3) for each face
    assert 0.30 <= medium_percentages[FaceType.BLACK_PIP] <= 0.36
    assert 0.30 <= medium_percentages[FaceType.RED_TRIANGLE] <= 0.36
    assert 0.30 <= medium_percentages[FaceType.GREEN_SQUIGGLE] <= 0.36
    
    # Test HARD mode
    dice_hard = Dice(GameMode.HARD)
    hard_results = {
        FaceType.BLACK_PIP: 0,
        FaceType.RED_TRIANGLE: 0,
        FaceType.GREEN_SQUIGGLE: 0
    }
    
    # Roll many times to get statistical distribution
    for _ in range(num_rolls):
        results = dice_hard.roll()
        for face in results:
            hard_results[face] += 1
    
    # Calculate percentages
    hard_percentages = {
        face: count / total_faces for face, count in hard_results.items()
    }
    
    # Check that percentages are close to expected values
    # HARD: Black pip (1/6), Red triangle (5/12), Green squiggle (5/12)
    assert 0.13 <= hard_percentages[FaceType.BLACK_PIP] <= 0.19
    assert 0.38 <= hard_percentages[FaceType.RED_TRIANGLE] <= 0.45
    assert 0.38 <= hard_percentages[FaceType.GREEN_SQUIGGLE] <= 0.45

def test_set_game_mode():
    """Test that changing the game mode works correctly."""
    dice = Dice(GameMode.EASY)
    assert dice.game_mode == GameMode.EASY
    
    dice.set_game_mode(GameMode.MEDIUM)
    assert dice.game_mode == GameMode.MEDIUM
    
    dice.set_game_mode(GameMode.HARD)
    assert dice.game_mode == GameMode.HARD
