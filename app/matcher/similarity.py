"""Explainable skill overlap plus a broad TF-IDF text similarity score."""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.extractor.skills import extract_skills
from app.models import MatchReport


YEARS_RE = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience\b", re.I)


def match_resume(resume_text: str, jd_text: str, resume_skills: list[str], resume_years: float | None, nlp) -> MatchReport:
    jd_skills = extract_skills(jd_text, nlp)
    resume_set, jd_set = set(resume_skills), set(jd_skills)
    matched = sorted(resume_set & jd_set, key=str.casefold)
    missing = sorted(jd_set - resume_set, key=str.casefold)
    extra = sorted(resume_set - jd_set, key=str.casefold)
    stated_years = [int(match.group(1)) for match in YEARS_RE.finditer(jd_text)]
    jd_years = max(stated_years) if stated_years else None
    experience_gap = round(max(0, jd_years - resume_years), 1) if jd_years is not None and resume_years is not None else None
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([resume_text, jd_text])
        score = round(float(cosine_similarity(matrix[0], matrix[1])[0, 0]) * 100, 1)
    except ValueError:  # Only stop words or punctuation.
        score = 0.0
    if not jd_skills:
        summary = "No skills from the editable taxonomy were found in the job description. Review the text similarity separately."
    elif not missing:
        summary = f"All {len(jd_skills)} recognized JD skills appear in the resume."
    else:
        summary = f"The resume matches {len(matched)} of {len(jd_skills)} recognized JD skills; missing: {', '.join(missing)}."
    if jd_years is not None:
        if resume_years is None:
            summary += f" The JD asks for {jd_years} years of experience; resume dates were insufficient to compare."
        elif experience_gap:
            summary += f" The JD asks for {jd_years} years; the parsed resume is {experience_gap} years short."
        else:
            summary += f" The parsed resume meets the stated {jd_years}-year experience minimum."
    return MatchReport(similarity_score=score, matched_skills=matched, missing_skills=missing, extra_skills=extra, jd_skills=jd_skills, jd_years_required=jd_years, experience_gap_years=experience_gap, gap_summary=summary)
