"""Serialization and canonicalization for GL String ASTs.

Three distinct guarantees are provided, and they must not be conflated
(spec item 5):

1. **Lexical round-trip** -- reproduce the *original text* exactly. This is
   provided by :class:`~glstring.api.GLString`, which keeps the source string;
   it is not something the AST alone can promise, because the AST intentionally
   discards insignificant detail such as surrounding whitespace.

2. **Structural serialization** -- render an AST back to a GL String. Parsing
   that output yields an equal AST (``parse(serialize(ast)) == ast``). This is
   :func:`serialize`. The node hierarchy encodes precedence, so no parentheses
   are ever required.

3. **Canonicalization** -- produce a *normalised* GL String whose AST is
   guaranteed to describe the **same set of possible genetic states** as the
   input. This is :func:`canonicalize`. Only transformations that are provably
   safe are applied; see the docstring for the exact, documented subset and its
   limitations.

Canonicalization never changes biological meaning: in particular it never
reorders ``~``-phased segments (phase is ordered and meaningful) and never
reorders ``+`` gene copies in a way that would alter a cis/trans relationship.
"""

from __future__ import annotations

from .ast import (
    Allele,
    AlleleList,
    Genotype,
    GenotypeList,
    GLNode,
    LocusBlockList,
    PhasedGenotype,
    PossibleLoci,
)
from .parser import parse as _parse
from .smartsort import allele_sort_key, smart_sort_ast

__all__ = ["serialize", "canonicalize", "smart_sort"]


def serialize(node: GLNode) -> str:
    """Structurally serialize an AST node to a GL String fragment.

    ``parse(serialize(node))`` is structurally equal to ``node`` for any node
    produced by the parser.
    """
    return node.to_string()


# ---------------------------------------------------------------------------
# Canonicalization
# ---------------------------------------------------------------------------
#
# Canonicalization has two parts, both meaning-preserving:
#
#   1. De-duplication of unordered alternatives:
#        * a/a == a                 (AlleleList)
#        * g|g == g                 (GenotypeList)
#        * p?p == p                 (PossibleLoci)
#   2. Deterministic smart-sort ordering of all unordered levels
#      (/, |, ^, ?) via :mod:`glstring.smartsort`, with numeric allele ordering.
#
# Ordered levels are preserved by default:
#
#   * '~' phased segments are NOT reordered -- phase is ordered and meaningful.
#   * '+' gene copies are NOT reordered     -- proving copies are interchangeable
#                                              is not always possible (phased
#                                              copies, KIR copy-number variation).
#
# Deliberately NOT done (documented as the level-C semantic problem in DESIGN.md):
#
#   * Cross-representation normalisation, e.g. rewriting a '/'-factored genotype
#     ("a/b+c") into its '|' expansion ("a+c|b+c") or vice versa. Establishing
#     that two differently-structured strings describe the same genetic states
#     is semantic canonicalization and is out of scope here.
#
# This canonical form therefore guarantees: two GL Strings that are
# *syntactically equivalent* (same structure up to ordering and duplication of
# unordered alternatives) produce identical canonical strings. It does NOT
# guarantee that two semantically equivalent but structurally different strings
# do so.


def _dedup_allele_list(node: AlleleList) -> AlleleList:
    unique: dict[str, Allele] = {}
    for a in node.alleles:
        unique.setdefault(a.to_string(), a)
    return AlleleList(tuple(unique.values()))


def _dedup_phased(node: PhasedGenotype) -> PhasedGenotype:
    return PhasedGenotype(tuple(_dedup_allele_list(s) for s in node.segments))


def _dedup_genotype(node: Genotype) -> Genotype:
    return Genotype(tuple(_dedup_phased(c) for c in node.copies))


def _dedup_genotype_list(node: GenotypeList) -> GenotypeList:
    unique: dict[str, Genotype] = {}
    for g in node.genotypes:
        dg = _dedup_genotype(g)
        unique.setdefault(dg.to_string(), dg)
    return GenotypeList(tuple(unique.values()))


def _dedup_locus_blocks(node: LocusBlockList) -> LocusBlockList:
    return LocusBlockList(tuple(_dedup_genotype_list(b) for b in node.blocks))


def _dedup_possible(node: PossibleLoci) -> PossibleLoci:
    unique: dict[str, LocusBlockList] = {}
    for alt in node.alternatives:
        da = _dedup_locus_blocks(alt)
        unique.setdefault(da.to_string(), da)
    return PossibleLoci(tuple(unique.values()))


def canonicalize(node: PossibleLoci, *, legacy: bool = False) -> PossibleLoci:
    """Return a canonical, meaning-preserving copy of a GL String AST.

    Canonicalization de-duplicates unordered alternatives and then applies the
    deterministic AST smart-sort ordering (numeric allele ordering, loci ordered
    by name). The set of possible genetic states described by the result is
    identical to the input; only the representation is normalised.

    Phase (``~``) and gene-copy (``+``) orderings are preserved by default. Pass
    ``legacy=True`` to additionally sort those levels, reproducing the historical
    ``SmartSort.pm`` convention (see :mod:`glstring.smartsort`).
    """
    deduped = _dedup_possible(node)
    return smart_sort_ast(deduped, legacy=legacy)


def smart_sort(text: str, *, legacy: bool = False) -> str:
    """Parse ``text`` and return its deterministically smart-sorted GL String.

    Convenience wrapper that shares the AST-based implementation with
    :func:`canonicalize`. By default it also de-duplicates unordered
    alternatives (a superset of pure ordering); the result is the canonical
    string form.

    >>> smart_sort("HLA-A*02:01+HLA-A*01:01")
    'HLA-A*01:01+HLA-A*02:01'
    >>> smart_sort("HLA-A*01:103/HLA-A*01:11")
    'HLA-A*01:11/HLA-A*01:103'

    Note that ``+`` gene-copy order is preserved by default (it is meaningful),
    so ``HLA-A*02:01+HLA-A*01:01`` is reordered only because, in the absence of
    phase, the two copies form an unordered genotype -- to match the historical
    smart-sort convention here, pass ``legacy=True``. Allele (``/``), genotype
    (``|``), locus (``^``), and gene-location (``?``) levels are always ordered.
    """
    canon = canonicalize(_parse(text), legacy=legacy)
    return serialize(canon)


# ``allele_sort_key`` is re-exported for callers that want the numeric allele
# ordering key directly.
_ = allele_sort_key
