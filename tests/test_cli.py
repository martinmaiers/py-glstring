"""CLI tests."""

from __future__ import annotations

import pytest

from glstring.cli import main

from . import corpus


def test_validate_valid(capsys):
    rc = main(["validate", corpus.SIMPLE_GENOTYPE])
    assert rc == 0
    assert "VALID" in capsys.readouterr().out


def test_validate_invalid(capsys):
    rc = main(["validate", "HLA-A*01:01+"])
    assert rc == 1
    assert "INVALID" in capsys.readouterr().err


def test_parse_tree(capsys):
    rc = main(["parse", corpus.EQUIV_FACTORED])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PossibleLoci" in out
    assert "AlleleList" in out
    assert "Allele 'HLA-A*02:01'" in out


def test_canonicalize_cli(capsys):
    rc = main(["canonicalize", "HLA-A*02:02/HLA-A*02:01"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "HLA-A*02:01/HLA-A*02:02"


def test_stdin(capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(corpus.SIMPLE_GENOTYPE))
    rc = main(["validate", "-"])
    assert rc == 0
    assert "VALID" in capsys.readouterr().out


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "glstring" in capsys.readouterr().out
