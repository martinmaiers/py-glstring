"""Canonicalization tests."""

from __future__ import annotations

from glstring import GLString, canonicalize, parse

from . import corpus


def test_allele_list_sorted_and_deduped():
    gl = GLString.parse("HLA-A*02:02/HLA-A*02:01/HLA-A*02:01")
    assert gl.canonicalize().to_string() == "HLA-A*02:01/HLA-A*02:02"


def test_genotype_list_sorted_and_deduped():
    gl = GLString.parse(
        "HLA-A*03:01+HLA-A*04:01|HLA-A*01:01+HLA-A*02:01|HLA-A*01:01+HLA-A*02:01"
    )
    canon = gl.canonicalize().to_string()
    # Deduplicated to two alternatives, sorted lexically.
    assert canon == "HLA-A*01:01+HLA-A*02:01|HLA-A*03:01+HLA-A*04:01"


def test_possible_alternatives_sorted_and_deduped():
    gl = GLString.parse("KIR2DL5B*00201?KIR2DL5A*00501?KIR2DL5B*00201")
    canon = gl.canonicalize().to_string()
    assert canon == "KIR2DL5A*00501?KIR2DL5B*00201"


def test_phase_order_not_reordered():
    # '~' is ordered: canonicalization must preserve segment order exactly.
    text = "HLA-DRB3*01:01~HLA-DRB1*03:01"
    gl = GLString.parse(text)
    assert gl.canonicalize().to_string() == text


def test_gene_copy_order_not_reordered():
    # '+' copies are not reordered in M1.
    text = "HLA-A*02:01+HLA-A*01:01"
    gl = GLString.parse(text)
    assert gl.canonicalize().to_string() == text


def test_canonicalize_is_idempotent():
    for text in corpus.ALL_VALID:
        once = canonicalize(parse(text))
        twice = canonicalize(once)
        assert once == twice


def test_canonicalize_preserves_loci_set():
    for text in corpus.ALL_VALID:
        gl = GLString.parse(text)
        assert set(gl.loci) == set(gl.canonicalize().loci)
