# -*- coding: utf-8 -*-
"""
run_all.py -- מריץ את כל שלבי ההכנה והבדיקה לפי הסדר הנכון, פקודה אחר פקודה.
מותאם למבנה הפרויקט הזה (config.py / --base-dir / --mock-llm וכו').

הרצה:
    python run_all.py
    python run_all.py --mock-llm   # לבדיקת מבנה בלבד, עם נתונים מזויפים
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config import Config


def run_step(title: str, cmd: list[str], stop_on_error: bool = True) -> bool:
    print("\n" + "=" * 70)
    print(f"שלב: {title}")
    print("פקודה: " + " ".join(cmd))
    print("=" * 70)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n!! השלב '{title}' נכשל (קוד יציאה {result.returncode}).")
        if stop_on_error:
            print("עוצרים כאן -- תקנו את השגיאה למעלה והריצו שוב את run_all.py")
            sys.exit(1)
        return False
    print(f"\n✓ השלב '{title}' הצליח.")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="הרצת כל שלבי ההכנה בפקודה אחת")
    ap.add_argument("--base-dir", default=".", type=Path)
    ap.add_argument("--mock-llm", action="store_true",
                     help="⚠️ בדיקת מבנה בלבד עם תשובות מזויפות - לא לקבצים אמיתיים")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    cfg = Config(base_dir=args.base_dir)

    print("מתחילים הרצה מלאה, שלב אחר שלב.")

    if not run_step("התקנת ספריות (pip install)",
                     [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                     stop_on_error=False):
        print("\nניסיון שני עם --break-system-packages (נפוץ בלינוקס/Ubuntu עדכני)...")
        run_step("התקנת ספריות (עם --break-system-packages)",
                  [sys.executable, "-m", "pip", "install", "--break-system-packages",
                   "-r", "requirements.txt"])

    run_step("בניית תיקיות וקבצי דוגמה (setup.py)", [sys.executable, "setup.py"])

    docx_files = list(cfg.inbox_dir.glob("*.docx")) if cfg.inbox_dir.exists() else []
    if not docx_files:
        print("\n" + "!" * 70)
        print(f"שימו לב: {cfg.inbox_dir}/ ריקה -- לא נמצאו קבצי docx.")
        print("העבירו לפחות קובץ Word אחד לבדיקה, ואז הריצו שוב.")
        print("!" * 70)
        sys.exit(1)

    print(f"\nנמצאו {len(docx_files)} קבצי docx ב-{cfg.inbox_dir}/:")
    for f in docx_files:
        print(f"  - {f.name}")

    if Path("diagnose_docx.py").exists():
        run_step(f"אבחון מבנה הקובץ ({docx_files[0].name})",
                  [sys.executable, "diagnose_docx.py", str(docx_files[0])],
                  stop_on_error=False)
    else:
        print("\n(דילוג: diagnose_docx.py לא נמצא -- לא קריטי)")

    dry_run_cmd = [sys.executable, "ingestion_pipeline.py", "--base-dir", str(args.base_dir), "--dry-run"]
    if args.mock_llm:
        dry_run_cmd.append("--mock-llm")
    if args.limit:
        dry_run_cmd += ["--limit", str(args.limit)]
    run_step("בדיקת dry-run (בלי Neo4j, בלי הזזת קבצים)", dry_run_cmd)

    print("\n" + "=" * 70)
    print(f"כל השלבים הסתיימו בהצלחה. בדקו את הדוחות ב-{cfg.output_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
