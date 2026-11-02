"""Public API facade for the glstring library.

:class:`GLString` is the single entry point most callers need. It wraps the
immutable AST (:mod:`glstring.ast`) and the original source text, exposing a
small, coherent interface while keeping AST internals available via
:attr:`GLString.root` for advanced use.

Example
-------
>>> from glstring import GLString
>>> gl = GLString.parse("HLA-A*01:01+HLA-A*02:01^HLA-B*07:02+HLA-B*08:01")
>>> gl.loci
('HLA-A', 'HLA-B')
>>> gl.is_valid
True
>>> gl.is_ambiguous()
False
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast import (
    GenotypeList,
    LocusBlockList,
    PossibleLoci,
)
from .errors import GLStringSyntaxError
from .parser import parse as _parse
from .serializer import canonicalize as _canonicalize
from .serializer import serialize as _serialize

__all__ = ["GLString"]


@dataclass(frozen=True, slots=True)
class GLString:
    """An immutable, parsed GL String.

    Construct via :meth:`parse`. The object keeps both the parsed ``root`` AST
    and the original ``source`` text, which lets it provide an exact lexical
    round-trip (:meth:`original`) distinct from structural serialization
    (:meth:`to_string`).
    """

    root: PossibleLoci
    source: str

    # -- construction --------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> GLString:
        """Parse ``text`` into a :class:`GLString`.

        Raises :class:`~glstring.errors.GLStringSyntaxError` on malformed input.
        """
        root = _parse(text)
        return cls(root=root, source=text)

    @classmethod
    def is_valid(cls, text: str) -> bool:
        """Return ``True`` iff ``text`` is a syntactically valid GL String.

        This checks *syntax only*; it never consults a nomenclature database
        (allele existence is a separate concern, spec item 10).
        """
        try:
            _parse(text)
        except GLStringSyntaxError:
            return False
        return True

    # -- serialization -------------------------------------------------------

    def original(self) -> str:
        """Return the exact original source text (lexical round-trip)."""
        return self.source

    def to_string(self) -> str:
        """Structurally serialize the AST back to a GL String.

        ``GLString.parse(gl.to_string()).root == gl.root`` holds for any ``gl``.
        This may differ from :meth:`original` only in insignificant detail such
        as surrounding whitespace.
        """
        return _serialize(self.root)

    def canonicalize(self, *, legacy: bool = False) -> GLString:
        """Return a new :class:`GLString` in canonical form.

        Canonicalization is meaning-preserving within the documented safe subset
        (see :mod:`glstring.serializer` and :mod:`glstring.smartsort`). The
        returned string's AST describes the same set of possible genetic states.
        It de-duplicates unordered alternatives and applies deterministic
        smart-sort ordering with numeric allele comparison.

        Pass ``legacy=True`` to additionally sort ``~`` and ``+`` levels,
        reproducing the historical ``SmartSort.pm`` convention.
        """
        canon = _canonicalize(self.root, legacy=legacy)
        return GLString(root=canon, source=_serialize(canon))

    def smart_sort(self, *, legacy: bool = False) -> GLString:
        """Alias for :meth:`canonicalize`; returns a smart-sorted GLString.

        Provided for callers who think in terms of "smart sort" rather than
        "canonicalize"; both share one AST-based implementation.
        """
        return self.canonicalize(legacy=legacy)

    # -- structural queries --------------------------------------------------

    @property
    def loci(self) -> tuple[str, ...]:
        """Distinct loci referenced, in first-seen order."""
        return self.root.loci

    def get_locus(self, locus: str) -> tuple[GenotypeList, ...]:
        """Return the locus block(s) that reference ``locus``.

        A block is a :class:`~glstring.ast.GenotypeList`. More than one may be
        returned when gene-location ambiguity (``?``) places a locus in multiple
        alternatives. Returns an empty tuple if the locus is absent.
        """
        found: list[GenotypeList] = []
        for alt in self.root.alternatives:
            for block in alt.blocks:
                if locus in block.loci and block not in found:
                    found.append(block)
        return tuple(found)

    def is_ambiguous(self) -> bool:
        """Whether the GL String expresses *any* ambiguity.

        True if it contains allele ambiguity (``/``), genotype ambiguity
        (``|``), or gene-location ambiguity (``?``). Known phase (``~``) and
        gene copies (``+``) are not ambiguity.
        """
        if self.root.is_location_ambiguous:
            return True
        for alt in self.root.alternatives:
            for block in alt.blocks:
                if block.is_ambiguous:  # genotype ambiguity '|'
                    return True
                for genotype in block.genotypes:
                    for copy in genotype.copies:
                        for seg in copy.segments:
                            if seg.is_ambiguous:  # allele ambiguity '/'
                                return True
        return False

    def is_fully_phased(self) -> bool:
        """Whether phase is known across all loci with no ambiguity.

        True iff the string has exactly one gene-location alternative, exactly
        one locus block, that block holds exactly one (unambiguous) genotype,
        and every allele position is unambiguous. In other words, the GL String
        denotes a single, fully phased multilocus genotype.
        """
        if self.root.is_location_ambiguous:
            return False
        if len(self.root.alternatives) != 1:
            return False
        alt: LocusBlockList = self.root.alternatives[0]
        if len(alt.blocks) != 1:
            return False
        block: GenotypeList = alt.blocks[0]
        if block.is_ambiguous:
            return False
        genotype = block.genotypes[0]
        for copy in genotype.copies:
            for seg in copy.segments:
                if seg.is_ambiguous:
                    return False
        return True

    def is_location_ambiguous(self) -> bool:
        """Whether gene-location ambiguity (``?``, GL String 1.1) is present."""
        return self.root.is_location_ambiguous

    # -- dunder --------------------------------------------------------------

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GLString.parse({self.source!r})"
