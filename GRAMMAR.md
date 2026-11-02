# GRAMMAR

The formal grammar `glstring` implements, from GL String 1.1 (Mack et al. 2023),
extending GL String 1.0 (Milius et al. 2013).

## Operators and precedence

GL String delimiters are evaluated in numerical precedence order. The delimiter
with the lowest number is evaluated **first** (split outermost, loosest
binding); the highest is evaluated **last** (innermost, tightest binding).

| Precedence | Delimiter | Identifies              | Introduced |
|-----------:|-----------|-------------------------|------------|
| 0          | `?`       | Possible gene locations | GL 1.1     |
| 1          | `^`       | Unphased genes (loci)   | GL 1.0     |
| 2          | `\|`      | Possible genotypes      | GL 1.0     |
| 3          | `+`       | Copies of genes         | GL 1.0     |
| 4          | `~`       | Genes known to be in phase | GL 1.0  |
| 5          | `/`       | Possible alleles        | GL 1.0     |

**The order in which delimited elements appear does not inform parsing.** A
parser must not infer precedence from appearance order. The order of `/`-
alleles or `|`-genotypes implies no likelihood; locus order implies no
chromosomal order.

A GL String containing no `?` is interpreted exactly as GL String 1.0
(backward compatible).

## EBNF

Written loosest (evaluated first) to tightest (evaluated last):

```ebnf
gl_string     = possible ;

possible      = locus_blocks , { "?" , locus_blocks } ;      (* PossibleLoci   *)
locus_blocks  = genotype_list , { "^" , genotype_list } ;    (* LocusBlockList *)
genotype_list = genotype , { "|" , genotype } ;              (* GenotypeList   *)
genotype      = phased , { "+" , phased } ;                  (* Genotype       *)
phased        = allele_list , { "~" , allele_list } ;        (* PhasedGenotype *)
allele_list   = allele , { "/" , allele } ;                  (* AlleleList     *)
allele        = allele_token ;                               (* Allele         *)

allele_token  = { any character except "?" "^" "|" "+" "~" "/" and whitespace } ;
```

Notes:

- Every production has at least one child (empty alternatives are invalid).
- Within one `allele_list`, all alleles must share a single locus (the portion
  before `*`). Mixing loci across `/` is a syntax error.
- `allele_token` content is deliberately permissive: the grammar does not
  validate allele *nomenclature*, only *structure*. Allele existence and
  format are the job of optional, external validators.

## Worked precedence example

The assembled example from Mack et al. (2023), combining precedence levels 1–5:

```
HLA-A*02:01/HLA-A*02:02+HLA-A*03:01|HLA-A*02:07+HLA-A*03:06^HLA-B*08:01+HLA-B*44:02/HLA-B*44:03^HLA-DRB1*03:01~HLA-DRB3*01:01+HLA-DRB1*03:01~HLA-DRB3*01:01
```

parses as (indented by precedence):

```
^-blocks:
  block 1 (locus HLA-A), genotype-ambiguous:
    (HLA-A*02:01 / HLA-A*02:02) + HLA-A*03:01
    |
    HLA-A*02:07 + HLA-A*03:06
  block 2 (locus HLA-B):
    HLA-B*08:01 + (HLA-B*44:02 / HLA-B*44:03)
  block 3 (loci HLA-DRB1, HLA-DRB3):
    (HLA-DRB1*03:01 ~ HLA-DRB3*01:01) + (HLA-DRB1*03:01 ~ HLA-DRB3*01:01)
```

## GL String 1.1 `?` example

The KIR2DL5 gene-location ambiguity example (Mack et al. 2023):

```
KIR2DL5A*0010101+KIR2DL5A*0010201?KIR2DL5A*0010301^KIR2DL5B*0010101?KIR2DL5B*0010201+KIR2DL5B*0010301
```

Because `?` has precedence 0, it splits the whole string first, into three
gene-location alternatives, each an independent `^`-structured GL String.
