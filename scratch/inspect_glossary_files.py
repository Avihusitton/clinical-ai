import os
import json
import hashlib
import time

def inspect():
    files_to_check = [
        "data/glossary.json",
        "data/official_glossary/glossary.json",
        "data/official_glossary/official_glossary.sample.jsonl",
        "data/backups/20260710_183528/glossary.json",
        "data/backups/20260710_185842/glossary.json",
        "data/backups/20260723_144633/glossary.json",
        "data/backups/20260723_144646/glossary.json",
        "out/glossary_clean_draft.json",
        "out/glossary_draft.json",
        "out/glossary_excluded_for_review.json",
        "preflight_run/data/glossary.json",
        "handoff_dictionary_integration/SAMPLES.jsonl",
        "data/concept_relationships_queue.json",
        "out/concept_relationships.json",
        "preflight_run/out/concept_relationships.json"
    ]
    
    # Also find any other file in data/ or out/
    for root, dirs, files in os.walk('data'):
        for f in files:
            p = os.path.normpath(os.path.join(root, f))
            if p not in files_to_check:
                files_to_check.append(p)
    for root, dirs, files in os.walk('out'):
        for f in files:
            p = os.path.normpath(os.path.join(root, f))
            if p not in files_to_check:
                files_to_check.append(p)

    out = []
    for p in files_to_check:
        if not os.path.exists(p):
            continue
        st = os.stat(p)
        with open(p, 'rb') as fp:
            data = fp.read()
        sha256 = hashlib.sha256(data).hexdigest()
        
        # Check record count and schema
        rec_count = 0
        schema = []
        sample = None
        if p.endswith('.json'):
            try:
                obj = json.loads(data.decode('utf-8'))
                if isinstance(obj, list):
                    rec_count = len(obj)
                    if rec_count > 0:
                        schema = sorted(list(obj[0].keys())) if isinstance(obj[0], dict) else [type(obj[0]).__name__]
                        sample = obj[0]
                elif isinstance(obj, dict):
                    rec_count = len(obj)
                    schema = sorted(list(obj.keys()))
                    sample = {k: type(v).__name__ for k, v in list(obj.items())[:3]}
            except Exception as e:
                schema = [f"JSON Parse Error: {e}"]
        elif p.endswith('.jsonl'):
            try:
                lines = [l for l in data.decode('utf-8').strip().split('\n') if l.strip()]
                rec_count = len(lines)
                if rec_count > 0:
                    first = json.loads(lines[0])
                    schema = sorted(list(first.keys())) if isinstance(first, dict) else [type(first).__name__]
                    sample = first
            except Exception as e:
                schema = [f"JSONL Parse Error: {e}"]
        else:
            rec_count = 1
            schema = ["raw"]

        out.append({
            "path": p,
            "byte_length": len(data),
            "sha256": sha256,
            "record_count": rec_count,
            "schema": schema,
            "modified_time": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime)),
            "sample_snippet": str(sample)[:300] if sample else None
        })

    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    inspect()
