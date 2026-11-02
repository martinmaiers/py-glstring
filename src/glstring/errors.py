"""Exception types for the glstring library."""

from __future__ import annotations

__all__ = ["GLStringError", "GLStringSyntaxError", "ExpansionLimitError"]


class GLStringError(ValueError):
    """Base class for all glstring errors."""


class GLStringSyntaxError(GLStringError):
    """Raised when a GL String cannot be parsed into a valid AST.

    The error carries the character ``position`` (0-based index into the
    original string) where the problem was detected, when known, so callers can
    point directly at the offending character.
    """

    def __init__(self, message: str, *, position: int | None = None, text: str | None = None):
        self.position = position
        self.text = text
        if position is not None:
            message = f"{message} (at position {position})"
            if text is not None:
                message = f"{message}\n{_caret(text, position)}"
        super().__init__(message)


class ExpansionLimitError(GLStringError):
    """Raised when lazy enumeration would exceed its configured result limit."""


def _caret(text: str, position: int) -> str:
    """Build a two-line caret pointer under ``text`` at ``position``."""
    pointer = " " * position + "^"
    return f"  {text}\n  {pointer}"
