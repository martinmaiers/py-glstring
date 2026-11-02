# DESIGN

This document is both the **architecture proposal** for `glstring` and the
reference for its design decisions. It covers the AST, the parser, the
syntax/structure/semantics distinction, canonicalization (including the
incorporated smart-sort functionality), grammar ambiguities, and provenance.

## 1. Goals and non-goals

**Goals (M1).**

- A correct, standards-conformant parser for **GL String 1.1** (all six
  operators, including `?`).
- An **immutable, typed AST** that preserves every distinction the grammar can
  express.
- **Lossless** parsing with exact lexical round-tripping on request.
- **Precise** syntax errors carrying character positions.
- **Nomenclature independence**: no allele database, no network, zero runtime
  dependencies.
- Deterministic **smart-sort** ordering and safe **canonicalization**.

**Non-goals (deferred to later milestones).**

- Compatibility checking of a known genetic state against an ambiguous string.
- Lazy enumeration of compatible genotypes/diplotypes.
- Semantic equivalence / full semantic canonicalization.
- Phase-manipulation transforms (remove/retain phase groups).

## 2. The grammar and operator precedence

GL String 1.1 has six operators. They are evaluated in a fixed numerical
*precedence* order (Mack et al. 2023, Table 2), independent of the order they
appear in the string:

| Prec. | Op | Meaning                     | Binds    |
|------:|----|-----------------------------|----------|
| 0     | `?`| Possible gene locations     | loosest  |
| 1     | `^`| Unphased genes (loci)       |          |
| 2     | `\|`| Possible genotypes          |          |
| 3     | `+`| Copies of genes             |          |
| 4     | `~`| Genes known to be in phase  |          |
| 5     | `/`| Possible alleles            | tightest |

"Evaluated first" means split first — so `?` is the **outermost** split and `/`
the **innermost**. See [GRAMMAR.md](GRAMMAR.md) for the formal EBNF.

A critical requirement (Mack et al. 2023): *the order of delimited elements does
not inform parsing.* `glstring` honours this by parsing strictly by precedence
in a recursive-descent parser — never by scanning for "whichever operator
appears first," which is the bug pattern in several prior string-splitting
implementations.

## 3. The AST

One node type per operator, each a frozen (immutable, hashable) dataclass:

```
PossibleLoci      (?)   alternatives: tuple[LocusBlockList, ...]
  LocusBlockList  (^)   blocks:       tuple[GenotypeList, ...]
    GenotypeList  (|)   genotypes:    tuple[Genotype, ...]      (alias LocusBlock)
      Genotype    (+)   copies:       tuple[PhasedGenotype, ...]
        PhasedGenotype (~) segments:  tuple[AlleleList, ...]
          AlleleList (/) alleles:     tuple[Allele, ...]
            Allele        name:       str   (verbatim token)
```

Design choices:

- **Uniform shape across versions.** The root is always `PossibleLoci`. A GL
  String 1.0 string (no `?`) parses to a root with a single alternative, so
  callers never special-case versions.
- **No fixed diploid structure.** `Genotype` holds *any* number of copies;
  `PossibleLoci`/`GenotypeList`/`AlleleList` hold any number of alternatives.
  KIR variable gene content and copy number are first-class. We deliberately do
  **not** impose "both copies span the same loci" invariants (which some prior
  diploid-oriented models enforce), because presence/absence variation makes
  that false in general.
- **Only one structural invariant:** an `AlleleList` (`/`) must reference a
  single locus, because `/` denotes allele ambiguity within one gene. This is
  enforced at construction and surfaced as a syntax error with position.
- **Verbatim allele tokens.** `Allele.name` is stored exactly as written;
  `locus`/`fields` are derived on demand. This guarantees losslessness and keeps
  the AST nomenclature-independent.

The six distinctions required by the task map one-to-one onto node types:

| Distinction                      | Where encoded              |
|----------------------------------|----------------------------|
| Allele ambiguity                 | `AlleleList` with >1 allele |
| Genotype ambiguity               | `GenotypeList` with >1 genotype |
| Known phase                      | `PhasedGenotype` with >1 segment (ordered) |
| Unknown phase (between loci)     | separate `^` blocks        |
| Gene-copy multiplicity           | `Genotype` with >1 copy    |
| Uncertainty about which locus    | `PossibleLoci` with >1 alternative (`?`) |

## 4. Parser and lexer

- The **lexer** produces `ALLELE` and `OPERATOR` tokens, each carrying a 0-based
  character position. Whitespace is insignificant *around* tokens/operators but
  is rejected *inside* an allele token (which has no spaces), with the error
  pointing at the offending space.
- The **parser** is a hand-written recursive descent with one method per
  precedence level, loosest to tightest. Node-invariant `ValueError`s are
  translated into `GLStringSyntaxError` carrying the position of the relevant
  token, and a caret pointer is rendered in the message.

## 5. Three guarantees: syntax, structure, semantics

These are deliberately kept distinct (spec item 5):

1. **Lexical round-trip** — `GLString.original()` returns the exact source text.
   The AST does not promise this (it discards insignificant whitespace); the
   `GLString` facade keeps the source for it.
2. **Structural round-trip** — `parse(serialize(ast)) == ast`. The node
   hierarchy encodes precedence, so no parentheses are needed and the mapping is
   exact.
3. **Semantic equivalence** — two *different* ASTs may describe the same set of
   possible genetic states (e.g. `a/b+c` vs `a+c|b+c`, an equivalence explicitly
   noted by Mack et al. 2023). `glstring` **does not** claim semantic
   equivalence from lexical or structural normalization. Establishing it is the
   level-C problem (below), reserved for a later milestone.

