import os
import time
import sys

inbox_dir = r"c:\Avihusitton\clinical_ai\docs_inbox"
archive_dir = r"c:\Avihusitton\clinical_ai\docs_archive"
error_dir = r"c:\Avihusitton\clinical_ai\docs_error"

def count_files(directory):
    if not os.path.exists(directory):
        return 0
    return len([f for f in os.listdir(directory) if f != ".gitkeep"])

print("========================================")
print("מעקב התקדמות - צינור הזרקת הנתונים")
print("========================================")

initial_archive = count_files(archive_dir)
initial_error = count_files(error_dir)

try:
    while True:
        inbox_count = count_files(inbox_dir)
        archive_count = count_files(archive_dir) - initial_archive
        error_count = count_files(error_dir) - initial_error
        
        sys.stdout.write(f"\r[סטטוס] נותרו באינבוקס: {inbox_count} | עובדו בהצלחה: {archive_count} | שגיאות: {error_count}  ")
        sys.stdout.flush()
        
        if inbox_count == 0:
            print("\n\nהתהליך הסתיים! כל הקבצים יצאו מהאינבוקס.")
            break
            
        time.sleep(2)
except KeyboardInterrupt:
    print("\nהמעקב הופסק.")
