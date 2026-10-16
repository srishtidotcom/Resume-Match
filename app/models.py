"""Public JSON response shape."""

from pydantic import BaseModel, Field


class Contact(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class Experience(BaseModel):
    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str | None = None
    degree: str | None = None
    dates: str | None = None


class Resume(BaseModel):
    contact: Contact
    skills: list[str]
    experience: list[Experience]
    education: list[Education]
    years_of_experience: float | None = None


class MatchReport(BaseModel):
    similarity_score: float = Field(ge=0, le=100, description="TF-IDF cosine similarity percentage")
    matched_skills: list[str]
    missing_skills: list[str]
    extra_skills: list[str]
    jd_skills: list[str]
    jd_years_required: int | None = None
    experience_gap_years: float | None = None
    gap_summary: str


class ParseResponse(BaseModel):
    resume: Resume
    match: MatchReport | None = None
