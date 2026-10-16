"""Run with: uvicorn app.main:app --reload"""

from functools import lru_cache
from pathlib import Path

import spacy
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.extractor.contact import extract_contact
from app.extractor.education import parse_education
from app.extractor.experience import parse_experience, years_of_experience
from app.extractor.sections import split_sections
from app.extractor.skills import extract_skills
from app.extractor.text import TextExtractionError, extract_jd_file, extract_text
from app.matcher.similarity import match_resume
from app.models import ParseResponse, Resume
from app.utils import clean_text

app = FastAPI(title="Resume Match", version="0.1.0")


@lru_cache(maxsize=1)
def get_nlp():
    try:
        return spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])
    except OSError as exc:
        raise RuntimeError("spaCy model missing. Run: python -m spacy download en_core_web_sm") from exc


def parse_resume(resume_text: str, jd_text: str | None = None) -> ParseResponse:
    nlp = get_nlp()
    sections = split_sections(resume_text)
    experience = parse_experience(sections.get("experience", ""))
    skills = extract_skills(resume_text, nlp)
    resume = Resume(
        contact=extract_contact(sections.get("header", "") or resume_text, nlp),
        skills=skills,
        experience=experience,
        education=parse_education(sections.get("education", "")),
        years_of_experience=years_of_experience(experience),
    )
    match = match_resume(resume_text, jd_text, skills, resume.years_of_experience, nlp) if jd_text else None
    return ParseResponse(resume=resume, match=match)


@app.post("/parse", response_model=ParseResponse)
async def parse(
    resume: UploadFile = File(...),
    jd_text: str | None = Form(None),
    jd_file: UploadFile | None = File(None),
):
    if jd_text and jd_file and jd_file.filename:
        raise HTTPException(400, "Provide either JD text or a JD file, not both.")
    try:
        resume_text = extract_text(resume.filename or "", await resume.read())
        if jd_file and jd_file.filename:
            jd = extract_jd_file(jd_file.filename, await jd_file.read())
        else:
            jd = clean_text(jd_text or "")
        if (jd_text is not None or jd_file is not None) and not jd:
            raise TextExtractionError("The job description is empty.")
    except TextExtractionError as exc:
        raise HTTPException(400, str(exc)) from exc
    return parse_resume(resume_text, jd or None)


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")
