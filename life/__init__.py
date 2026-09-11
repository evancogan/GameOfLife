"""Conway's Game of Life - a pygame implementation.

The package splits into a pygame-free model (`game`), the things that draw it
(`render`), the things that read the mouse and keyboard (`input`), the screens
that tie those together (`scenes`), and the application shell (`app`).

`LifeApp` is exported lazily so that importing `life.game` on its own - as the
tests do - never drags pygame in behind it.
"""

__all__ = ["LifeApp"]


def __getattr__(name):
    """Import `LifeApp` on first use rather than at package import."""
    if name == "LifeApp":
        from .app import LifeApp
        return LifeApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
