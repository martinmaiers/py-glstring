"""Error-reporting tests: invalid strings and character positions."""

from __future__ import annotations

import pytest

from glstring import GLString, parse
from glstring.errors import GLStringSyntaxError

from . import corpus


@pytest.mark.parametrize("text,position", corpus.INVALID)
def test_invalid_strings_raise(text, position):
    with pytest.raises(GLStringSyntaxError) as exc_info:
        parse(text)
    if position is not None:
        assert exc_info.value.position == position


def test_is_valid_false_for_invalid():
    assert not GLString.is_valid("HLA-A*01:01+")
    assert not GLString.is_valid("")


def test_mixed_locus_allele_list_reports_position():
    # '/' may not join alleles of different loci.
    with pytest.raises(GLStringSyntaxError) as exc_info:
        parse("HLA-A*01:01/HLA-B*08:01")
    assert "single locus" in str(exc_info.value)


def test_none_input_raises():
    with pytest.raises(GLStringSyntaxError):
        parse(None)  # type: ignore[arg-type]


def test_trailing_operator_position():
    text = "HLA-A*01:01+"
    with pytest.raises(GLStringSyntaxError) as exc_info:
        parse(text)
    # Error points at or beyond the trailing '+'.
    assert exc_info.value.position is not None
    assert exc_info.value.position >= text.index("+")


def test_caret_in_message():
    text = "HLA-A*01:01 HLA-A*02:01"
    with pytest.raises(GLStringSyntaxError) as exc_info:
        parse(text)
    msg = str(exc_info.value)
    assert "^" in msg  # caret pointer rendered
    assert "position" in msg


def test_operator_where_allele_expected():
    with pytest.raises(GLStringSyntaxError) as exc_info:
        parse("HLA-A*01:01+^HLA-B*08:01")
    assert exc_info.value.position is not None
