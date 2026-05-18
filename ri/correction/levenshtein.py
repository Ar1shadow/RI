"""Default corrector — prefix + Levenshtein with TD4-faithful filter/tie-break."""

from __future__ import annotations

from ri.correction.base import (
    Candidate,
    Corrector,
    CorrectionResult,
    Status,
    TokenAnalysis,
)
from ri.correction.lexicon import SurfaceLexicon
from ri.correction.text import (
    common_prefix_length,
    is_entity,
    levenshtein,
    normalize_token,
    tokenize,
    tokenize_with_spans,
)
from ri.preprocessing.tokenizer import lemmatize


class LevenshteinCorrector(Corrector):
    """Per-token corrector preserving the original TD4 scoring semantics."""

    def __init__(
        self,
        lexicon: SurfaceLexicon,
        *,
        seuil_min: int = 2,
        seuil_max: int = 3,
        seuil_proximite: float = 0.4,
        max_distance: int = 2,
    ) -> None:
        self.lexicon = lexicon
        self.seuil_min = seuil_min
        self.seuil_max = seuil_max
        self.seuil_proximite = seuil_proximite
        self.max_distance = max_distance

    def correct(self, query: str) -> CorrectionResult:
        # Re-emit the query unchanged except for tokens that actually got
        # rewritten. Surface forms (including accents and case) are preserved
        # for valid/entity/unknown tokens so downstream NLP (spaCy lemmatizer,
        # parser regex) sees the user's original orthography.
        out_tokens: list[TokenAnalysis] = []
        rendered: list[str] = []
        rendered_lemmas: list[str] = []
        cursor = 0
        for match in tokenize_with_spans(query):
            surface, start, end = match
            rendered.append(query[cursor:start])
            rendered_lemmas.append(query[cursor:start])
            cursor = end
            analysis = self._analyze(surface)
            out_tokens.append(analysis)
            if analysis.status.startswith("corrige") and analysis.correction:
                rendered.append(analysis.correction)
                rendered_lemmas.append(analysis.lemma or analysis.correction)
            else:
                rendered.append(surface)
                rendered_lemmas.append(analysis.lemma or surface)
        rendered.append(query[cursor:])
        rendered_lemmas.append(query[cursor:])
        return CorrectionResult(
            tokens=out_tokens,
            corrected_query="".join(rendered).strip(),
            lemmatized_query="".join(rendered_lemmas).strip(),
        )

    def _analyze(self, token: str) -> TokenAnalysis:
        normalized = normalize_token(token)
        if not normalized:
            return TokenAnalysis(token=token, status="introuvable", correction=None, lemma=None)
        if is_entity(token):
            return TokenAnalysis(token=token, status="entite", correction=token, lemma=token)
        lemma = self.lexicon.lemma_for(token)
        if lemma is not None:
            return TokenAnalysis(token=token, status="valide", correction=normalized, lemma=lemma)
        # spaCy fallback: surface unseen in corpus but its lemma is in vocab → still valid.
        spacy_lemmas = lemmatize(token)
        if spacy_lemmas and self.lexicon.lemma_in_vocab(spacy_lemmas[0]):
            return TokenAnalysis(
                token=token,
                status="valide",
                correction=normalized,
                lemma=spacy_lemmas[0],
            )
        candidates = self._generate_candidates(normalized)
        if not candidates:
            return TokenAnalysis(token=token, status="introuvable", correction=None, lemma=None)
        chosen, status = self._pick(candidates)
        return TokenAnalysis(
            token=token,
            status=status,
            correction=chosen.word,
            lemma=chosen.lemma,
            candidates=candidates,
        )

    def _generate_candidates(self, normalized_token: str) -> list[Candidate]:
        token_len = len(normalized_token)
        if not token_len:
            return []
        out: list[Candidate] = []
        for word in self.lexicon.iter_words():
            word_len = len(word)
            prefix_len = common_prefix_length(normalized_token, word)
            if prefix_len < self.seuil_min:
                continue
            if abs(word_len - token_len) > self.seuil_max:
                continue
            prefix_ratio = prefix_len / max(1, min(token_len, word_len))
            if prefix_ratio < self.seuil_proximite:
                continue
            distance = levenshtein(normalized_token, word)
            if distance > self.max_distance:
                continue
            lemma = self.lexicon.lemma_for(word) or word
            out.append(
                Candidate(
                    word=word,
                    lemma=lemma,
                    prefix_len=prefix_len,
                    prefix_ratio=prefix_ratio,
                    distance=distance,
                )
            )
        return sorted(out, key=lambda c: (c.distance, -c.prefix_len, c.word))

    @staticmethod
    def _pick(candidates: list[Candidate]) -> tuple[Candidate, Status]:
        if len(candidates) == 1:
            return candidates[0], "corrige-candidat-unique"
        best_distance = candidates[0].distance
        tied = [c for c in candidates if c.distance == best_distance]
        chosen = sorted(tied, key=lambda c: (-c.prefix_len, c.word))[0]
        return chosen, "corrige-levenshtein"
