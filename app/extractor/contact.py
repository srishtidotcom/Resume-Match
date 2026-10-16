"""Contact extraction: regex for contact details, NER plus header rules for name."""

import re

from app.models import Contact

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")
BAD_NAME_WORDS = {"resume", "curriculum", "vitae", "email", "phone", "linkedin", "github", "portfolio", "summary", "experience", "engineer", "developer", "scientist"}


def _looks_like_name(line: str) -> bool:
    words = line.strip().split()
    return (
        2 <= len(words) <= 4
        and all(re.fullmatch(r"[A-Za-z][A-Za-z'.-]*", word) for word in words)
        and not any(word.casefold() in BAD_NAME_WORDS for word in words)
    )


def extract_contact(text: str, nlp) -> Contact:
    email = EMAIL_RE.search(text)
    phone = PHONE_RE.search(text)
    top_lines = [line.strip() for line in text.splitlines()[:10] if line.strip()]
    header = "\n".join(top_lines)
    # NER is useful when the name is embedded in a line, but a clean first line is
    # generally more reliable on resumes than an unrestricted PERSON entity.
    candidates = [line for line in top_lines[:4] if _looks_like_name(line)]
    name = candidates[0] if candidates else None
    if not name:
        people = [ent.text.strip() for ent in nlp(header).ents if ent.label_ == "PERSON"]
        name = next((person for person in people if _looks_like_name(person)), None)
    return Contact(name=name, email=email.group() if email else None, phone=phone.group().strip() if phone else None)
