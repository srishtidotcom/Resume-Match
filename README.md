# Resume Match

A small, local FastAPI app that extracts structured fields from PDF or DOCX resumes and optionally compares a resume with a job description. It uses rules, spaCy's small English model, and TF-IDF. No external AI service or resume-parser package is involved.

## Install and run

Use Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/> for the one-page upload and results UI. It shows parsed details and JD gaps in cards, with a JSON download button. API documentation is at <http://127.0.0.1:8000/docs>.

The included `samples/sample_resume.docx` is ready to upload. `samples/sample_resume.txt` is its editable source; run `python samples/create_docx.py` to rebuild the DOCX after changing it. `samples/sample_jd.txt` contains a matching example JD. To call the API:

```bash
curl -X POST http://127.0.0.1:8000/parse \
  -F "resume=@samples/sample_resume.docx" \
  -F "jd_text=$(<samples/sample_jd.txt)"
```

You may instead upload a UTF-8 TXT, PDF, or DOCX job description with `-F "jd_file=@samples/sample_jd.txt"`. Supply either `jd_text` or `jd_file`. Without either, `match` is `null`. Resumes must be PDF or DOCX.

## How it works

See [algo.md](algo.md) for a detailed walkthrough of the extraction and comparison algorithms.

1. `pdfplumber` or `python-docx` extracts selectable text; whitespace is normalized while line breaks are retained for section parsing.
2. Common headings split the resume into experience, education, and other sections. For ruled PDF education tables, `pdfplumber` also supplies cell values; year-first rows are recognized when a table is flattened into plain text. Regex finds email and phone. A top-of-document rule and spaCy PERSON entities find a likely name.
3. A spaCy `PhraseMatcher` finds aliases from `app/skills_taxonomy.py` and returns canonical names. Edit this dictionary to add domain-specific skills. Very short aliases are case-sensitive to avoid common-word matches.
4. Date ranges and bullets provide basic work entries. Experience duration is the union of months covered by recognizable ranges, so overlapping jobs do not double count. Missing or unusual dates produce `null` for years of experience.
5. When a JD is supplied, the same skill matcher returns matched, missing, and extra skills. A simple pattern checks stated minimum years against parsed resume dates. TF-IDF cosine similarity over the full texts is shown as a 0–100 text similarity score. It is separate from skill coverage and is not a hiring score.

This rule-based parser works best with conventional headings and selectable text. It does not perform OCR, infer every job format, or understand skills absent from the taxonomy.

## Example JSON

This example is the parsed response for the included sample resume and JD:

```json
{
  "resume": {
    "contact": {"name": "Alex Morgan", "email": "alex.morgan@example.com", "phone": "+1 (415) 555-0123"},
    "skills": ["AWS", "Docker", "FastAPI", "Git", "Pandas", "PostgreSQL", "Python", "scikit-learn"],
    "experience": [
      {"title": "Software Engineer", "company": "Acme Labs", "start_date": "Jan 2022", "end_date": "Dec 2024", "bullets": ["Built FastAPI services backed by PostgreSQL.", "Deployed Docker containers on AWS."]},
      {"title": "Data Analyst", "company": "Northstar Analytics", "start_date": "Jun 2020", "end_date": "Dec 2021", "bullets": ["Automated reporting with Python and Pandas."]}
    ],
    "education": [{"institution": "State University", "degree": "B.S. in Computer Science", "dates": "2020"}],
    "years_of_experience": 4.6
  },
  "match": {
    "similarity_score": 20.1,
    "matched_skills": ["AWS", "Docker", "FastAPI", "PostgreSQL", "Python"],
    "missing_skills": ["CI/CD", "Kubernetes", "Terraform"],
    "extra_skills": ["Git", "Pandas", "scikit-learn"],
    "jd_skills": ["AWS", "CI/CD", "Docker", "FastAPI", "Kubernetes", "PostgreSQL", "Python", "Terraform"],
    "jd_years_required": 5,
    "experience_gap_years": 0.4,
    "gap_summary": "The resume matches 5 of 8 recognized JD skills; missing: CI/CD, Kubernetes, Terraform. The JD asks for 5 years; the parsed resume is 0.4 years short."
  }
}
```
