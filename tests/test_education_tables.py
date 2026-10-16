"""Regression checks for ruled PDF education tables and ordinary resumes."""

import unittest
from pathlib import Path

from app.extractor.education import parse_education
from app.extractor.sections import split_sections
from app.extractor.text import extract_text


def _pdf_with_education_table() -> bytes:
    """Tiny selectable-text PDF with the same four-column layout as the report."""
    rows = [
        ("Year", "Degree", "Institute", "CGPA / %"),
        ("2024-Present", "B.Tech, Computer Engineering", "Pune Institute of Computer Technology", "9.23/10.0"),
        ("2021-2023", "Senior Secondary (HSC)", "Maharashtra State Board (MSBSHSE)", "83.83%"),
        ("2019-2021", "Secondary (AISSE)", "Central Board of Secondary Education", "96.8%"),
    ]
    xs, ys = [40, 150, 390, 750, 860], [740, 710, 680, 650, 620]
    commands = ["BT /F1 12 Tf 40 765 Td (Education) Tj ET"]
    commands += [f"{x} 620 m {x} 740 l S" for x in xs]
    commands += [f"40 {y} m 860 {y} l S" for y in ys]
    for row_number, row in enumerate(rows):
        for column, value in enumerate(row):
            value = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"BT /F1 10 Tf {xs[column] + 4} {ys[row_number] - 20} Td ({value}) Tj ET")
    stream = "\n".join(commands).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 900 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    startxref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF".encode())
    return bytes(pdf)


class EducationTableTests(unittest.TestCase):
    def test_pdf_table(self):
        text = extract_text("education.pdf", _pdf_with_education_table())
        education = parse_education(split_sections(text)["education"])
        self.assertEqual(len(education), 3)
        self.assertEqual(education[0].model_dump(), {
            "institution": "Pune Institute of Computer Technology",
            "degree": "B.Tech, Computer Engineering",
            "dates": "2024 - Present",
        })
        self.assertEqual(education[1].degree, "Senior Secondary (HSC)")
        self.assertEqual(education[2].institution, "Central Board of Secondary Education")

    def test_existing_docx(self):
        path = Path(__file__).resolve().parents[1] / "samples" / "sample_resume.docx"
        text = extract_text(path.name, path.read_bytes())
        education = parse_education(split_sections(text)["education"])
        self.assertEqual(len(education), 1)
        self.assertEqual(education[0].institution, "State University")
        self.assertEqual(education[0].degree, "B.S. in Computer Science")


if __name__ == "__main__":
    unittest.main()
