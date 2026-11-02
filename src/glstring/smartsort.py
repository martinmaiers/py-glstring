"""AST-based smart sorting for GL Strings.

This module provides *deterministic ordering* of the components of a GL String,
operating on the parsed AST (:mod:`glstring.ast`) rather than on recursive
string splitting. It is the engine behind :func:`glstring.smart_sort` and the
sorting portion of :func:`glstring.serializer.canonicalize`.

Relationship to SmartSort.pm / gl-smartsort
-------------------------------------------
The sorting *behaviour* reproduces and extends ``SmartSort.pm`` (2012, Martin J.
Maiers) and its Python port ``gl-smartsort``:

* Order alternatives by locus (the portion before ``*``) first.
* Within a locus, order alleles by their **numeric** fields, so ``HLA-A*01:11``
  precedes ``HLA-A*01:103`` (numeric, not lexical).

No source code was copied from ``gl-smartsort``. That project declares MIT in
its ``pyproject.toml`` and README but ships a GPL-3.0 ``LICENSE`` file; this
unresolved discrepancy means its code cannot be safely incorporated into an
Apache-2.0 library. The behaviour is reimplemented independently from its
documented specification.

Deliberate differences from the legacy behaviour (see DESIGN.md):

* **Variable-width numeric fields** of unlimited depth are compared (legacy
  compared only 4 fields).
* **Deterministic suffix tie-breaking.** Legacy stripped expression suffixes
  (``N``, ``L``, ``S``, ``C``, ``A``, ``Q``) before comparison, so
  ``HLA-A*01:01`` and ``HLA-A*01:01N`` compared equal and their final order
  depended on input order. Here, when numeric fields are identical the full
  verbatim token breaks the tie, so ordering is fully deterministic and
  independent of input order.
* **Phase order is preserved.** Legacy reordered ``~`` phased segments, which
  can change biological meaning (phase is ordered). By default this module does
  *not* reorder ``~`` segments or ``+`` gene copies. A ``legacy`` mode is
  available for callers that require the exact historical convention.

Canonicalization level
-----------------------
Smart sorting is **syntactic normalization (level A)**: it changes only the
order of unordered components, never the grammatical structure, and together
with de-duplication provides a limited, safe form of **structural
canonicalization (level B)**. It does **not** provide **semantic
canonicalization (level C)** -- it does not prove two differently-structured GL
Strings describe the same genetic states. See DESIGN.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast import (
    Allele,
    AlleleList,
    Genotype,
    GenotypeList,
    LocusBlockList,
    PhasedGenotype,
    PossibleLoci,
)

__all__ = ["allele_sort_key", "smart_sort_ast"]


@dataclass(frozen=True, slots=True)
class _AlleleKey:
    """A total, deterministic ordering key for a single allele token.

    Ordering is: (locus, numeric fields, verbatim token). Comparing the
    verbatim token last makes the order deterministic even when the numeric
    fields are identical but expression suffixes differ (e.g. ``01:01`` vs
    ``01:01N``), which the legacy suffix-stripping comparator left ambiguous.
    """

    locus: str
    numeric: tuple[int, ...]
    token: str

    def as_tuple(self) -> tuple[str, tuple[int, ...], str]:
        return (self.locus, self.numeric, self.token)


def _numeric_fields(allele: Allele) -> tuple[int, ...]:
    """Return the allele's colon-separated fields as integers.

    Each field contributes its leading integer run; a trailing expression
    suffix (``N``, ``L``, ``S``, ``C``, ``A``, ``Q`` or any non-digit tail) is
    ignored *for the numeric component only*. A field with no leading digits
    contributes 0. Variable field counts are handled directly -- no fixed width.
    """
    out: list[int] = []
    for field in allele.fields:
        digits: list[str] = []
        for ch in field:
            if ch.isdigit():
                digits.append(ch)
            else:
                break
        out.append(int("".join(digits)) if digits else 0)
    return tuple(out)


def allele_sort_key(allele: Allele) -> tuple[str, tuple[int, ...], str]:
    """Return a deterministic total-order key for ``allele``.

    ``HLA-A*01:11`` sorts before ``HLA-A*01:103`` (numeric). When numeric fields
    tie, the full token decides (so ``HLA-A*01:01`` < ``HLA-A*01:01N``).
    """
    return _AlleleKey(allele.locus, _numeric_fields(allele), allele.name).as_tuple()


# ---------------------------------------------------------------------------
# Node sort keys. Each returns a tuple whose first element is an allele-style
# key (locus + numeric) so that sibling nodes order primarily by their first
# locus/allele, then by their full canonical string for a deterministic
# tie-break on nested structure.
# ---------------------------------------------------------------------------


def _allele_list_key(node: AlleleList) -> tuple:
    # Minimum allele within the list drives ordering; string breaks ties.
    min_allele = min(allele_sort_key(a) for a in node.alleles)
    return (min_allele, node.to_string())


def _phased_key(node: PhasedGenotype) -> tuple:
    return (_allele_list_key(node.segments[0]), node.to_string())


def _genotype_key(node: Genotype) -> tuple:
    return (_phased_key(node.copies[0]), node.to_string())


def _genotype_list_key(node: GenotypeList) -> tuple:
    return (_genotype_key(node.genotypes[0]), node.to_string())


def _locus_blocks_key(node: LocusBlockList) -> tuple:
    return (_genotype_list_key(node.blocks[0]), node.to_string())


# ---------------------------------------------------------------------------
# AST transformation. Sorts unordered levels; by default preserves ordered
# levels (~ segments, + copies). In legacy mode, those are sorted too.
# ---------------------------------------------------------------------------


def _sort_allele_list(node: AlleleList) -> AlleleList:
    ordered = tuple(sorted(node.alleles, key=allele_sort_key))
    return AlleleList(ordered)


def _sort_phased(node: PhasedGenotype, *, legacy: bool) -> PhasedGenotype:
    segments = tuple(_sort_allele_list(s) for s in node.segments)
    if legacy:
        segments = tuple(sorted(segments, key=_allele_list_key))
    return PhasedGenotype(segments)


def _sort_genotype(node: Genotype, *, legacy: bool) -> Genotype:
    copies = tuple(_sort_phased(c, legacy=legacy) for c in node.copies)
    if legacy:
        copies = tuple(sorted(copies, key=_phased_key))
    return Genotype(copies)


def _sort_genotype_list(node: GenotypeList, *, legacy: bool) -> GenotypeList:
    genotypes = tuple(_sort_genotype(g, legacy=legacy) for g in node.genotypes)
    genotypes = tuple(sorted(genotypes, key=_genotype_key))
    return GenotypeList(genotypes)


def _sort_locus_blocks(node: LocusBlockList, *, legacy: bool) -> LocusBlockList:
    blocks = tuple(_sort_genotype_list(b, legacy=legacy) for b in node.blocks)
    # '^' locus blocks are an unordered set: sort them for a canonical,
    # input-order-independent ordering (by locus/allele then string).
    blocks = tuple(sorted(blocks, key=_genotype_list_key))
    return LocusBlockList(blocks)


def smart_sort_ast(node: PossibleLoci, *, legacy: bool = False) -> PossibleLoci:
    """Return a deterministically sorted copy of a GL String AST.

    Unordered levels -- allele ambiguity (``/``), genotype ambiguity (``|``),
    unphased locus blocks (``^``), and gene-location alternatives (``?``) -- are
    sorted. Ordered levels -- phase (``~``) and gene copies (``+``) -- are
    preserved unless ``legacy`` is ``True``, which reproduces the historical
    ``SmartSort.pm`` behaviour of sorting those too.

    This only reorders components; it never adds, removes, or restructures them,
    so all information about allele ambiguity, genotype ambiguity, phase, and
    copy number is preserved.
    """
    alternatives = tuple(_sort_locus_blocks(a, legacy=legacy) for a in node.alternatives)
    alternatives = tuple(sorted(alternatives, key=_locus_blocks_key))
    return PossibleLoci(alternatives)
