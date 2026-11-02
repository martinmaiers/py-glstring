"""Shared corpus of GL String examples drawn from the published standards.

Sources:
* Milius et al. (2013) doi:10.1111/tan.12150
* Mack et al. (2023)  doi:10.1111/tan.15126 (Table 2 and Figure examples)
"""

from __future__ import annotations

# The assembled canonical example from Mack et al. (2023), combining all
# precedence levels 1-5 (no '?').
CANONICAL_MACK = (
    "HLA-A*02:01/HLA-A*02:02+HLA-A*03:01|HLA-A*02:07+HLA-A*03:06"
    "^HLA-B*08:01+HLA-B*44:02/HLA-B*44:03"
    "^HLA-DRB1*03:01~HLA-DRB3*01:01+HLA-DRB1*03:01~HLA-DRB3*01:01"
)

# Mack et al. (2023) '?' (gene-location ambiguity) KIR2DL5 example.
KIR_POSSIBLE = (
    "KIR2DL5A*0010101+KIR2DL5A*0010201?KIR2DL5A*0010301"
    "^KIR2DL5B*0010101?KIR2DL5B*0010201+KIR2DL5B*0010301"
)

# Mack et al. (2023) short '?' example from Table 2.
KIR_POSSIBLE_SHORT = "KIR2DL5B*00201?KIR2DL5A*00501"

# Two equivalent GL Strings for the same genotype data (Mack et al. 2023):
# "HLA-A*02:01/HLA-A*02:02+HLA-A*03:01" == the '|' expansion below.
EQUIV_FACTORED = "HLA-A*02:01/HLA-A*02:02+HLA-A*03:01"
EQUIV_EXPANDED = "HLA-A*02:01+HLA-A*03:01|HLA-A*02:02+HLA-A*03:01"

# Single-operator illustrative examples (Mack et al. 2023, Table 2).
ALLELE_AMBIGUITY = "HLA-A*02:01/HLA-A*02:02"
GENE_COPIES = "HLA-A*02:02+HLA-A*03:01"
PHASED = "HLA-DRB1*03:01~HLA-DRB3*01:01"
GENOTYPE_AMBIGUITY = "HLA-A*02:02:01G+HLA-A*03:01:01G|HLA-A*02:881+HLA-A*03:303"
UNPHASED_LOCI = "HLA-A*02:07+HLA-A*03:06^HLA-B*08:01+HLA-B*44:02"

# Simple unambiguous single-locus genotype.
SIMPLE_GENOTYPE = "HLA-A*01:01+HLA-A*02:01"

# Homozygous genotype.
HOMOZYGOUS = "HLA-A*01:01+HLA-A*01:01"

# Multilocus unphased example from the task prompt.
TWO_LOCUS_UNPHASED = "HLA-A*01:01+HLA-A*02:01^HLA-B*07:02+HLA-B*08:01"

# Fully phased multilocus diplotype (DiplotypeForge style).
FULLY_PHASED = (
    "HLA-A*01:01~HLA-B*08:01~HLA-DRB1*03:01+HLA-A*02:01~HLA-B*07:02~HLA-DRB1*15:01"
)

# A single bare allele.
SINGLE_ALLELE = "HLA-A*01:01"

# Collection of all valid examples for round-trip sweeps.
ALL_VALID = [
    CANONICAL_MACK,
    KIR_POSSIBLE,
    KIR_POSSIBLE_SHORT,
    EQUIV_FACTORED,
    EQUIV_EXPANDED,
    ALLELE_AMBIGUITY,
    GENE_COPIES,
    PHASED,
    GENOTYPE_AMBIGUITY,
    UNPHASED_LOCI,
    SIMPLE_GENOTYPE,
    HOMOZYGOUS,
    TWO_LOCUS_UNPHASED,
    FULLY_PHASED,
    SINGLE_ALLELE,
]

# Invalid strings with the (0-based) character position where parsing should
# fail, where a specific position is expected. None means "any position".
INVALID = [
    ("", None),
    ("^HLA-A*01:01", 0),  # leading operator, no allele
    ("HLA-A*01:01+", None),  # trailing operator, missing allele
    ("HLA-A*01:01++HLA-A*02:01", None),  # doubled operator
    ("HLA-A*01:01/HLA-B*08:01", None),  # '/' mixing loci
    ("HLA-A*01:01 HLA-A*02:01", None),  # interior whitespace / two tokens
    ("HLA-A*01:01^", None),  # trailing '^'
    ("|HLA-A*01:01", 0),  # leading '|'
]
