"""Conway's Game of Life - pygame edition.

Run it with `python gameoflife.py`. The window is resizable: the grid grows
and shrinks with it, keeping the cell size constant so the colony is never
squashed. Live cells are drawn as green dots.

The code lives in the `life` package; this file just starts it.
"""

import sys

from life import LifeApp


def main():
    """Open the window and run until the player quits."""
    LifeApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
