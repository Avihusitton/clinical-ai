import os
import json
import hashlib
import time

candidate_files = [
    "data/glossary.json",
    "data/official_glossary/official_glossary.sample.jsonl",
    "data/official_glossary/schema.json",
    "data/official_glossary/alias_exceptions.json",
    "data/official_glossary/entry_types.json",
    "data/backups/20260710_183528/glossary.json",
    "data/backups/20260710_185842/glossary.json",
    "data/backups/20260723_144633/glossary.json",
    "data/backups/20260723_144646/glossary.json",
    "out/glossary_clean_draft.json",
    "out/glossary_draft.json",
    "out/glossary_excluded_for_review.json",
    "preflight_run/data/glossary.json",
    "handoff_dictionary_integration/SAMPLES.jsonl",
    "tests/shadow_pilot_fixture.jsonl"
]

print("=== CANDIDATE SUMMARY ===")
for p in candidate_files:
    if os.path.exists(p):
        st = os.stat(p)
        raw = open(p, 'rb').read()
        sha = hashlib.sha256(raw).hexdigest()
        print(f"Path: {p}")
        print(f"  Byte length: {len(raw)}")
        print(f"  SHA256: {sha}")
        print(f"  Modified: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime))}")
        
        # sample view
        if p.endswith('.json'):
            try:
                data = json.loads(raw.decode('utf-8'))
                if isinstance(data, dict):
                    print(f"  Type: Dict, Keys: {list(data.keys())[:5]}")
                    if 'concepts' in data:
                        print(f"  Concepts count: {len(data['concepts'])}")
                        first_k = next(iter(data['concepts']))
                        print(f"  Sample concept ({first_k}): {data['concepts'][first_k]}")
                    elif '_readme' in data or 'concepts' in data:
                        pass
                    else:
                        print(f"  Dict length: {len(data)}")
                elif isinstance(data, list):
                    print(f"  Type: List, Len: {len(data)}")
                    if len(data) > 0:
                        print(f"  Sample element 0: {data[0]}")
            except Exception as e:
                print(f"  JSON Error: {e}")
        elif p.endswith('.jsonl'):
            lines = [l for l in raw.decode('utf-8').splitlines() if l.strip()]
            print(f"  Type: JSONL, Lines: {len(lines)}")
            if len(lines) > 0:
                print(f"  Sample line 0: {lines[0][:200]}")
        print("-" * 50)
