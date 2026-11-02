"""Immutable, typed Abstract Syntax Tree (AST) for GL Strings.

This module defines the node hierarchy that the parser produces and the
serializer consumes. Every node is a frozen dataclass, so an AST is immutable
and hashable; structural operations return *new* trees rather than mutating in
place.

Design principles
-----------------
* **One node type per grammar operator.** The node hierarchy mirrors GL String
  1.1 operator precedence exactly, so the tree structure -- not operator
  appearance order -- determines meaning (Mack et al. 2023, Table 2).
* **No fixed diploid assumption.** A :class:`Genotype` may hold any number of
  gene copies, and a :class:`PossibleLoci` any number of alternatives. KIR and
  other systems with variable gene content and copy number are first-class.
* **Lossless.** Allele tokens are preserved verbatim. Nothing is normalised at
  parse time; normalisation is an explicit, opt-in operation (canonicalize).
* **Nomenclature-independent.** An :class:`Allele` is any non-empty token; the
  AST never consults an allele database.

Operator precedence (Mack et al. 2023, Table 2), from the delimiter evaluated
*first* (outermost / loosest binding) to the delimiter evaluated *last*
(innermost / tightest binding)::

    precedence 0   ?   PossibleLoci     possible gene locations   (GL 1.1)
    precedence 1   ^   LocusBlockList   unphased genes (loci)
    precedence 2   |   GenotypeList     possible genotypes
    precedence 3   +   Genotype         copies of genes
    precedence 4   ~   PhasedGenotype   genes known to be in phase
    precedence 5   /   AlleleList       possible alleles

The root node is always :class:`PossibleLoci`. For a GL String with no ``?``
delimiter (i.e. a GL String 1.0 string) the root is a :class:`PossibleLoci`
with a single alternative; this keeps a single uniform tree shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

# Delimiter characters, keyed by the node that is built around them. These are
# the authoritative GL String 1.1 operators (Mack et al. 2023, Table 2).
DELIM_POSSIBLE = "?"
DELIM_LOCUS = "^"
DELIM_GENOTYPE_LIST = "|"
DELIM_COPY = "+"
DELIM_PHASE = "~"
DELIM_ALLELE = "/"

__all__ = [
    "GLNode",
    "Allele",
    "AlleleList",
    "PhasedGenotype",
    "Genotype",
    "GenotypeList",
    "LocusBlock",
    "LocusBlockList",
    "PossibleLoci",
]


class GLNode:
    """Base class for all GL String AST nodes.

    Subclasses are frozen dataclasses. This base exists to provide shared
    behaviour (``loci``, ``to_string``) and a common type for annotations.
    Serialization lives here so every node can render itself independently.
    """

    def to_string(self) -> str:
        """Render this node (and its subtree) as a GL String fragment."""
        raise NotImplementedError

    @property
    def loci(self) -> tuple[str, ...]:
        """Distinct loci referenced in this subtree, in first-seen order."""
        raise NotImplementedError

    def __str__(self) -> str:  # pragma: no cover - thin wrapper
        return self.to_string()


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    """Return ``values`` with duplicates removed, preserving first-seen order."""
    seen: dict[str, None] = {}
    for v in values:
        seen.setdefault(v, None)
    return tuple(seen)


@dataclass(frozen=True, slots=True)
class Allele(GLNode):
    """A single allele call, e.g. ``HLA-A*01:01`` or ``KIR2DL5A*0010101``.

    The token is stored verbatim. ``locus`` is derived as the portion before
    the ``*`` (the whole token if there is no ``*``). The AST never validates
    the token against a nomenclature database -- syntax validity and allele
    existence are deliberately separate concerns (spec item 10).
    """

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Allele token must be non-empty")

    @cached_property
    def locus(self) -> str:
        """Locus portion of the token, e.g. ``HLA-A`` from ``HLA-A*01:01``."""
        return self.name.split("*", 1)[0]

    @cached_property
    def fields(self) -> tuple[str, ...]:
        """Colon-separated fields after ``*``; empty tuple if none."""
        if "*" not in self.name:
            return ()
        return tuple(self.name.split("*", 1)[1].split(":"))

    def to_string(self) -> str:
        return self.name

    @property
    def loci(self) -> tuple[str, ...]:
        return (self.locus,)


@dataclass(frozen=True, slots=True)
class AlleleList(GLNode):
    """Allele ambiguity (``/``): an unordered set of candidate alleles.

    A single unambiguous allele is represented as a one-element AlleleList so
    every position in the tree has a uniform type. All alleles in the list must
    share one locus (the ``/`` delimiter joins alleles of a single locus); this
    invariant is enforced here and surfaced by the parser as a syntax error.
    """

    alleles: tuple[Allele, ...]

    def __post_init__(self) -> None:
        if not self.alleles:
            raise ValueError("AlleleList must contain at least one allele")
        distinct = {a.locus for a in self.alleles}
        if len(distinct) != 1:
            raise ValueError(
                "Allele ambiguity ('/') must join alleles of a single locus; "
                f"got {sorted(distinct)}"
            )

    @property
    def locus(self) -> str:
        return self.alleles[0].locus

    @property
    def is_ambiguous(self) -> bool:
        return len(self.alleles) > 1

    def to_string(self) -> str:
        return DELIM_ALLELE.join(a.to_string() for a in self.alleles)

    @property
    def loci(self) -> tuple[str, ...]:
        return (self.locus,)


@dataclass(frozen=True, slots=True)
class PhasedGenotype(GLNode):
    """Known phase (``~``): an ordered run of AlleleLists on one chromosome.

    Element *i* is the AlleleList at ``loci[i]``. A single-locus (unphased)
    position is a one-element PhasedGenotype so the tree shape is uniform. The
    order of the segments is significant -- it encodes cis relationships and is
    preserved exactly.
    """

    segments: tuple[AlleleList, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("PhasedGenotype must contain at least one segment")

    @property
    def is_phased(self) -> bool:
        """Whether this asserts phase across more than one segment."""
        return len(self.segments) > 1

    def to_string(self) -> str:
        return DELIM_PHASE.join(s.to_string() for s in self.segments)

    @property
    def loci(self) -> tuple[str, ...]:
        out: list[str] = []
        for seg in self.segments:
            out.extend(seg.loci)
        return _ordered_unique(tuple(out))


@dataclass(frozen=True, slots=True)
class Genotype(GLNode):
    """Gene copies (``+``): the copies that together make up a genotype.

    Each copy is a :class:`PhasedGenotype`. A diploid genotype has two copies,
    but any number is permitted (zero copies is invalid; one or more is allowed)
    so that KIR variable copy number is representable. No invariant requires the
    copies to span the same loci -- gene content may legitimately differ between
    copies in systems with presence/absence variation.
    """

    copies: tuple[PhasedGenotype, ...]

    def __post_init__(self) -> None:
        if not self.copies:
            raise ValueError("Genotype must contain at least one gene copy")

    @property
    def is_multi_copy(self) -> bool:
        return len(self.copies) > 1

    def to_string(self) -> str:
        return DELIM_COPY.join(c.to_string() for c in self.copies)

    @property
    def loci(self) -> tuple[str, ...]:
        out: list[str] = []
        for c in self.copies:
            out.extend(c.loci)
        return _ordered_unique(tuple(out))


@dataclass(frozen=True, slots=True)
class GenotypeList(GLNode):
    """Genotype ambiguity (``|``): alternative genotypes, exactly one of which
    is the true genotype.

    A single unambiguous genotype is a one-element GenotypeList. Alternatives
    are unordered (order carries no meaning per Mack et al. 2023).
    """

    genotypes: tuple[Genotype, ...]

    def __post_init__(self) -> None:
        if not self.genotypes:
            raise ValueError("GenotypeList must contain at least one genotype")

    @property
    def is_ambiguous(self) -> bool:
        return len(self.genotypes) > 1

    def to_string(self) -> str:
        return DELIM_GENOTYPE_LIST.join(g.to_string() for g in self.genotypes)

    @property
    def loci(self) -> tuple[str, ...]:
        out: list[str] = []
        for g in self.genotypes:
            out.extend(g.loci)
        return _ordered_unique(tuple(out))


# A locus block (``^``-delimited segment) is just a GenotypeList covering one
# locus-set whose phase to the other blocks is unasserted. We model it as an
# alias type so the names in the grammar and the code line up, while reusing
# GenotypeList's behaviour.
LocusBlock = GenotypeList


@dataclass(frozen=True, slots=True)
class LocusBlockList(GLNode):
    """Unphased loci (``^``): locus blocks whose inter-block phase is unknown.

    Each block is a :class:`GenotypeList` (aliased :data:`LocusBlock`). Loci in
    the same block may be phased (via ``~`` inside); loci in different blocks
    assert no phase relationship to one another. This is the "arbitrary locus
    subsets with known phase" representation required for partial phasing.
    """

    blocks: tuple[GenotypeList, ...]

    def __post_init__(self) -> None:
        if not self.blocks:
            raise ValueError("LocusBlockList must contain at least one block")

    def to_string(self) -> str:
        return DELIM_LOCUS.join(b.to_string() for b in self.blocks)

    @property
    def loci(self) -> tuple[str, ...]:
        out: list[str] = []
        for b in self.blocks:
            out.extend(b.loci)
        return _ordered_unique(tuple(out))


@dataclass(frozen=True, slots=True)
class PossibleLoci(GLNode):
    """Possible gene locations (``?``): the GL String 1.1 root node.

    Each alternative is a :class:`LocusBlockList`. A ``?`` expresses that the
    typing could not assign a sequence to one gene paralog versus another
    (e.g. KIR2DL5A vs KIR2DL5B); exactly one alternative is the truth, but which
    cannot be determined. A GL String with no ``?`` (a GL String 1.0 string)
    has a single alternative, so the tree shape is identical across versions.
    """

    alternatives: tuple[LocusBlockList, ...]

    def __post_init__(self) -> None:
        if not self.alternatives:
            raise ValueError("PossibleLoci must contain at least one alternative")

    @property
    def is_location_ambiguous(self) -> bool:
        """Whether a ``?`` gene-location ambiguity is present."""
        return len(self.alternatives) > 1

    def to_string(self) -> str:
        return DELIM_POSSIBLE.join(a.to_string() for a in self.alternatives)

    @property
    def loci(self) -> tuple[str, ...]:
        out: list[str] = []
        for a in self.alternatives:
            out.extend(a.loci)
        return _ordered_unique(tuple(out))
