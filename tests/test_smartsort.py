"""Tests for AST-based smart sorting and its integration with canonicalize.

These recreate the published ``gl-smartsort`` behaviour independently (no source
was copied; see DESIGN.md on the licensing discrepancy) and add cases that
exercise the AST-based improvements: deterministic suffix tie-breaking,
variable-width numeric fields, GL String 1.1 ``?`` support, and phase
preservation.
"""

from __future__ import annotations

from glstring import GLString, canonicalize, parse, smart_sort
from glstring.ast import Allele
from glstring.smartsort import allele_sort_key

from . import corpus

# -- 1. Numerical rather than lexical allele ordering ------------------------


def test_numeric_not_lexical_ordering():
    # Lexical would put '103' before '11'; numeric is the reverse.
    assert smart_sort("HLA-A*01:103/HLA-A*01:11") == "HLA-A*01:11/HLA-A*01:103"


def test_variable_width_numeric_fields():
    assert smart_sort("HLA-A*01:11/HLA-A*01:103/HLA-A*01:02") == (
        "HLA-A*01:02/HLA-A*01:11/HLA-A*01:103"
    )


def test_numeric_first_field():
    assert smart_sort("HLA-A*11:01/HLA-A*2:01") == "HLA-A*2:01/HLA-A*11:01"


def test_allele_sort_key_numeric():
    assert allele_sort_key(Allele("HLA-A*01:11")) < allele_sort_key(Allele("HLA-A*01:103"))


# -- 2. Deterministic ordering of different loci -----------------------------


def test_locus_ordering_blocks():
    assert smart_sort("HLA-B*07:02^HLA-A*02:01") == "HLA-A*02:01^HLA-B*07:02"


def test_locus_ordering_is_input_order_independent():
    a = smart_sort("HLA-B*07:02^HLA-A*02:01^HLA-C*01:02")
    b = smart_sort("HLA-C*01:02^HLA-A*02:01^HLA-B*07:02")
    assert a == b == "HLA-A*02:01^HLA-B*07:02^HLA-C*01:02"


# -- 3. Preservation of allele ambiguity -------------------------------------


def test_allele_ambiguity_preserved():
    out = smart_sort("HLA-A*02:02/HLA-A*02:01")
    assert out == "HLA-A*02:01/HLA-A*02:02"
    assert "/" in out  # still an allele-ambiguity list


# -- 4. Preservation of genotype ambiguity -----------------------------------


def test_genotype_ambiguity_preserved():
    out = smart_sort("HLA-A*03:01+HLA-A*04:01|HLA-A*01:01+HLA-A*02:01")
    assert "|" in out
    gl = GLString.parse(out)
    assert gl.is_ambiguous()


# -- 5. Preservation of phase ------------------------------------------------


def test_phase_order_preserved_by_default():
    # '~' is ordered; default smart sort must not reorder the segments.
    text = "HLA-DRB3*01:01~HLA-DRB1*03:01"
    assert smart_sort(text) == text


def test_phase_relationship_not_lost():
    out = smart_sort(corpus.FULLY_PHASED)
    assert "~" in out
    assert GLString.parse(out).is_fully_phased()


# -- 6. Preservation of gene-copy multiplicity -------------------------------


def test_gene_copy_count_preserved():
    out = smart_sort("KIR2DL4*003+KIR2DL4*001+KIR2DL4*002")
    g = parse(out).alternatives[0].blocks[0].genotypes[0]
    assert len(g.copies) == 3  # multiplicity preserved


def test_gene_copy_order_preserved_by_default():
    text = "HLA-A*02:01+HLA-A*01:01"
    assert smart_sort(text) == text  # '+' not reordered by default


# -- 7. GL String 1.1 possible-locus syntax ----------------------------------


def test_possible_locus_sorted_and_preserved():
    out = smart_sort("KIR2DL5B*00201?KIR2DL5A*00501")
    assert "?" in out
    assert out == "KIR2DL5A*00501?KIR2DL5B*00201"


def test_possible_locus_dedup():
    out = smart_sort("KIR2DL5B*00201?KIR2DL5A*00501?KIR2DL5B*00201")
    assert out == "KIR2DL5A*00501?KIR2DL5B*00201"


# -- 8. Idempotence ----------------------------------------------------------


def test_idempotent():
    for text in corpus.ALL_VALID:
        once = smart_sort(text)
        assert smart_sort(once) == once


def test_canonicalize_idempotent_ast():
    for text in corpus.ALL_VALID:
        once = canonicalize(parse(text))
        assert canonicalize(once) == once


# -- 9. Input-order independence ---------------------------------------------


def test_order_independence_allele_list():
    assert smart_sort("HLA-A*02:01/HLA-A*01:01") == smart_sort("HLA-A*01:01/HLA-A*02:01")


def test_order_independence_genotype_list():
    a = smart_sort("HLA-A*03:01+HLA-A*04:01|HLA-A*01:01+HLA-A*02:01")
    b = smart_sort("HLA-A*01:01+HLA-A*02:01|HLA-A*03:01+HLA-A*04:01")
    assert a == b


def test_order_independence_nested_complex():
    # A deeply nested expression that a naive string comparator may not sort
    # uniquely: different input orders must canonicalize identically.
    s1 = "HLA-B*08:01^HLA-A*02:01/HLA-A*01:01|HLA-A*03:01+HLA-A*11:01"
    s2 = "HLA-A*03:01+HLA-A*11:01|HLA-A*01:01/HLA-A*02:01^HLA-B*08:01"
    assert smart_sort(s1) == smart_sort(s2)


# -- 10. Parse-serialize-parse round-trip after canonicalization -------------


def test_round_trip_after_canonicalize():
    for text in corpus.ALL_VALID:
        canon = canonicalize(parse(text))
        assert parse(canon.to_string()) == canon


# -- Suffix handling ---------------------------------------------------------


def test_suffix_deterministic_tie_break():
    # Identical numeric fields, differing suffix: order is deterministic and
    # independent of input order (unlike the legacy suffix-stripping comparator).
    assert smart_sort("HLA-A*01:01N/HLA-A*01:01") == "HLA-A*01:01/HLA-A*01:01N"
    assert smart_sort("HLA-A*01:01/HLA-A*01:01N") == "HLA-A*01:01/HLA-A*01:01N"


# -- Legacy parity with published gl-smartsort cases -------------------------


def test_legacy_parity_published_cases():
    # Recreated from the gl-smartsort test suite (behaviour, not source).
    assert smart_sort("A*01:103+A*01:11", legacy=True) == "A*01:11+A*01:103"
    assert smart_sort("B*07:02^A*02:01", legacy=True) == "A*02:01^B*07:02"
    assert (
        smart_sort("A*02:01+A*01:01^B*08:01+B*07:02", legacy=True)
        == "A*01:01+A*02:01^B*07:02+B*08:01"
    )


def test_legacy_differs_from_default_on_plus():
    # The documented divergence: default preserves '+' order; legacy sorts it.
    text = "HLA-A*02:01+HLA-A*01:01"
    assert smart_sort(text) == "HLA-A*02:01+HLA-A*01:01"
    assert smart_sort(text, legacy=True) == "HLA-A*01:01+HLA-A*02:01"
