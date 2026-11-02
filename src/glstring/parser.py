"""Recursive-descent parser for GL String 1.1.

The grammar is parsed strictly by operator precedence (Mack et al. 2023,
Table 2), *not* by the order in which operators happen to appear. Each grammar
level corresponds to one node type in :mod:`glstring.ast`.

Grammar (EBNF), outermost (loosest) to innermost (tightest)::

    gl_string   := possible
    possible    := locus_blocks ( '?' locus_blocks )*       -> PossibleLoci
    locus_blocks:= genotype_list ( '^' genotype_list )*      -> LocusBlockList
    genotype_list := genotype ( '|' genotype )*              -> GenotypeList
    genotype    := phased ( '+' phased )*                    -> Genotype
    phased      := allele_list ( '~' allele_list )*          -> PhasedGenotype
    allele_list := allele ( '/' allele )*                    -> AlleleList
    allele      := ALLELE_TOKEN                               -> Allele

A valid GL String always parses to a :class:`PossibleLoci` root. GL String 1.0
strings (no ``?``) yield a root with a single alternative.

All errors are :class:`GLStringSyntaxError` carrying the character position of
the offending token, so callers get precise diagnostics (spec item 5).
"""

from __future__ import annotations

from .ast import (
    DELIM_ALLELE,
    DELIM_COPY,
    DELIM_GENOTYPE_LIST,
    DELIM_LOCUS,
    DELIM_PHASE,
    DELIM_POSSIBLE,
    Allele,
    AlleleList,
    Genotype,
    GenotypeList,
    LocusBlockList,
    PhasedGenotype,
    PossibleLoci,
)
from .errors import GLStringSyntaxError
from .lexer import Token, TokenKind, tokenize

__all__ = ["parse"]


class _Parser:
    def __init__(self, tokens: list[Token], text: str) -> None:
        self._tokens = tokens
        self._text = text
        self._pos = 0

    # -- token stream helpers ------------------------------------------------

    def _peek(self) -> Token | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _at_operator(self, op: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.kind is TokenKind.OPERATOR and tok.value == op

    def _end_position(self) -> int:
        """Character position just past the last token (for EOF errors)."""
        if not self._tokens:
            return 0
        last = self._tokens[-1]
        return last.position + len(last.value)

    # -- grammar rules (loosest to tightest) ---------------------------------

    def parse(self) -> PossibleLoci:
        node = self._possible()
        trailing = self._peek()
        if trailing is not None:
            raise GLStringSyntaxError(
                f"Unexpected trailing token {trailing.value!r}",
                position=trailing.position,
                text=self._text,
            )
        return node

    def _possible(self) -> PossibleLoci:
        alts = [self._locus_blocks()]
        while self._at_operator(DELIM_POSSIBLE):
            self._advance()
            alts.append(self._locus_blocks())
        return self._build(PossibleLoci, (tuple(alts),))

    def _locus_blocks(self) -> LocusBlockList:
        blocks = [self._genotype_list()]
        while self._at_operator(DELIM_LOCUS):
            self._advance()
            blocks.append(self._genotype_list())
        return self._build(LocusBlockList, (tuple(blocks),))

    def _genotype_list(self) -> GenotypeList:
        genotypes = [self._genotype()]
        while self._at_operator(DELIM_GENOTYPE_LIST):
            self._advance()
            genotypes.append(self._genotype())
        return self._build(GenotypeList, (tuple(genotypes),))

    def _genotype(self) -> Genotype:
        copies = [self._phased()]
        while self._at_operator(DELIM_COPY):
            self._advance()
            copies.append(self._phased())
        return self._build(Genotype, (tuple(copies),))

    def _phased(self) -> PhasedGenotype:
        segments = [self._allele_list()]
        while self._at_operator(DELIM_PHASE):
            self._advance()
            segments.append(self._allele_list())
        return self._build(PhasedGenotype, (tuple(segments),))

    def _allele_list(self) -> AlleleList:
        alleles = [self._allele()]
        while self._at_operator(DELIM_ALLELE):
            self._advance()
            alleles.append(self._allele())
        return self._build(AlleleList, (tuple(alleles),))

    def _allele(self) -> Allele:
        tok = self._peek()
        if tok is None:
            raise GLStringSyntaxError(
                "Expected an allele but reached end of input",
                position=self._end_position(),
                text=self._text,
            )
        if tok.kind is TokenKind.OPERATOR:
            raise GLStringSyntaxError(
                f"Expected an allele but found operator {tok.value!r}",
                position=tok.position,
                text=self._text,
            )
        self._advance()
        return self._build(Allele, (tok.value,), at=tok.position)

    # -- node construction with error translation ----------------------------

    def _build(self, node_cls, args, *, at: int | None = None):
        """Construct an AST node, translating its invariant ValueErrors into
        GLStringSyntaxError with a useful position."""
        if at is None:
            tok = self._peek()
            at = tok.position if tok is not None else self._end_position()
        try:
            return node_cls(*args)
        except ValueError as exc:
            raise GLStringSyntaxError(str(exc), position=at, text=self._text) from exc


def parse(text: str) -> PossibleLoci:
    """Parse ``text`` into a :class:`~glstring.ast.PossibleLoci` AST root.

    Raises :class:`~glstring.errors.GLStringSyntaxError` on any malformed input,
    including structural violations such as an allele-ambiguity list spanning
    multiple loci.
    """
    tokens = tokenize(text)
    return _Parser(tokens, text).parse()
