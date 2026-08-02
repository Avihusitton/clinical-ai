import os
import re
import json

py_files = []
for root, dirs, files in os.walk('.'):
    if '.git' in root or '__pycache__' in root or '.pytest_cache' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.normpath(os.path.join(root, f)))

refs = {}
pattern = re.compile(r'["\']([^"\']+\.(?:json|jsonl|csv|parquet|txt))["\']')
for pf in py_files:
    try:
        with open(pf, 'r', encoding='utf-8') as fp:
            content = fp.read()
        matches = pattern.findall(content)
        if matches:
            refs[pf] = matches
    except Exception as e:
        pass

print(json.dumps(refs, indent=2))
