"""Query correction layer — strategy-pluggable spell + lemma resolution."""

from ri.correction.base import (
    Candidate,
    Corrector,
    CorrectionResult,
    Status,
    Suggestion,
    TokenAnalysis,
)
from ri.correction.levenshtein import LevenshteinCorrector
from ri.correction.lexicon import SurfaceLexicon

__all__ = [
    "Candidate",
    "Corrector",
    "CorrectionResult",
    "LevenshteinCorrector",
    "Status",
    "Suggestion",
    "SurfaceLexicon",
    "TokenAnalysis",
]
