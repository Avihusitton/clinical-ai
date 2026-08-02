import shutil
from pathlib import Path

source = Path(r"C:\Users\avihu\Downloads\קהילת מטפלים 4 - חסכים.docx")

sandbox = Path("preflight_run")
data_src = Path("data")
data_dst = sandbox / "data"
inbox = sandbox / "docs_inbox"

if not source.is_file():
    raise SystemExit(f"לא נמצא קובץ מקור: {source}")

if sandbox.exists():
    shutil.rmtree(sandbox)

inbox.mkdir(parents=True)
data_dst.mkdir(parents=True)

for name in ("glossary.json", "exercises.json", "relationship_types.json"):
    src = data_src / name
    if src.exists():
        shutil.copy2(src, data_dst / name)

shutil.copy2(source, inbox / source.name)

print(f"עותק לבדיקה: {inbox / source.name}")
print(f"סביבת ניסיון: {sandbox}")
print("המסמך המקורי לא שונה.")
