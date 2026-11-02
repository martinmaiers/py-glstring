"""Public API facade tests."""

from __future__ import annotations

from glstring import GLString

from . import corpus


def test_is_ambiguous_allele():
    assert GLString.parse(corpus.ALLELE_AMBIGUITY).is_ambiguous()


def test_is_ambiguous_genotype():
    assert GLString.parse(corpus.GENOTYPE_AMBIGUITY).is_ambiguous()


def test_is_ambiguous_location():
    assert GLString.parse(corpus.KIR_POSSIBLE_SHORT).is_ambiguous()


def test_not_ambiguous_simple_and_phased():
    assert not GLString.parse(corpus.SIMPLE_GENOTYPE).is_ambiguous()
    assert not GLString.parse(corpus.PHASED).is_ambiguous()
    assert not GLString.parse(corpus.GENE_COPIES).is_ambiguous()


def test_is_fully_phased_true():
    assert GLString.parse(corpus.FULLY_PHASED).is_fully_phased()
    assert GLString.parse(corpus.PHASED).is_fully_phased()


def test_is_fully_phased_false_when_unphased_loci():
    # Separate '^' blocks => inter-block phase unknown.
    assert not GLString.parse(corpus.TWO_LOCUS_UNPHASED).is_fully_phased()


def test_is_fully_phased_false_when_ambiguous():
    assert not GLString.parse(corpus.ALLELE_AMBIGUITY).is_fully_phased()
    assert not GLString.parse(corpus.GENOTYPE_AMBIGUITY).is_fully_phased()


def test_is_location_ambiguous():
    assert GLString.parse(corpus.KIR_POSSIBLE).is_location_ambiguous()
    assert not GLString.parse(corpus.SIMPLE_GENOTYPE).is_location_ambiguous()


def test_get_locus_returns_blocks():
    gl = GLString.parse(corpus.TWO_LOCUS_UNPHASED)
    a_blocks = gl.get_locus("HLA-A")
    assert len(a_blocks) == 1
    assert "HLA-A" in a_blocks[0].loci
    assert gl.get_locus("HLA-DRB1") == ()


def test_get_locus_across_possible_alternatives():
    gl = GLString.parse(corpus.KIR_POSSIBLE)
    blocks = gl.get_locus("KIR2DL5A")
    assert len(blocks) >= 1


def test_str_is_structural_serialization():
    gl = GLString.parse(corpus.SIMPLE_GENOTYPE)
    assert str(gl) == gl.to_string()


def test_loci_published_example():
    gl = GLString.parse(corpus.CANONICAL_MACK)
    assert gl.loci == ("HLA-A", "HLA-B", "HLA-DRB1", "HLA-DRB3")
