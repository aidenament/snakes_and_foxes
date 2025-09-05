"""
Test for ALSA configuration fix.

This test verifies that pygame can be initialized without ALSA errors
in environments where audio devices are not available.
"""
import unittest
import sys
import os

# Add the project root to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from pygame_utils import init_pygame_no_audio, quit_pygame


class TestALSAFix(unittest.TestCase):
    """Test that pygame initializes without ALSA errors."""
    
    def test_pygame_no_audio_init(self):
        """Test that pygame can be initialized without audio."""
        # This should not raise any exceptions or produce ALSA errors
        init_pygame_no_audio()
        
        # Verify that display is initialized
        self.assertTrue(pygame.display.get_init())
        
        # Verify that font is initialized  
        self.assertTrue(pygame.font.get_init())
        
        # Cleanup
        quit_pygame()
    
    def test_display_functionality(self):
        """Test that display functionality works after audio-free init."""
        init_pygame_no_audio()
        
        # Should be able to create a surface without errors
        screen = pygame.display.set_mode((800, 600))
        self.assertIsNotNone(screen)
        self.assertEqual(screen.get_size(), (800, 600))
        
        # Cleanup
        quit_pygame()


if __name__ == '__main__':
    unittest.main()