import os
import json
import hashlib
import time
import re

def analyze_all():
    # 1. Find all project python files and their string references to relative or absolute paths
    py_files = []
    for root, dirs, files in os.walk('.'):
        if any(x in root for x in ['.git', '__pycache__', '.pytest_cache']):
            continue
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.normpath(os.path.join(root, f)))

    code_contents = {}
    for pf in py_files:
        try:
            with open(pf, 'r', encoding='utf-8') as fp:
                code_contents[pf] = fp.read()
        except Exception:
            pass

    # 2. Gather candidates
    candidates_list = []
    for root, dirs, files in os.walk('.'):
        if any(x in root for x in ['.git', '__pycache__', '.pytest_cache', '_archive', 'scratch']):
            continue
        for f in files:
            fl = f.lower()
            if any(k in fl for k in ['glossary', 'dictionary', 'concept', 'lexicon']):
                p = os.path.normpath(os.path.join(root, f))
                candidates_list.append(p)

    candidates_list = sorted(list(set(candidates_list)))
    
    results = []
    for cpath in candidates_list:
        if not os.path.exists(cpath):
            continue
        st = os.stat(cpath)
        with open(cpath, 'rb') as fp:
            raw = fp.read()
        sha = hashlib.sha256(raw).hexdigest()
        
        # Check references in python code
        norm_cpath = cpath.replace('\\', '/')
        cbasename = os.path.basename(cpath)
        refs = []
        for pf, content in code_contents.items():
            pf_norm = pf.replace('\\', '/')
            if norm_cpath in content or cpath in content or (cbasename in content and ('glossary' in cbasename or 'concept' in cbasename)):
                # Verify if it's actually referencing this path or file
                if cbasename in content:
                    refs.append(pf_norm)

        # Parse format, record_count, schema
        fmt = os.path.splitext(cpath)[1].lstrip('.').lower()
        if not fmt:
            fmt = "unknown"
        
        record_count = 0
        schema_keys = []
        parsed = None
        
        if fmt == 'json':
            try:
                parsed = json.loads(raw.decode('utf-8'))
                if isinstance(parsed, list):
                    record_count = len(parsed)
                    if record_count > 0 and isinstance(parsed[0], dict):
                        schema_keys = sorted(list(parsed[0].keys()))
                elif isinstance(parsed, dict):
                    if 'concepts' in parsed and isinstance(parsed['concepts'], dict):
                        record_count = len(parsed['concepts'])
                        # peek into concepts
                        first_val = next(iter(parsed['concepts'].values()))
                        if isinstance(first_val, dict):
                            schema_keys = ['dict_key: concept_id', 'concepts_value_schema: ' + str(sorted(list(first_val.keys())))]
                    else:
                        record_count = len(parsed)
                        schema_keys = sorted(list(parsed.keys()))
            except Exception as e:
                schema_keys = [f"Error: {e}"]
        elif fmt == 'jsonl':
            try:
                lines = [l for l in raw.decode('utf-8').splitlines() if l.strip()]
                record_count = len(lines)
                if record_count > 0:
                    first = json.loads(lines[0])
                    if isinstance(first, dict):
                        schema_keys = sorted(list(first.keys()))
            except Exception as e:
                schema_keys = [f"Error: {e}"]
        elif fmt == 'py':
            fmt = "python_code"
            record_count = 0
            schema_keys = ["python_script"]

        mtime = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(st.st_mtime))
        
        # Determine likely role
        role = "unknown"
        if fmt == "python_code":
            role = "code_script"
        elif "backups" in cpath:
            role = "historical_backup"
        elif "official_glossary.sample.jsonl" in cpath or "sample" in cpath or "SAMPLES" in cpath:
            role = "sample_test_fixture"
        elif "tests" in cpath or "preflight_run" in cpath or "fixtures" in cpath:
            role = "test_fixture"
        elif "data/glossary.json" in cpath.replace('\\', '/'):
            role = "concept_dictionary_or_official_glossary_candidate"
        elif "data/official_glossary/glossary.json" in cpath.replace('\\', '/'):
            role = "official_glossary_candidate"
        elif "out/glossary_draft" in cpath.replace('\\', '/'):
            role = "pipeline_draft_output"
        elif "data/concept_relationships_queue.json" in cpath.replace('\\', '/'):
            role = "relationship_queue"

        results.append({
            "path": cpath.replace('\\', '/'),
            "format": fmt,
            "byte_length": len(raw),
            "sha256": sha,
            "record_count": record_count,
            "schema": schema_keys,
            "modified_time": mtime,
            "references_from_project_code": refs,
            "likely_role": role
        })

    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    analyze_all()
