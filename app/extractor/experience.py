"""Simple work history parsing and non-overlapping duration calculation."""

import re
from datetime import date

from app.models import Experience

MONTHS = {name: index for index, name in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
DATE_PART = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[ .]+\d{4}|(?:19|20)\d{2}"
DATE_RANGE = re.compile(rf"(?P<start>{DATE_PART})\s*(?:-|–|—|to)\s*(?P<end>{DATE_PART}|present|current|now)", re.I)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def _date_parts(value: str) -> tuple[int, int] | None:
    if value.lower() in {"present", "current", "now"}:
        today = date.today()
        return today.year, today.month
    year = re.search(r"(?:19|20)\d{2}", value)
    if not year:
        return None
    month = MONTHS.get(value[:3].lower(), 1)
    return int(year.group()), month


def _entry(lines: list[str]) -> Experience | None:
    if not lines:
        return None
    date_line = next((line for line in lines[:3] if DATE_RANGE.search(line)), None)
    dates = DATE_RANGE.search(date_line) if date_line else None
    labels = [DATE_RANGE.sub("", line).strip(" |,–—-\t") for line in lines[:3]]
    labels = [line for line in labels if line and not BULLET.match(line)]
    title = company = None
    if labels:
        combined = re.split(r"\s+(?:at|@)\s+|\s+[|–—]\s+", labels[0], maxsplit=1, flags=re.I)
        if len(combined) == 2:
            title, company = combined
        else:
            title = labels[0]
            company = labels[1] if len(labels) > 1 else None
    bullets = [BULLET.sub("", line).strip() for line in lines if BULLET.match(line)]
    if not any([title, company, dates, bullets]):
        return None
    return Experience(title=title, company=company, start_date=dates.group("start") if dates else None, end_date=dates.group("end") if dates else None, bullets=bullets)


def parse_experience(section: str) -> list[Experience]:
    if not section:
        return []
    blocks = [block.splitlines() for block in re.split(r"\n\s*\n", section) if block.strip()]
    # Many resumes have no blank lines: a new dated header starts a new job.
    entries: list[Experience] = []
    for block in blocks:
        groups: list[list[str]] = []
        current: list[str] = []
        for line in block:
            if DATE_RANGE.search(line) and current and any(DATE_RANGE.search(item) for item in current):
                # Move trailing undated heading lines to the new job; they often
                # contain its title and company just before the date range.
                split_at = len(current)
                while split_at > 0 and not DATE_RANGE.search(current[split_at - 1]) and not BULLET.match(current[split_at - 1]):
                    split_at -= 1
                groups.append(current[:split_at])
                current = current[split_at:]
            current.append(line)
        if current:
            groups.append(current)
        entries.extend(entry for group in groups if (entry := _entry(group)))
    return entries


def years_of_experience(entries: list[Experience]) -> float | None:
    months: set[int] = set()
    for entry in entries:
        if not entry.start_date or not entry.end_date:
            continue
        start, end = _date_parts(entry.start_date), _date_parts(entry.end_date)
        if not start or not end:
            continue
        first, last = start[0] * 12 + start[1], end[0] * 12 + end[1]
        if 0 <= last - first <= 720:
            months.update(range(first, last + 1))
    return round(len(months) / 12, 1) if months else None