## 6. Canonicalization and smart sort

Canonicalization combines **de-duplication** of unordered alternatives with
**deterministic smart-sort ordering**. Smart sorting incorporates and extends
the behaviour of `SmartSort.pm` (2012, Martin J. Maiers) and its Python port
`gl-smartsort`.

### 6.1 Canonicalization levels

The task defines three levels; `glstring` positions its features explicitly.

- **Level A — Syntactic normalization.** Deterministic sorting of unordered
  components without changing grammar structure. **Implemented** via
  `smart_sort` / `canonicalize`.
- **Level B — Structural canonicalization.** Normalizing structurally equivalent
  ASTs where equivalence is establishable *without expanding genotype
  ambiguity*. **Carefully supported subset implemented**: de-duplication of
  repeated unordered alternatives (`a/a == a`, `g|g == g`, `p?p == p`). Broader
  level-B rewrites are not attempted.
- **Level C — Semantic canonicalization.** A unique representation of all
  possible genetic states (e.g. unifying `a/b+c` and `a+c|b+c`). **Documented as
  a separate, more advanced problem; not implemented.** Smart sorting does
  **not** establish full semantic equivalence.

### 6.2 What is ordered, what is preserved

Ordered (sorted deterministically): `/` alleles, `|` genotypes, `^` locus
blocks, `?` gene-location alternatives — all denote *unordered* alternatives, so
reordering is meaning-preserving.

Preserved by default (not reordered): `~` phased segments (phase is ordered and
biologically meaningful) and `+` gene copies (proving copies are interchangeable
is not always valid — phased copies, KIR CNV). A `legacy=True` mode sorts these
too, to reproduce the historical convention.

### 6.3 Numeric allele ordering

Alleles order by `(locus, numeric-fields, verbatim-token)`:

- Locus first, lexicographically.
- Then field-by-field **numerically**, so `HLA-A*01:11` precedes
  `HLA-A*01:103`. Fields are variable-width and unbounded in count.
- Finally the verbatim token breaks ties, so identical numeric fields with
  differing expression suffixes (`HLA-A*01:01` vs `HLA-A*01:01N`) order
  deterministically — independent of input order.

### 6.4 Relationship to SmartSort.pm / gl-smartsort, and divergences

The sorting behaviour reproduces the documented `gl-smartsort` behaviour and the
original `SmartSort.pm`. **No source code was copied.** `gl-smartsort` declares
MIT in its `pyproject.toml` and `README.md` but ships a **GPL-3.0 `LICENSE`
file**; this unresolved license discrepancy means its code cannot be
incorporated into an Apache-2.0 library. The behaviour was reimplemented
independently from its documented specification. (`pyglstring`, LGPL/GPL, was
likewise not copied.)

Deliberate divergences from legacy behaviour (reported per spec item 7):

| Aspect | Legacy gl-smartsort | glstring (default) |
|--------|---------------------|--------------------|
| Parse model | recursive string split (`if delim in s`) | precedence-correct AST |
| `~` phased segments | reordered | **preserved** (meaningful) |
| `+` gene copies | reordered | **preserved** (use `legacy=True` to sort) |
| Expression suffix | stripped → `01:01` == `01:01N` (tie, input-order-dependent) | kept as deterministic tie-break |
| Numeric fields | first 4 only | unbounded |
| `?` (GL 1.1) | not supported | supported |

A concrete divergence: `smart_sort("HLA-A*02:01+HLA-A*01:01")` returns
`HLA-A*02:01+HLA-A*01:01` by default (copies preserved), whereas legacy
gl-smartsort returns `HLA-A*01:01+HLA-A*02:01`. Use `legacy=True` for the
historical output.

## 7. Grammar / operation ambiguities identified

1. **Precedence-number vs binding direction.** Mack et al. number `?`=0 … `/`=5
   as *evaluation order*; "evaluated first" = outermost split = loosest binding.
   A prior implementation's docstring conflated the numbering with binding
   tightness. `glstring` fixes the orientation: `?` loosest, `/` tightest.
2. **Semantic equivalence of factored vs expanded forms.** `a/b+c` and
   `a+c|b+c` are semantically equal but structurally different. The grammar
   permits both; canonicalization at level A/B does not unify them. This is
   flagged, not silently "normalized."
3. **`+` copy orderedness.** The grammar does not state whether the two sides of
   `+` are an ordered pair or an unordered set. For safety `glstring` treats the
   order as *significant* (does not reorder) by default; legacy mode treats it as
   unordered.
4. **`?` scope.** `?` is outermost, so `a+b?c^d` groups as `(a+b) ? (c^d)`-style
   per precedence. The published KIR example confirms this reading; `glstring`
   follows it exactly.
5. **Allele token syntax is nomenclature-specific.** The standard does not fix a
   regex for allele tokens across all genetic systems. `glstring` therefore
   treats any non-operator, non-space run as a valid token and defers
   existence/format checks to optional external validators (spec item 10).

## 8. Provenance and licensing

- `glstring` is original work, Apache-2.0.
- **TissueTypeForge** (MIT) and **DiplotypeForge** (Apache-2.0) were reviewed for
  design; their AST/parser ideas are compatible and instructive, but `glstring`
  was reimplemented cleanly rather than copied.
- **pyglstring** (LGPL/GPL) and **gl-smartsort** (MIT/GPL discrepancy) were
  reviewed for behaviour only; **no code was copied** from either, for licensing
  reasons documented above.
