"""Deterministic skill extraction with spaCy's PhraseMatcher."""

from functools import lru_cache

from spacy.matcher import PhraseMatcher

from app.skills_taxonomy import SKILLS


@lru_cache(maxsize=1)
def _matchers(vocab):
    # LOWER handles ordinary names; ORTH protects short ambiguous abbreviations.
    lower = PhraseMatcher(vocab, attr="LOWER")
    exact = PhraseMatcher(vocab, attr="ORTH")
    return lower, exact


def build_skill_matchers(nlp):
    lower, exact = _matchers(nlp.vocab)
    if len(lower) or len(exact):
        return lower, exact
    for canonical, aliases in SKILLS.items():
        for alias in set([canonical, *aliases]):
            target = exact if len(alias) <= 3 and alias.isalpha() else lower
            target.add(canonical, [nlp.make_doc(alias)])
    return lower, exact


def extract_skills(text: str, nlp) -> list[str]:
    doc = nlp.make_doc(text)
    lower, exact = build_skill_matchers(nlp)
    found = {nlp.vocab.strings[match_id] for matcher in (lower, exact) for match_id, _, _ in matcher(doc)}
    return sorted(found, key=str.casefold)
