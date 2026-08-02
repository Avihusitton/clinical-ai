import os
import time
import subprocess

inbox = r"c:\Avihusitton\clinical_ai\docs_inbox"
print("Waiting for files in docs_inbox...")
while True:
    files = [f for f in os.listdir(inbox) if f != ".gitkeep"]
    has_pdf = any(f.endswith('.pdf') for f in files)
    has_doc = any(f.endswith('.doc') or f.endswith('.docx') for f in files)
    
    # We proceed if there's at least one file, but ideally we want both as the user mentioned
    if len(files) > 0:
        print(f"Found files: {files}")
        break
    time.sleep(5)
print("Files detected. Ready for pipeline.")
