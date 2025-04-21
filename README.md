# Snakes and Foxes Game

A Python implementation of the Snakes and Foxes board game from Wheel of Time using PyGame.

## Game Rules

1. The game is played on a board with 6 concentric circles.
2. The innermost circle is a single large node (the center), while other circles contain 10 nodes each.
3. Players start at the center node and need to:
   - First reach any node in the outermost circle
   - Then return to the center node to win
4. Movement is determined by rolling a six-sided die.
5. Movement rules:
   - From the center node, a roll of 1 allows moving to any node in the first circle
   - In other circles, players can move around their current circle by the number of spaces shown on the dice
   - Movement direction alternates between circles (clockwise/counter-clockwise)
   - Players can move to adjacent circles only with a dice roll of 1
6. The board contains snakes and foxes:
   - Landing on a snake sends the player back to the previous circle
   - Landing on a fox allows the player to move forward to the next circle
7. The player wins by reaching the center after visiting any node in the outermost circle.
8. The player loses if they exceed 100 turns without winning.

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/snakes_and_foxes.git
cd snakes_and_foxes
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

## How to Play

1. Run the game:
```
python main.py
```

2. Command-line options:
```
python main.py --circles 6 --nodes 10
```
Where:
- `--circles`: Number of concentric circles (default: 6)
- `--nodes`: Number of nodes per circle (default: 10)

3. Game Controls:
   - Press SPACE to roll the dice
   - Click on a highlighted node to move (valid moves are highlighted in yellow)
   - Press R to restart the game after winning or losing

## Features

- Concentric circle board with customizable number of circles and nodes
- Dice rolling mechanism
- Special spaces (snakes and foxes) that affect player movement
- Directional movement that alternates between circles
- Win condition requiring visiting the outer circle before returning to center
- Lose condition after exceeding maximum turns
- Visual highlighting of valid moves
- Simple and intuitive UI

## Project Structure

- `main.py`: Entry point for the game
- `game.py`: Game engine and logic
- `board.py`: Board representation and rendering
- `player.py`: Player class for movement and position tracking
- `dice.py`: Dice rolling functionality
- `tests/`: Unit tests for game components
