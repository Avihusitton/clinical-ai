#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
document_types_inspector.py -- בודק את data/document_types.json ומאתר
קטגוריות תוכן שדומות מדי זו לזו ומומלץ לאחד אותן ידנית.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from rapidfuzz import fuzz
except ImportError:
    import sys
    sys.exit("חסרה תלות: pip install rapidfuzz")

DEFAULT_THRESHOLD = 65


def load_registry(path: Path) -> dict:
    if not path.exists():
        print(f"לא נמצא קובץ: {path}")
        raise SystemExit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("categories", {})


def save_registry(path: Path, categories: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"categories": categories}, f, ensure_ascii=False, indent=2)


def find_similar_pairs(categories: dict, threshold: int):
    names = list(categories.keys())
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            score = fuzz.ratio(a, b)
            aliases_a = categories[a].get("aliases", [a])
            aliases_b = categories[b].get("aliases", [b])
            cross_score = max(
                (fuzz.ratio(x, y) for x in aliases_a for y in aliases_b), default=0
            )
            best = max(score, cross_score)
            if best >= threshold:
                pairs.append((a, b, best))
    return sorted(pairs, key=lambda p: -p[2])


def print_report(categories: dict, threshold: int) -> None:
    print("=" * 70)
    print("סה\"כ קטגוריות תוכן שהתגלו עד כה: " + str(len(categories)))
    print("=" * 70)
    for name, meta in sorted(categories.items(), key=lambda kv: -kv[1].get("confidence_weight", 1.0)):
        weight = meta.get("confidence_weight", 1.0)
        aliases = meta.get("aliases", [])
        alias_preview = ", ".join(a for a in aliases if a != name) or "-"
        print("  * " + name + "  (משקל אמינות: " + str(weight) + ")")
        print("      כינויים שנקלטו: " + alias_preview)
    print()

    similar = find_similar_pairs(categories, threshold)
    if not similar:
        print("לא נמצאו קטגוריות דומות מעל סף " + str(threshold) + " - נראה נקי.")
        return

    print("נמצאו " + str(len(similar)) + " זוגות קטגוריות דומות (סף בדיקה: " + str(threshold) + "):")
    print("-" * 70)
    for a, b, score in similar:
        print("  '" + a + "'  <->  '" + b + "'   (דמיון: " + str(score) + ")")
        print("      מומלץ לבדוק אם צריך לאחד. לאיחוד הריצו:")
        print('      python document_types_inspector.py --merge "' + a + '" "' + b + '"')
        print()


def merge_categories(categories: dict, source: str, target: str) -> dict:
    if source not in categories:
        print("קטגוריה '" + source + "' לא נמצאה.")
        raise SystemExit(1)
    if target not in categories:
        print("קטגוריה '" + target + "' לא נמצאה.")
        raise SystemExit(1)
    if source == target:
        print("לא ניתן לאחד קטגוריה עם עצמה.")
        raise SystemExit(1)

    src_meta = categories.pop(source)
    tgt_meta = categories[target]

    merged_aliases = list(dict.fromkeys(
        tgt_meta.get("aliases", [target]) + src_meta.get("aliases", [source]) + [source]
    ))
    tgt_meta["aliases"] = merged_aliases

    src_n = len(src_meta.get("aliases", [source]))
    tgt_n = len(tgt_meta.get("aliases", [target])) - src_n
    src_w = src_meta.get("confidence_weight", 1.0)
    tgt_w = tgt_meta.get("confidence_weight", 1.0)
    if src_n + tgt_n > 0:
        tgt_meta["confidence_weight"] = round(
            (src_w * src_n + tgt_w * max(tgt_n, 1)) / (src_n + max(tgt_n, 1)), 3
        )

    print("'" + source + "' אוחד לתוך '" + target + "'.")
    print("   משקל אמינות סופי: " + str(tgt_meta["confidence_weight"]))
    print("   כינויים מאוחדים: " + ", ".join(merged_aliases))
    return categories


def main() -> None:
    ap = argparse.ArgumentParser(description="בדיקת קטגוריות תוכן דומות")
    ap.add_argument("--base-dir", default=".", type=Path)
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    ap.add_argument("--merge", nargs=2, metavar=("SOURCE", "TARGET"))
    args = ap.parse_args()

    path = args.base_dir / "data" / "document_types.json"
    categories = load_registry(path)

    if args.merge:
        source, target = args.merge
        categories = merge_categories(categories, source, target)
        save_registry(path, categories)
        print("נשמר: " + str(path))
        return

    print_report(categories, args.threshold)


if __name__ == "__main__":
    main()