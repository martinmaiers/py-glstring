# DEVELOPMENT PLAN

`glstring` is developed in milestones. Each milestone is independently useful and
does not depend on later ones. Milestones are not implemented simultaneously.

## M1 — Grammar and object model (this release)

**Status: complete.**

- [x] Review specifications (Milius 2013, Mack 2023) and existing implementations
      (TissueTypeForge, DiplotypeForge, pyglstring, gl-smartsort).
- [x] Immutable, typed AST — one node per operator; no fixed diploid assumption.
- [x] Full GL String 1.1 parsing with correct operator precedence and character-
      position error reporting.
- [x] Structural serialization; exact lexical round-trip via `GLString.original()`.
- [x] Safe canonicalization (level A + a careful subset of level B) with AST-based
      smart sort and numeric allele ordering; `smart_sort` convenience function.
- [x] CLI: `validate`, `parse`, `canonicalize`.
- [x] Comprehensive tests: parsing, precedence, round-trip, immutability,
      canonicalization, error reporting, smart sort, and property-based tests.
- [x] Documentation: README, DESIGN, GRAMMAR, API, EXAMPLES, this plan.

## M2 — Structural operations

- [ ] Richer AST traversal/visitor utilities.
- [ ] Phase queries: known phase relationships between loci.
- [ ] Phase transformations on the AST (not regex): remove phase between selected
      loci, retain specified phase groups.
- [ ] "Contains more phase information than" comparison between two GL Strings.
- [ ] Structural equivalence predicate (level B, broadened).

## M3 — Genetic operations

- [ ] Compatibility: does a known genetic state satisfy an ambiguous GL String?
      (`is_compatible_with`) — symbolic where possible, documented supported
      subset, never silently wrong on unsupported constructs.
- [ ] Lazy enumeration of compatible genotypes/diplotypes with configurable
      expansion limits (`iter_genotypes(max_results=...)`) and
      `ExpansionLimitError` when exceeded.
- [ ] Ambiguity containment.
- [ ] Semantic equivalence for supported cases (level C, partial).
- [ ] Performance tests on large ambiguity expressions.

## M4 — Forge interoperability

- [ ] Verify DiplotypeForge output parses and round-trips.
- [ ] Verify TissueTypeForge input/output interchange.
- [ ] Migration guidance for both Forge projects.
- [ ] Freeze a stable public API (1.0).

## Design invariants held across milestones

- Zero runtime dependencies for parser and AST.
- Nomenclature independence; optional validators only.
- Parsing never expands ambiguity (must stay efficient for huge genotype spaces).
- No claim of semantic equivalence from lexical/structural normalization.
