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

## Running it in a browser
`web/index.html` is the same colony without pygame, for phones and anything
else that has a browser but no Python. Open the file directly - there is no
build step, no server and nothing to install.

It is a port of the model, not a rewrite of it: the rules, the glow and fade
tables and the generation clock in `life/game.py` carry across line for line,
and only the pygame layer is replaced. The six keys become on-screen buttons,
and because a phone has no right mouse button, erasing is a `DRAW`/`ERASE`
toggle instead. Right-drag still erases on a desktop.

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
| `UP` / `DOWN` | Faster / slower, 1-60 generations per second. Tap to nudge by one, or hold to roll the number - the longer you hold, the faster it climbs. `+` / `-` work too. |
| `ESC` | Back to the main menu |
| `Q` | Quit |

The board wraps around at the edges, so a glider that leaves one side comes
back in on the other rather than dying against a wall. Pass `wrap=False` to
`GameOfLife` (in `life/game.py`) for the classic bounded board.

## Code layout
`gameoflife.py` is only a launcher; the code lives in the `life` package.

| File | What is in it |
| --- | --- |
| `life/config.py` | Frozen dataclasses of tunable values: board scale, speeds, effect lengths, menu type sizes and the colour theme |
| `life/game.py` | The model, with no pygame at all: `GameOfLife` (the rules), `CellEffects` (glow and fade), `GenerationClock` (pacing) and `Simulation` tying the three together |
| `life/render.py` | `FontBook`, `BoardRenderer`, `Hud` and `MenuPanel` - everything that puts pixels on the screen |
| `life/input.py` | `Viewport` (pixels to cells), `Painter` (mouse drawing) and `SpeedController` (the hold-to-roll speed keys) |
| `life/scenes.py` | `Scene` and its two subclasses, `MenuScene` and `SimulationScene`, each owning its own keys, updates and drawing |
| `life/app.py` | `LifeApp`: the window, the event pump and the current scene |

Because the model has no pygame dependency, the rules are tested without opening
a window:

```
python -m unittest discover -s tests
```

## REQUIREMENTS
- at least Python 3.13
- Pygame
