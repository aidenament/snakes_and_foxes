"""
Utility functions for pygame initialization without audio to avoid ALSA errors.
"""
import pygame


def init_pygame_no_audio():
    """
    Initialize pygame without audio modules to avoid ALSA configuration errors.
    
    This function initializes only the pygame modules that are required for
    this game (display and font), skipping audio/mixer initialization which
    can cause ALSA errors in headless environments.
    """
    # Initialize only the modules we need
    pygame.display.init()
    pygame.font.init()


def quit_pygame():
    """
    Properly quit pygame.
    """
    pygame.quit()