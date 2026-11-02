"""Parsing correctness and operator-precedence tests."""

from __future__ import annotations

import pytest

from glstring import GLString, parse
from glstring.ast import (
    Allele,
    AlleleList,
    Genotype,
    GenotypeList,
    LocusBlockList,
    PhasedGenotype,
    PossibleLoci,
)

from . import corpus


def test_single_allele_tree_shape():
    root = parse(corpus.SINGLE_ALLELE)
    assert isinstance(root, PossibleLoci)
    assert len(root.alternatives) == 1
    lbl = root.alternatives[0]
    assert isinstance(lbl, LocusBlockList)
    assert len(lbl.blocks) == 1
    gl = lbl.blocks[0]
    assert isinstance(gl, GenotypeList)
    assert len(gl.genotypes) == 1
    g = gl.genotypes[0]
    assert isinstance(g, Genotype)
    assert len(g.copies) == 1
    ph = g.copies[0]
    assert isinstance(ph, PhasedGenotype)
    assert len(ph.segments) == 1
    al = ph.segments[0]
    assert isinstance(al, AlleleList)
    assert al.alleles == (Allele("HLA-A*01:01"),)


def test_allele_ambiguity_binds_tightest():
    # HLA-A*02:01/HLA-A*02:02+HLA-A*03:01 must parse as (a/b) + c,
    # i.e. the '/' binds tighter than '+'.
    root = parse(corpus.EQUIV_FACTORED)
    genotype = root.alternatives[0].blocks[0].genotypes[0]
    assert genotype.is_multi_copy  # two '+' copies
    first_copy = genotype.copies[0]
    assert first_copy.segments[0].is_ambiguous  # the '/' list
    assert len(first_copy.segments[0].alleles) == 2
    # second copy is a single allele
    assert not genotype.copies[1].segments[0].is_ambiguous


def test_possible_binds_loosest():
    # '?' is precedence 0, evaluated first => outermost split.
    root = parse(corpus.KIR_POSSIBLE)
    assert root.is_location_ambiguous
    # The whole string splits into alternatives on '?', each of which contains
    # the '^'-joined locus structure. KIR_POSSIBLE has two '?' => 3 alts.
    assert len(root.alternatives) == 3


def test_precedence_full_hierarchy():
    # Build the Mack canonical example and verify the nesting at each level.
    root = parse(corpus.CANONICAL_MACK)
    assert not root.is_location_ambiguous
    lbl = root.alternatives[0]
    # Three '^'-delimited locus blocks: A, B, DRB1/DRB3.
    assert len(lbl.blocks) == 3
    a_block, b_block, drb_block = lbl.blocks
    # A block has genotype ambiguity '|' (two genotypes).
    assert a_block.is_ambiguous
    assert len(a_block.genotypes) == 2
    # First A genotype: (A*02:01/A*02:02) + A*03:01
    g0 = a_block.genotypes[0]
    assert g0.copies[0].segments[0].is_ambiguous
    # DRB block: phased ~ within each copy, two '+' copies.
    drb_g = drb_block.genotypes[0]
    assert drb_g.is_multi_copy
    assert drb_g.copies[0].is_phased  # DRB1~DRB3


def test_phase_order_preserved():
    root = parse(corpus.PHASED)
    ph = root.alternatives[0].blocks[0].genotypes[0].copies[0]
    assert [a.name for seg in ph.segments for a in seg.alleles] == [
        "HLA-DRB1*03:01",
        "HLA-DRB3*01:01",
    ]


def test_order_does_not_change_structure_class():
    # The order of '|' alternatives must not change how the string is parsed.
    a = parse("HLA-A*01:01+HLA-A*02:01|HLA-A*03:01+HLA-A*04:01")
    b = parse("HLA-A*03:01+HLA-A*04:01|HLA-A*01:01+HLA-A*02:01")
    block_a = a.alternatives[0].blocks[0]
    block_b = b.alternatives[0].blocks[0]
    assert block_a.is_ambiguous and block_b.is_ambiguous
    assert len(block_a.genotypes) == len(block_b.genotypes) == 2


def test_loci_first_seen_order():
    gl = GLString.parse(corpus.TWO_LOCUS_UNPHASED)
    assert gl.loci == ("HLA-A", "HLA-B")


def test_kir_variable_copy_number_allowed():
    # Three copies at one locus (no diploid assumption).
    root = parse("KIR2DL4*001+KIR2DL4*002+KIR2DL4*003")
    g = root.alternatives[0].blocks[0].genotypes[0]
    assert len(g.copies) == 3


@pytest.mark.parametrize("text", corpus.ALL_VALID)
def test_all_valid_parse(text):
    assert GLString.is_valid(text)
