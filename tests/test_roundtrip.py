"""Round-trip serialization and immutability tests."""

from __future__ import annotations

import dataclasses

import pytest

from glstring import GLString, parse, serialize
from glstring.ast import Allele, AlleleList

from . import corpus


@pytest.mark.parametrize("text", corpus.ALL_VALID)
def test_structural_round_trip(text):
    # parse -> serialize -> parse yields an equal AST.
    root = parse(text)
    reparsed = parse(serialize(root))
    assert reparsed == root


@pytest.mark.parametrize("text", corpus.ALL_VALID)
def test_structural_serialization_matches_input_when_clean(text):
    # For these whitespace-free canonical examples, structural serialization
    # reproduces the input exactly.
    assert serialize(parse(text)) == text


def test_lexical_round_trip_preserves_whitespace_difference():
    # Structural output may normalise insignificant whitespace, but original()
    # always returns the exact source.
    text = "HLA-A*01:01 + HLA-A*02:01"
    gl = GLString.parse(text)
    assert gl.original() == text
    # Structural form drops the insignificant spaces around '+'.
    assert gl.to_string() == "HLA-A*01:01+HLA-A*02:01"


def test_ast_is_frozen():
    al = AlleleList((Allele("HLA-A*01:01"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        al.alleles = ()  # type: ignore[misc]


def test_allele_is_hashable():
    assert hash(Allele("HLA-A*01:01")) == hash(Allele("HLA-A*01:01"))
    s = {Allele("HLA-A*01:01"), Allele("HLA-A*01:01"), Allele("HLA-A*02:01")}
    assert len(s) == 2


def test_glstring_equality_by_ast():
    a = GLString.parse("HLA-A*01:01 + HLA-A*02:01")
    b = GLString.parse("HLA-A*01:01+HLA-A*02:01")
    # Sources differ, so the dataclasses are not equal...
    assert a != b
    # ...but their parsed ASTs are equal.
    assert a.root == b.root


def test_allele_fields_and_locus():
    a = Allele("HLA-DRB1*03:01")
    assert a.locus == "HLA-DRB1"
    assert a.fields == ("03", "01")
    bare = Allele("HLA-A")
    assert bare.locus == "HLA-A"
    assert bare.fields == ()
