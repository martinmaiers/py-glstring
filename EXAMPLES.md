# EXAMPLES

Worked examples for HLA and KIR. All are runnable against the installed package.

## Unambiguous single-locus genotype

```python
from glstring import GLString

gl = GLString.parse("HLA-A*01:01+HLA-A*02:01")
gl.loci              # ('HLA-A',)
gl.is_ambiguous()    # False
gl.is_fully_phased() # False  (two copies, inter-copy phase not asserted)
```

## Allele ambiguity (`/`)

```python
gl = GLString.parse("HLA-A*02:01/HLA-A*02:02")
gl.is_ambiguous()            # True
gl.is_location_ambiguous()   # False
```

## Genotype ambiguity (`|`)

```python
gl = GLString.parse("HLA-A*02:02:01G+HLA-A*03:01:01G|HLA-A*02:881+HLA-A*03:303")
gl.is_ambiguous()            # True
```

## Phased (`~`) and the fully-phased check

```python
gl = GLString.parse("HLA-DRB1*03:01~HLA-DRB3*01:01")
gl.is_fully_phased()         # True
gl.loci                      # ('HLA-DRB1', 'HLA-DRB3')
```

A fully phased multilocus diplotype:

```python
gl = GLString.parse(
    "HLA-A*01:01~HLA-B*08:01~HLA-DRB1*03:01+"
    "HLA-A*02:01~HLA-B*07:02~HLA-DRB1*15:01"
)
gl.is_fully_phased()         # True
```

## Unphased loci (`^`)

```python
gl = GLString.parse("HLA-A*01:01+HLA-A*02:01^HLA-B*07:02+HLA-B*08:01")
gl.loci                      # ('HLA-A', 'HLA-B')
gl.is_fully_phased()         # False  (A and B are in separate '^' blocks)
gl.get_locus("HLA-B")        # (GenotypeList for the B block,)
```

## Homozygous

```python
GLString.parse("HLA-A*01:01+HLA-A*01:01").loci   # ('HLA-A',)
```

## KIR with multiple gene copies (no diploid assumption)

```python
gl = GLString.parse("KIR2DL4*001+KIR2DL4*002+KIR2DL4*003")
g = gl.root.alternatives[0].blocks[0].genotypes[0]
len(g.copies)                # 3  -- variable copy number is fine
```

## GL String 1.1 possible gene locations (`?`)

```python
gl = GLString.parse(
    "KIR2DL5A*0010101+KIR2DL5A*0010201?KIR2DL5A*0010301"
    "^KIR2DL5B*0010101?KIR2DL5B*0010201+KIR2DL5B*0010301"
)
gl.is_location_ambiguous()   # True
len(gl.root.alternatives)    # 3  -- '?' splits first (precedence 0)
```

## Smart sort / canonicalization

Numeric (not lexical) allele ordering:

```python
from glstring import smart_sort
smart_sort("HLA-A*01:103/HLA-A*01:11")   # 'HLA-A*01:11/HLA-A*01:103'
```

Deterministic ordering of loci, independent of input order:

```python
smart_sort("HLA-B*07:02^HLA-A*02:01")    # 'HLA-A*02:01^HLA-B*07:02'
```

Deterministic suffix tie-break (numeric fields equal, suffix differs):

```python
smart_sort("HLA-A*01:01N/HLA-A*01:01")   # 'HLA-A*01:01/HLA-A*01:01N'
```

Phase order is preserved (not reordered):

```python
smart_sort("HLA-DRB3*01:01~HLA-DRB1*03:01")  # unchanged: '...DRB3*01:01~...DRB1*03:01'
```

Gene-copy order preserved by default; legacy mode sorts it:

```python
smart_sort("HLA-A*02:01+HLA-A*01:01")                # 'HLA-A*02:01+HLA-A*01:01'
smart_sort("HLA-A*02:01+HLA-A*01:01", legacy=True)   # 'HLA-A*01:01+HLA-A*02:01'
```

Via the object API:

```python
GLString.parse("HLA-A*02:02/HLA-A*02:01").canonicalize().to_string()
# 'HLA-A*02:01/HLA-A*02:02'
```

## Syntax vs structure vs semantics

```python
gl = GLString.parse("HLA-A*01:01 + HLA-A*02:01")  # note the spaces

gl.original()    # 'HLA-A*01:01 + HLA-A*02:01'   (lexical: exact)
gl.to_string()   # 'HLA-A*01:01+HLA-A*02:01'      (structural: whitespace dropped)

# Semantic equivalence is NOT asserted by canonicalization:
a = GLString.parse("HLA-A*02:01/HLA-A*02:02+HLA-A*03:01").canonicalize()
b = GLString.parse("HLA-A*02:01+HLA-A*03:01|HLA-A*02:02+HLA-A*03:01").canonicalize()
a.to_string() == b.to_string()   # False -- same genetic states, different structure
```

These two strings describe the same genotype data (Mack et al. 2023), but
`glstring` does not unify them: that is level-C semantic canonicalization, a
separate problem (see [DESIGN.md](DESIGN.md)).

## Error reporting with character positions

```python
from glstring import GLString
from glstring.errors import GLStringSyntaxError

try:
    GLString.parse("HLA-A*01:01+")
except GLStringSyntaxError as exc:
    print(exc.position)   # 12
    print(exc)            # message with a caret pointing at the offending spot
```
