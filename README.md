## Game of Life
_Original idea by John Horton Conway_

## What is this?
This is a simple implementation of the popular comp-sci programming challenge, Conway's Game of Life. It has a list of rules you can read about here: https://en.wikipedia.org/wiki/Conway%27s_Game_of_Life

<img width="933" height="684" alt="image" src="https://github.com/user-attachments/assets/54e4f305-9f1a-46f1-abb0-db08fcdc23ff" />

## Running it
```
python gameoflife.py
```

It opens on a main menu that explains the rules, with a colony quietly running
behind it. From there you can start from a random soup, or start from an empty
board and draw your own.

The window is resizable. Cells stay the same size as you drag, so the board
gains or loses rows and columns instead of stretching, and the colony you
already have keeps going.

## Drawing
Click and drag anywhere on the board to draw life, and right-click and drag to
erase it. This works whether the simulation is paused or running, so you can
drop a new cluster into a colony mid-flight and watch it take. Fast drags are
joined up into a continuous line, and the cell under the pointer is outlined so
you can see where you are about to draw.

## Controls
| Input | Action |
| --- | --- |
| Drag | Draw life |
| Right-drag | Erase |
| `SPACE` | Play / pause |
| `N` | Step one generation (while paused) |
| `R` | Reseed with a random soup |
| `C` | Clear the board |
| `G` | Toggle the grid lines |
| `UP` / `DOWN` | Faster / slower (1-60 generations per second) |
| `ESC` | Back to the main menu |
| `Q` | Quit |

The board wraps around at the edges, so a glider that leaves one side comes
back in on the other rather than dying against a wall. Pass `wrap=False` to
`GameOfLife` for the classic bounded board.

## REQUIREMENTS
- at least Python 3.13
- Pygame
