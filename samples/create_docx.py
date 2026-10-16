"""Create a sample uploadable DOCX from the readable sample resume text."""

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
target = root / "sample_resume.docx"
lines = (root / "sample_resume.txt").read_text(encoding="utf-8").splitlines()
paragraphs = "".join(f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in lines)
document = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    f"<w:body>{paragraphs}<w:sectPr/></w:body></w:document>"
)
with ZipFile(target, "w", ZIP_DEFLATED) as docx:
    docx.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?>'
                  '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="xml" ContentType="application/xml"/>'
                  '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                  '</Types>')
    docx.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?>'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                  '</Relationships>')
    docx.writestr("word/document.xml", document)
print(target)
