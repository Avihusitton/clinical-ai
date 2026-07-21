# -*- coding: utf-8 -*-
"""
מוסיף תמיכה בקריאת PDF לצינור, בנוסף ל-Word הקיים.
יוצר גיבוי לפני שינוי (ingestion_pipeline.before_pdf_support.py).

הרצה: python add_pdf_support.py
"""
from pathlib import Path

path = Path("ingestion_pipeline.py")
original = path.read_text(encoding="utf-8")

anchor_class = (
    '    @staticmethod\n'
    '    def content_hash(paragraphs: list[dict]) -> str:\n'
    '        joined = "".join(p["text"] for p in paragraphs)\n'
    '        normalized = re.sub(r"\\s+", "", joined)\n'
    '        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()'
)

pdf_reader_class = '''

class PdfReader:
    """
    קורא PDF ומחזיר רשימת פסקאות בפורמט תואם ל-DocxReader.read():
    [{"text": str, "is_heading": bool, "is_bold": bool}, ...]
    ב-PDF אין סטייל כותרת מובנה, אז הזיהוי מבוסס על גודל גופן יחסי
    לגודל החציוני של המסמך.
    """

    HEADING_SIZE_RATIO = 1.15

    @staticmethod
    def read(path: Path) -> list[dict]:
        import pdfplumber

        lines: list[dict] = []
        sizes: list[float] = []

        with pdfplumber.open(str(path)) as pdf:
            page_lines = []
            for page in pdf.pages:
                words = page.extract_words(extra_attrs=["size", "fontname"], use_text_flow=False)
                if not words:
                    continue
                current_line, current_top = [], None
                for w in words:
                    if current_top is None or abs(w["top"] - current_top) < 3:
                        current_line.append(w)
                        current_top = w["top"] if current_top is None else current_top
                    else:
                        page_lines.append(current_line)
                        current_line, current_top = [w], w["top"]
                if current_line:
                    page_lines.append(current_line)

            for line_words in page_lines:
                text = " ".join(w["text"] for w in line_words).strip()
                if not text:
                    continue
                avg_size = sum(w["size"] for w in line_words) / len(line_words)
                is_bold = any("bold" in w.get("fontname", "").lower() for w in line_words)
                sizes.append(avg_size)
                lines.append({"text": text, "_size": avg_size, "is_bold": is_bold})

        if not sizes:
            return []

        sizes_sorted = sorted(sizes)
        median_size = sizes_sorted[len(sizes_sorted) // 2]

        paragraphs = []
        for ln in lines:
            is_heading = ln["_size"] >= median_size * PdfReader.HEADING_SIZE_RATIO
            paragraphs.append({"text": ln["text"], "is_heading": is_heading, "is_bold": ln["is_bold"]})
        return paragraphs'''

anchor_glob = 'files = sorted(self.cfg.inbox_dir.glob("*.docx"))'
new_glob = (
    'files = sorted(self.cfg.inbox_dir.glob("*.docx")) + '
    'sorted(self.cfg.inbox_dir.glob("*.pdf"))\n        files = sorted(files)'
)

anchor_read_call = '''        try:
            paragraphs = DocxReader.read(path)
        except Exception as exc:'''
new_read_call = '''        try:
            if path.suffix.lower() == ".pdf":
                paragraphs = PdfReader.read(path)
            else:
                paragraphs = DocxReader.read(path)
        except Exception as exc:'''

replacements = [
    ("הוספת מחלקת PdfReader", anchor_class, anchor_class + pdf_reader_class),
    ("עדכון glob לזיהוי PDF", anchor_glob, new_glob),
    ("בחירת reader לפי סיומת", anchor_read_call, new_read_call),
]

missing = [label for label, old, _ in replacements if old not in original]
if missing:
    raise SystemExit(f"לא נמצאו הקטעים הבאים בקובץ, לא בוצע שום שינוי: {missing}")

backup = Path("ingestion_pipeline.before_pdf_support.py")
if not backup.exists():
    backup.write_text(original, encoding="utf-8")

for label, old, new in replacements:
    original = original.replace(old, new, 1)

path.write_text(original, encoding="utf-8")
print(f"גיבוי קוד: {backup}")
print("תמיכה ב-PDF נוספה בהצלחה. ודאו: pip install pdfplumber")