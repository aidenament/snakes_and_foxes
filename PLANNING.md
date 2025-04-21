# Snakes and Foxes - Game Planning

## Overview
This project implements the Snakes and Foxes game from the Wheel of Time series using Pygame. The game features a circular board with concentric rings, player pieces, and AI-controlled enemies (snakes and foxes) that move according to dice rolls.

## Game Mechanics

### Board Structure
- 6 concentric circles
- 10 nodes per circle
- Players start in the innermost circle
- Snakes and Foxes start on the outermost circle
- Movement paths are customizable for future versions

### Pieces
- 2 player pieces (black and white circles)
- 5 foxes (red triangles)
- 5 snakes (green curvy lines)

### Gameplay Flow
1. Roll 6 dice (each with 3 possible outcomes: black pip, red triangle, green line)
2. Move active player piece based on black pips rolled
3. Move foxes toward active player (number = red triangles rolled)
4. Move snakes toward active player (number = green lines rolled)
5. Switch active player piece
6. Repeat until win/loss condition is met

### Movement Rules
- Players can move between adjacent nodes on their current circle
- Players can move to adjacent circles (inward or outward)
- Movement is directional (can only move in one direction within a circle)
- Snakes and foxes move toward the active player

### Win/Loss Conditions
- Win: Get at least one player piece to the outermost circle and back to the center
- Loss: Both player pieces are captured by snakes or foxes

## Technical Design

### Core Components
1. **Board Manager**: Handles the board structure, node positions, and valid connections
2. **Piece Manager**: Tracks positions of all pieces and handles movement logic
3. **Dice System**: Handles dice rolling and outcome determination
4. **Game Logic**: Controls game flow, turns, and win/loss conditions
5. **Rendering Engine**: Visualizes the board, pieces, and dice
6. **Input Handler**: Processes user inputs for piece selection and movement

### Data Structures
- Board: Graph representation with nodes and edges
- Pieces: Objects with position, type, and movement capabilities
- Game State: Current active player, dice results, game phase

### Rendering Approach
- Board: Draw concentric circles with nodes at appropriate positions
- Pieces: Draw appropriate shapes at node positions
- Dice: Visualize dice and their outcomes
- UI: Display game state information and controls

## Implementation Plan

### Phase 1: Foundation
- Set up basic Pygame structure
- Implement board visualization
- Implement piece rendering

### Phase 2: Game Logic
- Implement dice mechanics
- Create movement logic for pieces
- Build game flow control

### Phase 3: AI and Interactions
- Implement snake and fox AI movement
- Add collision detection and capture mechanics

### Phase 4: Polish
- Refine visuals
- Add animations
- Implement sound effects
- Add menu and options

## Technical Considerations
- Make board structure easily modifiable for future variations
- Ensure separation of game logic from rendering
- Use object-oriented design for maintainability
- Include appropriate tests for core game mechanics

## Stretch Goals
- Advanced board layouts with custom movement paths
- Multiplayer support
- Different difficulty levels
- Save/load game functionality
- Animation effects for movement and captures