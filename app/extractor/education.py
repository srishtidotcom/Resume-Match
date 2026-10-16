"""Extract degree, school, and visible dates from Education blocks."""

import re

from app.models import Education

DEGREE_RE = re.compile(r"\b(?:B\.?Tech\.?|M\.?Tech\.?|B\.?E\.?|M\.?E\.?|B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|Ph\.?D\.?|Bachelor(?:'s)?|Master(?:'s)?|Doctorate|Associate(?:'s)?|Senior Secondary|Secondary)(?=\s|,|$)[^\n,|]*", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
DATE_ROW_RE = re.compile(r"^\s*(?P<start>(?:19|20)\d{2})\s*(?:--?|[–—]|to)\s*(?P<end>(?:19|20)\d{2}|present|current)\b", re.I)
DEGREE_START_RE = re.compile(r"^(?:B\.?Tech\.?|M\.?Tech\.?|B\.?E\.?|M\.?E\.?|B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|Ph\.?D\.?|Senior Secondary(?:\s*\([^)]*\))?|Secondary(?:\s*\([^)]*\))?|Bachelor(?:'s)?|Master(?:'s)?|Doctorate|Associate(?:'s)?)(?=\s|,|$)", re.I)
PROGRAM_RE = re.compile(r"^,\s*(?:[A-Za-z&-]+\s+){0,3}(?:Engineering|Science|Technology|Arts|Commerce|Administration|Management|Studies)\b", re.I)
GRADE_RE = re.compile(r"\s+\d{1,3}(?:\.\d+)?\**(?:\s*/\s*\d+(?:\.\d+)?)?%?\s*$")


def _dates(value: str) -> str | None:
    match = DATE_ROW_RE.match(value)
    if match:
        end = match.group("end")
        return f"{match.group('start')} - {end.title() if end.isalpha() else end}"
    year = YEAR_RE.fullmatch(value.strip())
    return year.group() if year else None


def _table_row(line: str) -> Education | None:
    """Read either explicit PDF cells or a year-first row flattened to text."""
    cells = [cell.strip() for cell in line.split("|")]
    if len(cells) >= 3 and (dates := _dates(cells[0])):
        return Education(dates=dates, degree=cells[1] or None, institution=cells[2] or None)

    date_match = DATE_ROW_RE.match(line)
    if not date_match:
        return None
    rest = line[date_match.end():].strip()
    degree_match = DEGREE_START_RE.match(rest)
    if not degree_match:
        return None
    degree = degree_match.group().strip()
    institution = rest[degree_match.end():].strip()
    # In plain extracted text the B.Tech specialization may run into the
    # institution column. Common field endings give us a useful boundary.
    if program := PROGRAM_RE.match(institution):
        degree += program.group()
        institution = institution[program.end():].strip()
    institution = GRADE_RE.sub("", institution).strip(" ,")
    return Education(dates=_dates(date_match.group()), degree=degree, institution=institution or None)


def _is_table_header(line: str) -> bool:
    words = set(re.findall(r"[a-z]+", line.casefold()))
    return {"year", "degree", "institute"} <= words


def parse_education(section: str) -> list[Education]:
    if not section:
        return []
    structured: list[Education] = []
    flattened: list[Education] = []
    other_lines = []
    for line in section.splitlines():
        if _is_table_header(line) or line.lstrip().startswith("*"):
            other_lines.append("")
            continue
        row = _table_row(line)
        if row:
            (structured if "|" in line else flattened).append(row)
            other_lines.append("")
        else:
            other_lines.append(line)

    # Prefer cell-aware rows over flattened duplicates from the same PDF page.
    results = list(structured)
    structured_dates = {row.dates for row in structured}
    results.extend(row for row in flattened if row.dates not in structured_dates)
    blocks = [block.strip() for block in re.split(r"\n\s*\n", "\n".join(other_lines)) if block.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        degree_match = DEGREE_RE.search(block)
        years = YEAR_RE.findall(block)
        if results and not degree_match and not re.search(r"\b(?:University|College|School|Institute)\b", block, re.I):
            continue
        institution = next((line for line in lines if not DEGREE_RE.search(line) and not YEAR_RE.fullmatch(line)), None)
        if not institution and lines:
            institution = re.split(r"\s+[|–—]\s+", lines[0])[0]
            if DEGREE_RE.search(institution):
                institution = None
        if degree_match or institution:
            results.append(Education(institution=institution, degree=degree_match.group().strip() if degree_match else None, dates=" - ".join(years[:2]) if years else None))
    return results
