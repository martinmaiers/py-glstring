# API

Public interface of `glstring`. Import everything from the top-level package.

```python
from glstring import GLString, parse, serialize, canonicalize, smart_sort
```

## `GLString`

Immutable, parsed GL String. Construct with `GLString.parse`.

### Constructors

| Method | Returns | Description |
|--------|---------|-------------|
| `GLString.parse(text: str)` | `GLString` | Parse `text`; raises `GLStringSyntaxError` on malformed input. |
| `GLString.is_valid(text: str)` | `bool` | True iff `text` is syntactically valid. Syntax only — never checks allele existence. |

### Serialization

| Method | Returns | Description |
|--------|---------|-------------|
| `gl.original()` | `str` | Exact original source text (lexical round-trip). |
| `gl.to_string()` | `str` | Structural serialization; `parse(gl.to_string()).root == gl.root`. |
| `gl.canonicalize(*, legacy=False)` | `GLString` | Canonical form: de-dup + deterministic smart-sort. Meaning-preserving. |
| `gl.smart_sort(*, legacy=False)` | `GLString` | Alias of `canonicalize`. |

### Structural queries

| Member | Returns | Description |
|--------|---------|-------------|
| `gl.loci` | `tuple[str, ...]` | Distinct loci, first-seen order. |
| `gl.get_locus(locus: str)` | `tuple[GenotypeList, ...]` | Locus block(s) referencing `locus`; empty if absent. |
| `gl.is_ambiguous()` | `bool` | Any allele (`/`), genotype (`|`), or gene-location (`?`) ambiguity. |
| `gl.is_fully_phased()` | `bool` | Single, unambiguous, fully phased multilocus genotype. |
| `gl.is_location_ambiguous()` | `bool` | Gene-location ambiguity (`?`) present. |
| `gl.root` | `PossibleLoci` | The underlying AST root (advanced use). |

`str(gl)` is `gl.to_string()`.

## Module-level functions

| Function | Returns | Description |
|----------|---------|-------------|
| `parse(text: str)` | `PossibleLoci` | Parse to the AST root. |
| `serialize(node: GLNode)` | `str` | Structurally serialize any AST node. |
| `canonicalize(node: PossibleLoci, *, legacy=False)` | `PossibleLoci` | Canonicalize an AST root. |
| `smart_sort(text: str, *, legacy=False)` | `str` | Parse, canonicalize, and serialize in one call. |
| `allele_sort_key(allele: Allele)` | `tuple` | The deterministic numeric ordering key for an allele. |

### `smart_sort` / `canonicalize` options

- `legacy=False` (default): orders unordered levels (`/ | ^ ?`); **preserves**
  `~` phase order and `+` gene-copy order.
- `legacy=True`: additionally sorts `~` and `+`, reproducing the historical
  `SmartSort.pm` convention. See [DESIGN.md](DESIGN.md) §6.4.

## AST nodes

All are frozen (immutable, hashable) dataclasses. Each exposes `to_string()` and
a `loci` property.

| Node | Operator | Key field |
|------|----------|-----------|
| `PossibleLoci` | `?` | `alternatives: tuple[LocusBlockList, ...]` |
| `LocusBlockList` | `^` | `blocks: tuple[GenotypeList, ...]` |
| `GenotypeList` (alias `LocusBlock`) | `\|` | `genotypes: tuple[Genotype, ...]` |
| `Genotype` | `+` | `copies: tuple[PhasedGenotype, ...]` |
| `PhasedGenotype` | `~` | `segments: tuple[AlleleList, ...]` |
| `AlleleList` | `/` | `alleles: tuple[Allele, ...]` |
| `Allele` | — | `name: str`; derived `locus`, `fields` |

Helpful predicates: `PossibleLoci.is_location_ambiguous`,
`GenotypeList.is_ambiguous`, `Genotype.is_multi_copy`, `PhasedGenotype.is_phased`,
`AlleleList.is_ambiguous`.

## Errors

| Class | Base | Raised when |
|-------|------|-------------|
| `GLStringError` | `ValueError` | Base for all library errors. |
| `GLStringSyntaxError` | `GLStringError` | Malformed input; carries `.position` and `.text`. |
| `ExpansionLimitError` | `GLStringError` | Reserved for enumeration limits (future milestone). |

## CLI

```
glstring validate GLSTRING      # exit 0 valid, 1 invalid (diagnostic on stderr)
glstring parse GLSTRING         # indented AST tree
glstring canonicalize GLSTRING  # canonical (smart-sorted) form
glstring --version
```

Pass `-` as `GLSTRING` to read from stdin.
