"""glstring -- a standards-conformant GL String 1.1 library.

Parse, validate, serialize, and canonicalize Genotype List (GL) Strings for
HLA, KIR, and other immune-polymorphism genetic systems.

Standards
---------
Implements the GL String 1.1 grammar:

* Milius et al. (2013) "Genotype List String: a grammar for describing HLA and
  KIR genotyping results in a text string." Tissue Antigens 82(2):106-112.
  doi:10.1111/tan.12150
* Mack et al. (2023) "Genotype List String 1.1: Extending the Genotype List
  String Grammar for Describing HLA and Killer-cell Immunoglobulin-like
  Receptor Genotypes." HLA 102(2):206-212. doi:10.1111/tan.15126

The library has zero runtime dependencies for parsing and the AST, and never
requires a nomenclature database or internet access.
"""

from __future__ import annotations

from .api import GLString
from .ast import (
    Allele,
    AlleleList,
    Genotype,
    GenotypeList,
    GLNode,
    LocusBlock,
    LocusBlockList,
    PhasedGenotype,
    PossibleLoci,
)
from .errors import ExpansionLimitError, GLStringError, GLStringSyntaxError
from .parser import parse
from .serializer import canonicalize, serialize, smart_sort
from .smartsort import allele_sort_key

__version__ = "0.1.0"

__all__ = [
    "GLString",
    "parse",
    "serialize",
    "canonicalize",
    "smart_sort",
    "allele_sort_key",
    "GLNode",
    "Allele",
    "AlleleList",
    "PhasedGenotype",
    "Genotype",
    "GenotypeList",
    "LocusBlock",
    "LocusBlockList",
    "PossibleLoci",
    "GLStringError",
    "GLStringSyntaxError",
    "ExpansionLimitError",
    "__version__",
]
