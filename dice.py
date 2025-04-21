"""
Dice module for Snakes and Foxes game
"""
import pygame
import random
import math
from typing import List, Tuple
from enum import Enum

class FaceType(Enum):
    """Types of dice faces"""
    BLACK_PIP = 0
    RED_TRIANGLE = 1
    GREEN_SQUIGGLE = 2

class GameMode(Enum):
    """Game difficulty modes"""
    EASY = 0    # Black pip: 1/2, Red triangle: 1/4, Green squiggle: 1/4
    MEDIUM = 1  # Black pip: 1/3, Red triangle: 1/3, Green squiggle: 1/3
    HARD = 2    # Black pip: 1/6, Red triangle: 5/12, Green squiggle: 5/12

class Dice:
    """
    Represents a set of six dice for the Snakes and Foxes game.
    
    Each die has three faces with probabilities determined by the game mode:
    - Black pip
    - Upside down red triangle
    - Vertical green squiggle line
    """
    
    def __init__(self, game_mode: GameMode = GameMode.MEDIUM):
        """
        Initialize the dice with default values.
        
        Args:
            game_mode: The game difficulty mode that determines dice probabilities
        """
        self.num_dice = 6  # Number of dice
        self.dice_values = [FaceType.BLACK_PIP] * self.num_dice  # Current displayed values
        self.final_values = [FaceType.BLACK_PIP] * self.num_dice  # Final values after roll
        self.size = 60  # Size of each die square
        self.spacing = 10  # Spacing between dice
        self.color = (255, 255, 255)  # White background
        self.game_mode = game_mode  # Game difficulty mode
        
        # Animation properties
        self.is_rolling = False
        self.roll_frames = 0
        self.roll_duration = 10  # Frames
    
    def roll(self) -> List[FaceType]:
        """
        Roll all six dice at once with probabilities based on game mode.
        
        Returns:
            List of dice values.
        """
        self.final_values = []
        
        # Roll each die with probabilities based on game mode
        for _ in range(self.num_dice):
            face = self._roll_single_die()
            self.final_values.append(face)
            
        self.is_rolling = True
        self.roll_frames = 0
        return self.final_values  # Return the final values for counting
    
    def _roll_single_die(self) -> FaceType:
        """
        Roll a single die with probabilities based on game mode.
        
        Returns:
            The face value of the die.
        """
        # Generate a random number between 0 and 11 (for finest probability control)
        roll = random.randint(0, 11)
        
        if self.game_mode == GameMode.EASY:
            # EASY: Black pip (1/2), Red triangle (1/4), Green squiggle (1/4)
            if roll < 6:  # 0-5 (6/12 = 1/2)
                return FaceType.BLACK_PIP
            elif roll < 9:  # 6-8 (3/12 = 1/4)
                return FaceType.RED_TRIANGLE
            else:  # 9-11 (3/12 = 1/4)
                return FaceType.GREEN_SQUIGGLE
                
        elif self.game_mode == GameMode.MEDIUM:
            # MEDIUM: Equal probability (1/3) for each face
            if roll < 4:  # 0-3 (4/12 = 1/3)
                return FaceType.BLACK_PIP
            elif roll < 8:  # 4-7 (4/12 = 1/3)
                return FaceType.RED_TRIANGLE
            else:  # 8-11 (4/12 = 1/3)
                return FaceType.GREEN_SQUIGGLE
                
        else:  # GameMode.HARD
            # HARD: Black pip (1/6), Red triangle (5/12), Green squiggle (5/12)
            if roll < 2:  # 0-1 (2/12 = 1/6)
                return FaceType.BLACK_PIP
            elif roll < 7:  # 2-6 (5/12)
                return FaceType.RED_TRIANGLE
            else:  # 7-11 (5/12)
                return FaceType.GREEN_SQUIGGLE
    
    def update(self) -> None:
        """Update the dice animation if they're rolling."""
        if self.is_rolling:
            self.roll_frames += 1
            if self.roll_frames < self.roll_duration:
                # Show random values during animation (equal probability for visual effect)
                self.dice_values = [random.choice(list(FaceType)) for _ in range(self.num_dice)]
            else:
                # End of animation
                self.is_rolling = False
                # Restore the final values
                self.dice_values = self.final_values.copy()
    
    def set_game_mode(self, mode: GameMode) -> None:
        """
        Set the game mode which determines dice probabilities.
        
        Args:
            mode: The new game mode
        """
        self.game_mode = mode
    
    def _draw_black_pip(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Draw a black pip (circle) on the die."""
        center_x = x + self.size // 2
        center_y = y + self.size // 2
        radius = self.size // 6
        pygame.draw.circle(screen, (0, 0, 0), (center_x, center_y), radius)
    
    def _draw_red_triangle(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Draw an upside down red triangle on the die."""
        # Calculate triangle points (upside down)
        top_x = x + self.size // 2
        top_y = y + self.size * 2 // 3  # Lower position for upside down
        
        left_x = x + self.size // 3
        left_y = y + self.size // 3
        
        right_x = x + self.size * 2 // 3
        right_y = y + self.size // 3
        
        # Draw the triangle
        pygame.draw.polygon(screen, (255, 0, 0), [(top_x, top_y), (left_x, left_y), (right_x, right_y)])
    
    def _draw_green_squiggle(self, screen: pygame.Surface, x: int, y: int) -> None:
        """Draw a vertical green squiggle line on the die."""
        # Draw a wavy vertical line
        center_x = x + self.size // 2
        start_y = y + self.size // 5
        end_y = y + self.size * 4 // 5
        
        # Draw the squiggle as a series of connected points
        points = []
        num_segments = 10
        amplitude = self.size // 10
        
        for i in range(num_segments + 1):
            segment_y = start_y + (end_y - start_y) * i / num_segments
            # Sine wave pattern
            offset_x = amplitude * math.sin(i * math.pi / 2)
            points.append((center_x + offset_x, segment_y))
        
        # Draw the squiggle
        if len(points) >= 2:
            pygame.draw.lines(screen, (0, 200, 0), False, points, 3)
    
    def render(self, screen: pygame.Surface, x: int, y: int) -> None:
        """
        Render all six dice on the screen.
        
        Args:
            screen: The pygame surface to render on.
            x: The x-coordinate for the top-left of the first die.
            y: The y-coordinate for the top-left of the first die.
        """
        # Update animation if rolling
        self.update()
        
        # Calculate layout (2 rows of 3 dice)
        dice_per_row = 3
        
        # Draw each die
        for i, value in enumerate(self.dice_values):
            # Calculate position
            row = i // dice_per_row
            col = i % dice_per_row
            
            die_x = x + col * (self.size + self.spacing)
            die_y = y + row * (self.size + self.spacing)
            
            # Draw die background
            dice_rect = pygame.Rect(die_x, die_y, self.size, self.size)
            pygame.draw.rect(screen, self.color, dice_rect)
            pygame.draw.rect(screen, (0, 0, 0), dice_rect, 2)  # Border
            
            # Draw the appropriate face
            if value == FaceType.BLACK_PIP:
                self._draw_black_pip(screen, die_x, die_y)
            elif value == FaceType.RED_TRIANGLE:
                self._draw_red_triangle(screen, die_x, die_y)
            elif value == FaceType.GREEN_SQUIGGLE:
                self._draw_green_squiggle(screen, die_x, die_y)
