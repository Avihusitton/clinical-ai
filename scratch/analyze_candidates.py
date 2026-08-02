import os
import json
import hashlib
import time

def analyze_candidates():
    # Candidates to investigate
    candidate_paths = [
        "data/glossary.json",
        "data/official_glossary/official_glossary.sample.jsonl",
        "data/official_glossary/glossary.json",
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
        "preflight_run/out/concept_relationships.json",
    ]
    
    # Also scan any other json/jsonl in repo for concepts/glossary
    all_files = []
    for root, dirs, files in os.walk('.'):
        if any(x in root for x in ['.git', '__pycache__', '.pytest_cache', '_archive', 'scratch']):
            continue
        for f in files:
            if f.endswith('.json') or f.endswith('.jsonl'):
                p = os.path.normpath(os.path.join(root, f))
                all_files.append(p)

    results = []
    for p in sorted(list(set(candidate_paths + all_files))):
        if not os.path.exists(p):
            continue
        st = os.stat(p)
        with open(p, 'rb') as fp:
            content = fp.read()
        sha256 = hashlib.sha256(content).hexdigest()
        
        # Analyze structure
        fmt = "jsonl" if p.endswith('.jsonl') else "json"
        rec_count = 0
        schema = []
        sample_keys = []
        try:
            if fmt == "jsonl":
                lines = content.decode('utf-8').strip().split('\n')
                rec_count = len([l for l in lines if l.strip()])
                if rec_count > 0:
                    first = json.loads(lines[0])
                    if isinstance(first, dict):
                        sample_keys = sorted(list(first.keys()))
            else:
                data = json.loads(content.decode('utf-8'))
                if isinstance(data, list):
                    rec_count = len(data)
                    if rec_count > 0 and isinstance(data[0], dict):
                        sample_keys = sorted(list(data[0].keys()))
                elif isinstance(data, dict):
                    rec_count = len(data)
                    sample_keys = sorted(list(data.keys()))[:10]
        except Exception as e:
            sample_keys = [f"Error parsing: {e}"]

        results.append({
            "path": p,
            "format": fmt,
            "byte_length": len(content),
            "sha256": sha256,
            "record_count": rec_count,
            "sample_keys": sample_keys,
            "modified_time": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime))
        })
        
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    analyze_candidates()
