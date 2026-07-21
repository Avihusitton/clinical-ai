# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from config import Config
from llm_client import LLMClient, LLMError
from ingestion_pipeline import DocxReader, PdfReader

import argparse

load_dotenv()
cfg = Config()

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=None, help="Limit number of files")
args = parser.parse_args()

archive = cfg.inbox_dir
out_path = cfg.output_dir / "glossary_draft.json"

files = sorted(
    (p for p in archive.rglob("*.*") if p.suffix.lower() in [".docx", ".pdf"] and p.stat().st_size > 0 and not p.name.lower().startswith("demo_")),
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

if args.limit:
    files = files[:args.limit]

if not files:
    raise SystemExit(f"לא נמצא קובץ נתמך ב-{archive}")

merged = {}
if out_path.exists():
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            if "concepts" in existing_data:
                merged = existing_data["concepts"]
    except Exception:
        pass


SYSTEM_EXERCISE = """אתה מחלץ דפי עבודה ותרגילים מתוך טקסט עבור מערכת ידע טיפולית-זוגית.

הטקסט שלפניך שייך לתיקיית דפי עבודה/תרגילים. חלץ את התרגילים והמשימות מתוכו באופן שלם והגיוני.
- כל תרגיל חייב לקבל שם קצר ומדויק.
- בשדה definition תאר את מהות התרגיל ומה עושים בו.
- חובה להגדיר את השדה type כ-"exercise".
- אין צורך להגדיר היררכיה (parent יכול להיות null).
- אם יש כותרות ברורות בתוך הקטע המפרידות בין תרגילים, פצל אותם לתרגילים נפרדים בתוך אותו JSON. אם לא, התייחס לקטע כתרגיל כולל.

החזר JSON תקין בלבד, ללא Markdown וללא הסבר, בפורמט המדויק:
{
  "concepts": {
    "שם תרגיל / משימה": {
      "parent": null,
      "synonyms": ["שם חלופי אם יש"],
      "definition": "תיאור קצר של התרגיל",
      "type": "exercise"
    }
  }
}
"""

SYSTEM_CONCEPT = """אתה בונה טיוטת גלוסר היררכית בעברית עבור מערכת ידע טיפולית-זוגית.

חלץ רק מונחים מקצועיים או מושגיים שמופיעים או נתמכים בבירור בטקסט. אל תחלץ שמות של אנשים, מידע מזהה או משפטים שלמים.
המבנה הוא שתי רמות בלבד:
- מושג ראשי: parent הוא null.
- מושג משנה: parent הוא שם מדויק של מושג ראשי שמופיע באותו JSON.
- הוסף את השדה "type": "concept" לכל המושגים.

החזר JSON תקין בלבד, בפורמט המדויק:
{
  "concepts": {
    "שם מושג": {
      "parent": null,
      "synonyms": ["ניסוח חלופי"],
      "definition": "הגדרה קצרה, מדויקת וניטרלית בעברית",
      "type": "concept"
    }
  }
}
"""

def parse_json(text: str):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("לא נמצא JSON בתשובת המודל")
    return json.loads(text[start:end + 1])

def call_model(part: str, number: int, doc_name: str, folder_name: str, is_exercise: bool):
    context_str = f"הקטע הבא נלקח ממסמך בשם '{doc_name}'"
    if folder_name:
        context_str += f" אשר נמצא בתיקייה '{folder_name}'"
    context_str += ". קח הקשר זה בחשבון בעת חילוץ המידע.\n\n"
    
    system_prompt = SYSTEM_EXERCISE if is_exercise else SYSTEM_CONCEPT
    payload = {
        "model": cfg.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context_str}קטע מסמך מספר {number}:\n\n{part}"},
        ],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {cfg.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return parse_json(content)
        except Exception as exc:
            last_error = exc
            print(f"קטע {number}: ניסיון {attempt}/3 נכשל: {exc}")

    raise RuntimeError(f"קטע {number} נכשל סופית: {last_error}")


llm = LLMClient(cfg.openrouter_api_key, cfg.llm_model, mock=False)

processed_files_path = cfg.output_dir / "processed_files.txt"
processed_files = set()
if processed_files_path.exists():
    with open(processed_files_path, "r", encoding="utf-8") as f:
        processed_files = set(line.strip() for line in f if line.strip())

total_project_chunks = 0
processed_project_chunks = 0
file_parts_cache = []

print("סורק את כל המסמכים כדי לחשב כמות קטעים (Chunks) בפרויקט. אנא המתן...")

for source in files:
    rel_path = source.relative_to(archive)
    folder_context = rel_path.parent.name if rel_path.parent != Path(".") else ""
    is_exercise = "תרגיל" in folder_context or "תרגילים" in folder_context

    if source.suffix.lower() == ".pdf":
        raw_paragraphs = PdfReader.read(source)
    else:
        raw_paragraphs, _ = DocxReader.read(source)

    if not raw_paragraphs:
        continue

    parts = []
    current = []
    current_len = 0
    MAX_CHARS = 7000

    for p in raw_paragraphs:
        text = p.get("text", "").strip()
        if not text:
            continue
        
        is_heading = p.get("is_heading_style", False) or p.get("is_heading", False)
        
        if is_heading and current_len > 1000:
            parts.append("\n\n".join(current))
            current = []
            current_len = 0
            
        current.append(text)
        current_len += len(text)
        
        if current_len > MAX_CHARS:
            parts.append("\n\n".join(current))
            current = []
            current_len = 0

    if current:
        parts.append("\n\n".join(current))
        
    total_project_chunks += len(parts)
    
    if source.name in processed_files:
        processed_project_chunks += len(parts)
    else:
        file_parts_cache.append((source, folder_context, is_exercise, parts))

print(f"סה\"כ קטעים בפרויקט: {total_project_chunks}. מתוכם עובדו: {processed_project_chunks}.")

for source, folder_context, is_exercise, parts in file_parts_cache:
    print(f"\n--- מתחיל לעבד קובץ: {source.name} ---")
    if folder_context:
        print(f"הקשר תיקייה: '{folder_context}' (תרגיל? {is_exercise})")

    total_doc_chunks = len(parts)
    print(f"חולק ל-{total_doc_chunks} קטעי תוכן.")

    for i, part in enumerate(parts, start=1):
        try:
            with open(cfg.output_dir / "pipeline_status.json", "r", encoding="utf-8") as sf:
                pstat = json.load(sf)
        except Exception:
            pstat = {"status": "שלב 1/2: קריאת כל המסמכים לחילוץ מושגים (Glossary Extraction)..."}
        
        pstat["current_file"] = source.name
        pstat["total_doc_chunks"] = total_doc_chunks
        pstat["current_chunk"] = i
        pstat["total_project_chunks"] = total_project_chunks
        pstat["processed_project_chunks"] = processed_project_chunks
        
        with open(cfg.output_dir / "pipeline_status.json", "w", encoding="utf-8") as sf:
            json.dump(pstat, sf, ensure_ascii=False)

        try:
            clean_part = llm.deidentify(part)
        except LLMError as exc:
            print(f"de-identification נכשל בקטע {i}: {exc} - מדלג")
            continue
        
        result = call_model(clean_part, i, source.stem, folder_context, is_exercise)
        processed_project_chunks += 1
        if not result:
            continue
        concepts = result.get("concepts", {})

        if not isinstance(concepts, dict):
            print(f"קטע {i}: תשובה לא תקינה — מדלג")
            continue

        for name, meta in concepts.items():
            name = str(name).strip()
            if not name or not isinstance(meta, dict):
                continue

            parent = meta.get("parent")
            parent = str(parent).strip() if parent else None
            
            c_type = meta.get("type", "exercise" if is_exercise else "concept")

            synonyms = meta.get("synonyms", [])
            if not isinstance(synonyms, list):
                synonyms = []

            clean_synonyms = sorted({
                str(item).strip()
                for item in synonyms
                if str(item).strip() and str(item).strip() != name
            })

            definition = str(meta.get("definition", "")).strip()

            if name not in merged:
                merged[name] = {
                    "parent": parent,
                    "synonyms": clean_synonyms,
                    "definition": definition,
                    "type": c_type
                }
            else:
                merged[name]["synonyms"] = sorted(
                    set(merged[name]["synonyms"]) | set(clean_synonyms)
                )
                if not merged[name]["definition"] and definition:
                    merged[name]["definition"] = definition
                if merged[name]["parent"] is None and parent:
                    merged[name]["parent"] = parent

        print(f"חילוץ: קטע {i}/{len(parts)} | סהכ {len(merged)} אובייקטים במצטבר")

    # Save progress after every document
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source_document": "Multiple Files",
                "status": "draft_requires_human_approval",
                "concepts": dict(sorted(merged.items())),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    
    with open(processed_files_path, "a", encoding="utf-8") as pf:
        pf.write(source.name + "\n")
        
    print(f"טיוטה עודכנה ונשמרה עבור {source.name}")

# Final validation
for name, meta in merged.items():
    if meta["parent"] and meta["parent"] not in merged:
        print(f"אזהרה: ההורה '{meta['parent']}' של '{name}' חסר — הוגדר כראשי")
        meta["parent"] = None

primary = sum(1 for meta in merged.values() if meta["parent"] is None)
secondary = len(merged) - primary

out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "source_document": "All Processed Files",
            "status": "draft_requires_human_approval",
            "concepts": dict(sorted(merged.items())),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

print()
print(f"נשמרה טיוטה סופית: {out_path}")
print(f"סהכ מחולצים: {len(merged)}")
print("לא בוצע שינוי ב-data/glossary.json ולא בוצעה טעינה ל-Neo4j.")
