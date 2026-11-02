"""Command-line interface for glstring.

Subcommands
-----------
* ``glstring validate GLSTRING`` -- exit 0 if valid, 1 if not; prints a precise
  diagnostic (with a caret pointing at the offending character) on failure.
* ``glstring parse GLSTRING``     -- print an indented structural view of the AST.
* ``glstring canonicalize GLSTRING`` -- print the canonical form of the string.

All subcommands read the GL String from the positional argument, or from stdin
if the argument is ``-``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .api import GLString
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
from .errors import GLStringSyntaxError


def _read_input(value: str) -> str:
    if value == "-":
        return sys.stdin.read().strip()
    return value


def _tree_lines(node: GLNode, indent: int = 0) -> list[str]:
    """Produce an indented textual rendering of an AST node and its children."""
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(node, PossibleLoci):
        label = "PossibleLoci" + (" (?)" if node.is_location_ambiguous else "")
        lines.append(f"{pad}{label}")
        for alt in node.alternatives:
            lines.extend(_tree_lines(alt, indent + 1))
    elif isinstance(node, LocusBlockList):
        lines.append(f"{pad}LocusBlockList (^)")
        for block in node.blocks:
            lines.extend(_tree_lines(block, indent + 1))
    elif isinstance(node, GenotypeList):
        label = "GenotypeList" + (" (|)" if node.is_ambiguous else "")
        lines.append(f"{pad}{label}")
        for g in node.genotypes:
            lines.extend(_tree_lines(g, indent + 1))
    elif isinstance(node, Genotype):
        label = "Genotype" + (" (+)" if node.is_multi_copy else "")
        lines.append(f"{pad}{label}")
        for c in node.copies:
            lines.extend(_tree_lines(c, indent + 1))
    elif isinstance(node, PhasedGenotype):
        label = "PhasedGenotype" + (" (~)" if node.is_phased else "")
        lines.append(f"{pad}{label}")
        for s in node.segments:
            lines.extend(_tree_lines(s, indent + 1))
    elif isinstance(node, AlleleList):
        label = "AlleleList" + (" (/)" if node.is_ambiguous else "")
        lines.append(f"{pad}{label} [{node.locus}]")
        for a in node.alleles:
            lines.extend(_tree_lines(a, indent + 1))
    elif isinstance(node, Allele):
        lines.append(f"{pad}Allele {node.name!r}")
    else:  # pragma: no cover - exhaustive above
        lines.append(f"{pad}{node!r}")
    return lines


def _cmd_validate(text: str) -> int:
    try:
        GLString.parse(text)
    except GLStringSyntaxError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID")
    return 0


def _cmd_parse(text: str) -> int:
    try:
        gl = GLString.parse(text)
    except GLStringSyntaxError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("\n".join(_tree_lines(gl.root)))
    return 0


def _cmd_canonicalize(text: str) -> int:
    try:
        gl = GLString.parse(text)
    except GLStringSyntaxError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print(gl.canonicalize().to_string())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glstring",
        description="Parse, validate, and canonicalize GL String 1.1 strings.",
    )
    parser.add_argument("--version", action="version", version=f"glstring {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("validate", "Check whether a GL String is syntactically valid."),
        ("parse", "Print the parsed AST structure of a GL String."),
        ("canonicalize", "Print the canonical form of a GL String."),
    ):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument(
            "glstring",
            help="The GL String to process, or '-' to read from stdin.",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    text = _read_input(args.glstring)
    dispatch = {
        "validate": _cmd_validate,
        "parse": _cmd_parse,
        "canonicalize": _cmd_canonicalize,
    }
    return dispatch[args.command](text)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
