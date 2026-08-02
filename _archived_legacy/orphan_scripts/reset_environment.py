import os
import shutil
from pathlib import Path
import re

archive_dir = Path("docs_archive")
inbox_dir = Path("docs_inbox")

if not inbox_dir.exists():
    inbox_dir.mkdir()

# regex to find "_processed_YYYY-MM-DD"
suffix_pattern = re.compile(r"(_processed_\d{4}-\d{2}-\d{2})+")

count = 0
for root, dirs, files in os.walk(archive_dir):
    for f in files:
        if f == ".gitkeep":
            continue
        
        # calculate relative path
        rel_path = Path(root).relative_to(archive_dir)
        source_path = Path(root) / f
        
        # calculate new name
        new_name = suffix_pattern.sub("", f)
        dest_dir = inbox_dir / rel_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / new_name
        
        try:
            shutil.move(str(source_path), str(dest_path))
            count += 1
        except Exception as e:
            print(f"Failed to move {source_path}: {e}")

# clean up empty directories in archive
for root, dirs, files in os.walk(archive_dir, topdown=False):
    for d in dirs:
        dir_path = Path(root) / d
        try:
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
        except:
            pass

print(f"Moved {count} files from archive to inbox.")
