"""Small shared text helpers."""

import re


def clean_text(text: str) -> str:
    """Keep line boundaries for section parsing while removing layout noise."""
    text = text.replace("\x00", " ").replace("\xa0", " ").replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    lines = [re.sub(r"[\t \f\v]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
