import os
import time
import subprocess
import sys
from pathlib import Path

inbox = Path(r"c:\Avihusitton\clinical_ai\docs_inbox")
pipeline_script = Path(r"c:\Avihusitton\clinical_ai\ingestion_pipeline.py")

print("==================================================")
print("Auto-Ingest loop started!")
print("Listening to docs_inbox folder...")
print("==================================================")

try:
    while True:
        # Check recursively if there are files (ignoring .gitkeep)
        files = [f for f in inbox.rglob("*") if f.is_file() and f.name != ".gitkeep"]
        
        if len(files) > 0:
            print(f"\n[!] Detected {len(files)} new files! Starting pipeline...")
            
            # Run the ingestion pipeline
            result = subprocess.run([sys.executable, str(pipeline_script)])
            
            if result.returncode == 0:
                print("\n[v] Pipeline finished successfully. Resuming listening...\n")
            else:
                print(f"\n[x] Pipeline failed (Code {result.returncode}). Resuming listening...\n")
                
        time.sleep(5)  # Wait 5 seconds before checking again
except KeyboardInterrupt:
    print("\nAuto-Ingest stopped.")
