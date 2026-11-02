# glstring

A standards-conformant Python library for parsing, manipulating, validating,
and serializing **Genotype List (GL) Strings**, implementing the **GL String
1.1** grammar.

`glstring` is a shared, reusable implementation of the GL String grammar for
HLA, KIR, and other immune-polymorphism applications. It is a project of the
**Society for Immune Polymorphism (SIP)** and is intended to be used by
DiplotypeForge, TissueTypeForge, HLA imputation-assessment tools, and any other
application that needs a correct GL String parser. It does **not** depend on
either Forge project.

## Highlights

- **Correct operator precedence.** A real recursive-descent parser builds an
  immutable AST strictly by the published precedence of the six GL String
  operators — never by the order operators happen to appear.
- **All six GL String 1.1 operators**: `/ ~ + | ^ ?` (including the `?`
  gene-location ambiguity delimiter introduced in GL String 1.1).
- **Immutable, typed AST** — one node type per operator, hashable and safe to
  share.
- **No fixed diploid assumption** — variable gene content and copy number (as in
  KIR) are first-class.
- **Lossless** — exact original-text round-tripping on request, distinct from
  structural serialization and from (explicit) canonicalization.
- **Precise errors** — syntax errors carry the offending character position and
  a caret pointer.
- **Nomenclature-independent** — no IPD-IMGT/HLA, KIR database, pyard, HFX, or
  internet access required. Syntax validity and allele existence are separate.
- **Zero runtime dependencies** for the parser and AST. Python 3.12+.

## Installation

```bash
uv pip install -e ".[dev]"   # from a checkout, with dev tools
```

## Quick start

```python
from glstring import GLString

gl = GLString.parse(
    "HLA-A*01:01+HLA-A*02:01^HLA-B*07:02+HLA-B*08:01"
)

print(gl.to_string())        # structural serialization
print(gl.is_valid)           # classmethod: GLString.is_valid(text)
print(gl.loci)               # ('HLA-A', 'HLA-B')
print(gl.is_ambiguous())     # False
print(gl.is_fully_phased())  # False (two unphased '^' blocks)
```

## Command line

```bash
glstring validate "HLA-A*01:01+HLA-A*02:01"
glstring parse "HLA-A*01:01+HLA-A*02:01"
glstring canonicalize "HLA-A*02:01+HLA-A*01:01"
```

`validate` exits 0 for valid input, 1 for invalid (with a diagnostic on
stderr). Pass `-` as the argument to read the GL String from stdin.

## The six operators

| Operator | Precedence | Meaning                         | Node             |
|----------|-----------:|---------------------------------|------------------|
| `?`      | 0          | Possible gene locations (1.1)   | `PossibleLoci`   |
| `^`      | 1          | Unphased genes (loci)           | `LocusBlockList` |
| `\|`     | 2          | Possible genotypes              | `GenotypeList`   |
| `+`      | 3          | Copies of genes                 | `Genotype`       |
| `~`      | 4          | Genes known to be in phase      | `PhasedGenotype` |
| `/`      | 5          | Possible alleles                | `AlleleList`     |

Delimiters are evaluated in numerical precedence order: `?` is evaluated first
(outermost / loosest binding) and `/` last (innermost / tightest binding). See
[GRAMMAR.md](GRAMMAR.md).

## Three kinds of round-trip

These are different guarantees and are not conflated (see [DESIGN.md](DESIGN.md)):

1. **Lexical** — `gl.original()` reproduces the source text exactly.
2. **Structural** — `parse(serialize(ast)) == ast`.
3. **Semantic** — two different ASTs can describe the same genetic states.
   `glstring` does **not** claim semantic equivalence from lexical or structural
   normalization alone. Canonicalization is restricted to a documented,
   provably safe subset.

## Scope (milestone M1)

This release implements **M1: grammar and object model** — the parser, AST,
serialization, safe canonicalization, a public API, and a CLI, with a
comprehensive test suite. Compatibility checking, lazy enumeration, phase
transformations, and semantic equivalence are planned for later milestones; see
[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

## Documentation

- [DESIGN.md](DESIGN.md) — architecture and the syntax/structure/semantics distinction
- [GRAMMAR.md](GRAMMAR.md) — formal grammar and operator precedence
- [API.md](API.md) — public API reference
- [EXAMPLES.md](EXAMPLES.md) — worked HLA and KIR examples
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) — milestones and roadmap

## Citing the standard

- Milius RP, et al. *Genotype List String: a grammar for describing HLA and KIR
  genotyping results in a text string.* Tissue Antigens. 2013;82(2):106–112.
  doi:10.1111/tan.12150
- Mack SJ, et al. *Genotype List String 1.1: Extending the Genotype List String
  Grammar for Describing HLA and Killer-cell Immunoglobulin-like Receptor
  Genotypes.* HLA. 2023;102(2):206–212. doi:10.1111/tan.15126

## License

Apache License 2.0. See [LICENSE](LICENSE). No source code was copied from any
GPL/LGPL-licensed project; see [DESIGN.md](DESIGN.md) for provenance notes.
