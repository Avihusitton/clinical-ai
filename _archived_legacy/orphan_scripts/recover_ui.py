import json
import re

log_file = r'C:\Users\avihu\.gemini\antigravity\brain\dbd07d4d-a307-4489-bd27-d08e440333b4\.system_generated\logs\transcript_full.jsonl'
lines_map = {}

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            # Find strings that contain our marker
            # Instead of guessing the JSON structure, let's just dump the JSON object to a string
            # and search it!
            data_str = json.dumps(data)
            if 'Showing lines' in data_str and 'clinical_workspace_ui.py' in data_str:
                # We need to extract the actual text blocks.
                # Let's search the Python dictionary recursively to find all string values.
                def extract_strings(obj):
                    res = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            res.extend(extract_strings(v))
                    elif isinstance(obj, list):
                        for item in obj:
                            res.extend(extract_strings(item))
                    elif isinstance(obj, str):
                        res.append(obj)
                    return res
                
                for s in extract_strings(data):
                    if 'Showing lines' in s and 'clinical_workspace_ui.py' in s:
                        # Extract the lines
                        # Format is typically:
                        # Showing lines 1 to 149 of /path/to/clinical_workspace_ui.py:
                        # 1: <html>
                        # 2: <body>
                        matches = re.findall(r'^(\d+):\s(.*)$', s, re.MULTILINE)
                        for num, text in matches:
                            lines_map[int(num)] = text
        except json.JSONDecodeError:
            pass

print(f'Recovered {len(lines_map)} lines!')
with open('C:/Avihusitton/clinical_ai/recovered_lines.py', 'w', encoding='utf-8') as out:
    for i in sorted(lines_map.keys()):
        out.write(lines_map[i] + '\n')
