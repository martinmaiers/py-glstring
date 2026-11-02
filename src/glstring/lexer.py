"""Tokenizer for GL Strings, with character-position tracking.

The lexer splits an input string into a flat list of :class:`Token` objects.
Two token kinds exist:

* ``OPERATOR`` -- one of the six GL String delimiters ``? ^ | + ~ /``.
* ``ALLELE``   -- a maximal run of non-operator, non-whitespace characters
  (an allele token such as ``HLA-A*01:01``). The lexer does not interpret the
  internal structure of allele tokens; that is nomenclature-specific and out of
  scope for syntax parsing (spec item 10).

Every token records the 0-based character ``position`` at which it began in the
original string, so the parser can raise errors that point precisely at the
offending character.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .ast import (
    DELIM_ALLELE,
    DELIM_COPY,
    DELIM_GENOTYPE_LIST,
    DELIM_LOCUS,
    DELIM_PHASE,
    DELIM_POSSIBLE,
)
from .errors import GLStringSyntaxError

__all__ = ["Token", "TokenKind", "OPERATORS", "tokenize"]

# The set of single-character operators. Ordered mapping to the node precedence
# is handled by the parser; the lexer only needs membership.
OPERATORS: frozenset[str] = frozenset(
    {
        DELIM_POSSIBLE,
        DELIM_LOCUS,
        DELIM_GENOTYPE_LIST,
        DELIM_COPY,
        DELIM_PHASE,
        DELIM_ALLELE,
    }
)


class TokenKind(Enum):
    ALLELE = "ALLELE"
    OPERATOR = "OPERATOR"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str
    position: int

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.kind.name}, {self.value!r}, pos={self.position})"


def tokenize(text: str) -> list[Token]:
    """Split ``text`` into a list of :class:`Token`.

    Leading/trailing whitespace around tokens is ignored, but whitespace *inside*
    an allele token is disallowed: a GL String allele token has no spaces, so an
    interior space signals a malformed string and raises
    :class:`GLStringSyntaxError` pointing at the space.

    Raises :class:`GLStringSyntaxError` if ``text`` is ``None`` or empty.
    """
    if text is None:
        raise GLStringSyntaxError("GL String must not be None")
    if text == "":
        raise GLStringSyntaxError("GL String must not be empty", position=0, text=text)

    tokens: list[Token] = []
    buf: list[str] = []
    buf_start = -1
    space_after_token = False
    space_pos = -1

    def flush() -> None:
        nonlocal buf, buf_start, space_after_token, space_pos
        if buf:
            tokens.append(Token(TokenKind.ALLELE, "".join(buf), buf_start))
            buf = []
            buf_start = -1
        space_after_token = False
        space_pos = -1

    for i, ch in enumerate(text):
        if ch.isspace():
            # Whitespace is not significant; it ends the current token's
            # content. It only becomes an error if token content resumes before
            # the next operator (an interior space within one allele token).
            if buf:
                space_after_token = True
                if space_pos < 0:
                    space_pos = i
            continue
        if ch in OPERATORS:
            flush()
            tokens.append(Token(TokenKind.OPERATOR, ch, i))
        else:
            if buf and space_after_token:
                # Non-space content resumed after a space with no intervening
                # operator => interior whitespace within one allele token.
                raise GLStringSyntaxError(
                    "Whitespace is not permitted inside an allele token",
                    position=space_pos,
                    text=text,
                )
            if not buf:
                buf_start = i
            buf.append(ch)
    flush()

    if not tokens:
        raise GLStringSyntaxError(
            "GL String contains no tokens", position=0, text=text
        )
    return tokens
