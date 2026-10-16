"""Split a resume at common standalone headings."""

import re

HEADINGS = {
    "experience": {"experience", "work experience", "professional experience", "employment", "employment history", "work history", "career history", "professional background"},
    "education": {"education", "academic background", "academic history", "qualifications"},
    "skills": {"skills", "technical skills", "core skills", "technologies", "technical expertise"},
    "projects": {"projects", "personal projects", "selected projects"},
}


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        heading = re.sub(r"[:\s]+$", "", line.strip().lower())
        category = next((name for name, names in HEADINGS.items() if heading in names), None)
        if category:
            current = category
            sections.setdefault(current, [])
        else:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}
