# How Resume Match works

Resume Match uses a **rule-based extraction pipeline with spaCy support**, followed by **TF-IDF cosine similarity** and explicit skill-set comparison. It does not train a resume model, call an LLM, or use a third-party resume parser. The small spaCy English model helps identify a person's name; the main field extraction remains deterministic.

## The full flow

```text
PDF/DOCX resume ──> text extraction ──> cleaning ──> sections
                                               ├── contact
                                               ├── skills
                                               ├── experience + years
                                               └── education

optional JD text/TXT/PDF/DOCX ──> cleaning + skills ──> skill comparison
resume text + JD text ──> TF-IDF vectors ──> cosine similarity
all extracted data ──> Pydantic models ──> JSON response
```

The upload endpoint is `POST /parse` in [`app/main.py`](app/main.py). It accepts one PDF or DOCX resume and, optionally, either `jd_text` or `jd_file`. `parse_resume()` connects the extraction modules and returns a `ParseResponse` defined in [`app/models.py`](app/models.py). If there is no JD, `match` is `null`.

## 1. Turn files into usable text

[`app/extractor/text.py`](app/extractor/text.py) uses `pdfplumber` for PDF pages and `python-docx` for DOCX paragraphs and tables. PDF text must be selectable; there is no OCR. A JD uploaded as `.txt` is decoded as UTF-8. Unsupported, unreadable, or empty files produce a clear 400 error.

[`app/utils.py`](app/utils.py) removes null characters, normalizes spaces and line endings, and collapses excessive blank lines. It **keeps line breaks** because headings, dates, and bullet lists depend on them.

PDF table text often loses its columns when extracted as ordinary text. For ruled education tables, the PDF extractor also asks `pdfplumber` for cell rows and records them as `year | degree | institute | grade`. Education parsing can also read a flattened year-first row when table detection does not recover cells.

## 2. Locate resume sections

[`app/extractor/sections.py`](app/extractor/sections.py) compares each standalone line against known headings such as “Experience,” “Work History,” “Education,” and “Technical Skills.” Lines between headings belong to the current section. Text before the first heading is the header, where the name and contact details usually appear. This is a heading rule, not a learned classifier.

## 3. Extract fields

### Contact

[`app/extractor/contact.py`](app/extractor/contact.py) finds email and phone with regular expressions. For the name, it first looks for a short, plausible name in the first few lines. If that fails, it uses spaCy `PERSON` entities found near the top of the document. The header rule is preferred because resumes often put the name alone on the first line.

### Skills: the main extraction algorithm

[`app/skills_taxonomy.py`](app/skills_taxonomy.py) holds canonical skill names and aliases; for example, `k8s` maps to `Kubernetes` and `JS` maps to `JavaScript`. [`app/extractor/skills.py`](app/extractor/skills.py) builds spaCy `PhraseMatcher` patterns from that dictionary, matches them against the text, converts each hit to its canonical name, removes duplicates, and sorts the result.

Most aliases are matched without case sensitivity. Alphabetic aliases of three characters or fewer use exact case to reduce accidental matches with ordinary words. The same matcher is applied to the full resume and to the JD, so both sides use the same skill vocabulary. Adding a skill or alias means editing the taxonomy dictionary; no training step is required.

### Work experience and years

[`app/extractor/experience.py`](app/extractor/experience.py) splits the experience section into likely jobs using blank lines and recognizable date ranges. It attempts to separate title and company from a line such as `Software Engineer at Acme Labs`, and collects lines beginning with bullet markers. Dates may contain a month and year, a year alone, or `Present`/`Current`/`Now`.

For total experience, each valid job range is converted to month numbers. The parser takes the **union of covered months** and divides its size by 12, rounded to one decimal place. Overlapping jobs therefore do not count the same month twice. If no usable ranges exist, years of experience is `null`. For a current role, `Present` means the date when parsing runs.

### Education

[`app/extractor/education.py`](app/extractor/education.py) recognizes conventional degree lines and year-first table rows. It handles PDF rows with `|` cell separators and rows flattened into text, including `B.Tech`, `Senior Secondary`, and `Secondary`. Table headers and grade footnotes are skipped; duplicate flattened rows are omitted when cell-aware rows are present. The output records institution, degree, and visible dates when found.

## 4. Compare with a job description

[`app/matcher/similarity.py`](app/matcher/similarity.py) reports three **skill-set operations** on canonical names:

| Report field | Calculation | Meaning |
| --- | --- | --- |
| `matched_skills` | Resume skills ∩ JD skills | Recognized on both sides |
| `missing_skills` | JD skills − resume skills | Requested in the JD but not recognized in the resume |
| `extra_skills` | Resume skills − JD skills | Recognized in the resume but not the JD |

For example, if the resume has `Python`, `Docker`, and `FastAPI`, while the JD has `Python`, `Docker`, and `Kubernetes`, the matched skills are `Python` and `Docker`; `Kubernetes` is missing; `FastAPI` is extra. “Missing” means **not detected by this matcher**, not proof that the person lacks the skill.

The JD is also searched for simple phrases such as `5 years of experience`. If there are several such phrases, the largest number is treated as the stated minimum. `experience_gap_years` is `max(0, JD minimum − parsed resume years)`, rounded to one decimal. It is `null` when the JD has no recognizable minimum or the resume dates cannot be calculated.

### Text similarity score

`TfidfVectorizer(stop_words="english", ngram_range=(1, 2))` turns the **full cleaned resume text and full cleaned JD text** into two TF-IDF vectors. It considers single words and two-word phrases and excludes common English stop words. `cosine_similarity` measures their angle:

```text
similarity_score = round(100 × cosine(TF-IDF(resume), TF-IDF(JD)), 1)
```

The result is between 0 and 100. If the text contains no usable terms, it is 0.0. This score measures wording overlap; it is **not** a percentage of JD requirements met, a probability of being hired, or a weighted combination of skills and experience. The skill lists and experience gap are shown separately so the comparison stays understandable. A short gap summary describes recognized missing skills and any detected experience shortfall.

## Output and limits

[`app/models.py`](app/models.py) defines Pydantic models for contact, work entries, education, resume details, and the optional match report. FastAPI serializes these as JSON. [`app/index.html`](app/index.html) displays the same response in cards and offers a JSON download; it does not change the algorithm.

This approach is intentionally small and editable. It depends on selectable text, familiar section headings, recognizable date formats, and the skills in the taxonomy. Multi-column layouts, unusual job formatting, misspellings, scanned PDFs, and skills outside the taxonomy can lead to omissions or wrong fields. The text similarity score may also be low when equivalent experience is phrased differently.
