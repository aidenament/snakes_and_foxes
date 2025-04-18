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

class Dice:
    """
    Represents a set of six dice for the Snakes and Foxes game.
    
    Each die has three equally likely faces:
    - Black pip
    - Upside down red triangle
    - Vertical green squiggle line
    """
    
    def __init__(self):
        """
        Initialize the dice with default values.
        """
        self.num_dice = 6  # Number of dice
        self.dice_values = [FaceType.BLACK_PIP] * self.num_dice  # Current displayed values
        self.final_values = [FaceType.BLACK_PIP] * self.num_dice  # Final values after roll
        self.size = 60  # Size of each die square
        self.spacing = 10  # Spacing between dice
        self.color = (255, 255, 255)  # White background
        
        # Animation properties
        self.is_rolling = False
        self.roll_frames = 0
        self.roll_duration = 10  # Frames
    
    def roll(self) -> List[FaceType]:
        """
        Roll all six dice at once.
        
        Returns:
            List of dice values.
        """
        # Roll each die with equal probability for each face
        self.final_values = [random.choice(list(FaceType)) for _ in range(self.num_dice)]
        self.is_rolling = True
        self.roll_frames = 0
        return self.final_values  # Return the final values for counting
    
    def update(self) -> None:
        """Update the dice animation if they're rolling."""
        if self.is_rolling:
            self.roll_frames += 1
            if self.roll_frames < self.roll_duration:
                # Show random values during animation
                self.dice_values = [random.choice(list(FaceType)) for _ in range(self.num_dice)]
            else:
                # End of animation
                self.is_rolling = False
                # Restore the final values
                self.dice_values = self.final_values.copy()
    
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
