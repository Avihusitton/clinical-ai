import sys
import argparse
import subprocess
import json
from pathlib import Path
import traceback

def update_status(status_text: str):
    status_file = Path("out/pipeline_status.json")
    status_file.parent.mkdir(exist_ok=True)
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({"status": status_text}, f, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    try:
        # 1. Glossary Extraction
        update_status("שלב 1/2: קריאת כל המסמכים לחילוץ מושגים (Glossary Extraction)...")
        cmd_glossary = [sys.executable, "build_glossary.py"]
        if args.limit:
            cmd_glossary.extend(["--limit", str(args.limit)])
        
        print(f"Running: {' '.join(cmd_glossary)}")
        subprocess.run(cmd_glossary, check=True)
        
        # 2. Ingestion Pipeline
        update_status("שלב 2/2: הזרקת מסמכים, קישור מושגים ועדכון Neo4j...")
        cmd_ingestion = [sys.executable, "ingestion_pipeline.py"]
        if args.limit:
            cmd_ingestion.extend(["--limit", str(args.limit)])
        
        print(f"Running: {' '.join(cmd_ingestion)}")
        subprocess.run(cmd_ingestion, check=True)
        
        update_status("תהליך הסתיים בהצלחה!")
    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed with error code {e.returncode}")
        update_status(f"נכשל: תהליך משנה קרס. (קוד שגיאה {e.returncode})")
    except Exception as e:
        print("Pipeline failed:")
        traceback.print_exc()
        update_status(f"נכשל: שגיאה פנימית בצינור - {str(e)}")

if __name__ == "__main__":
    main()
