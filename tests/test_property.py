"""Property-based tests using Hypothesis.

We generate random *structurally valid* GL Strings by building them from a
grammar-shaped strategy, then assert invariants that must hold for every valid
string:

* parse -> serialize -> parse is a fixed point (structural round-trip).
* canonicalize is idempotent.
* canonicalize preserves the set of loci.
* the AST is immutable (hashable).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from glstring import GLString, canonicalize, parse, serialize

# Allele tokens: a small but realistic alphabet of HLA/KIR-like names. We keep
# each AlleleList to a single locus to satisfy the grammar invariant.
_LOCI = ["HLA-A", "HLA-B", "HLA-C", "HLA-DRB1", "KIR2DL5A", "KIR2DL5B"]
_FIELDS = ["01:01", "02:01", "03:01", "0010101", "00201", "11:01:01G"]


@st.composite
def alleles_for_locus(draw, locus: str):
    field = draw(st.sampled_from(_FIELDS))
    return f"{locus}*{field}"


@st.composite
def allele_list(draw):
    locus = draw(st.sampled_from(_LOCI))
    n = draw(st.integers(min_value=1, max_value=3))
    parts = [draw(alleles_for_locus(locus)) for _ in range(n)]
    return "/".join(parts)


@st.composite
def phased(draw):
    n = draw(st.integers(min_value=1, max_value=3))
    return "~".join(draw(allele_list()) for _ in range(n))


@st.composite
def genotype(draw):
    n = draw(st.integers(min_value=1, max_value=3))
    return "+".join(draw(phased()) for _ in range(n))


@st.composite
def genotype_list(draw):
    n = draw(st.integers(min_value=1, max_value=3))
    return "|".join(draw(genotype()) for _ in range(n))


@st.composite
def locus_blocks(draw):
    n = draw(st.integers(min_value=1, max_value=3))
    return "^".join(draw(genotype_list()) for _ in range(n))


@st.composite
def possible(draw):
    n = draw(st.integers(min_value=1, max_value=2))
    return "?".join(draw(locus_blocks()) for _ in range(n))


@given(possible())
def test_structural_round_trip_property(text):
    root = parse(text)
    assert parse(serialize(root)) == root


@given(possible())
def test_canonicalize_idempotent_property(text):
    once = canonicalize(parse(text))
    assert canonicalize(once) == once


@given(possible())
def test_canonicalize_preserves_loci_property(text):
    gl = GLString.parse(text)
    assert set(gl.loci) == set(gl.canonicalize().loci)


@given(possible())
def test_ast_hashable_property(text):
    root = parse(text)
    assert hash(root) == hash(parse(text))


@given(possible())
def test_smart_sort_idempotent_property(text):
    from glstring import smart_sort

    once = smart_sort(text)
    assert smart_sort(once) == once


@given(possible())
def test_smart_sort_round_trip_property(text):
    from glstring import canonicalize, serialize

    canon = canonicalize(parse(text))
    assert parse(serialize(canon)) == canon
