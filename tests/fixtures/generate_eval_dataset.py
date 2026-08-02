import json
import os

categories = {
    "LONGEST_MATCH": 25,
    "WORD_BOUNDARY": 25,
    "NIQQUD": 20,
    "PUNCTUATION": 20,
    "MIXED_RTL_LTR": 20,
    "OVERLAPPING_TERMS": 20,
    "UNSAFE_SHORT_ALIAS": 20,
    "NEGATIVE_FALSE_POSITIVE": 20,
    "ALIAS_COLLISION": 10
}

entries = []
case_id_counter = 1

def generate_record(category, text, expected_matches):
    global case_id_counter
    expected_card_ids = list(set([m["card_id"] for m in expected_matches]))
    record = {
        "case_id": f"HB-{case_id_counter:04d}",
        "text": text,
        "expected_card_ids": expected_card_ids,
        "expected_spans": expected_matches,
        "expected_non_matches": [],
        "category": category
    }
    case_id_counter += 1
    entries.append(record)

# Generate mock data
for i in range(categories["LONGEST_MATCH"]):
    # Matcher should prefer the longer string
    generate_record("LONGEST_MATCH", f"טיפול קוגניטיבי התנהגותי מקיף {i}", [{"card_id": "Z903", "start": 0, "end": 25, "matched_text": "טיפול קוגניטיבי התנהגותי"}])

for i in range(categories["WORD_BOUNDARY"]):
    generate_record("WORD_BOUNDARY", f"המטופל חווה פחד נטישה פתאומי {i}", [{"card_id": "Z901", "start": 12, "end": 21, "matched_text": "פחד נטישה"}])

for i in range(categories["NIQQUD"]):
    generate_record("NIQQUD", f"פַּחַד נְטִישָׁה {i}", [{"card_id": "Z901", "start": 0, "end": 15, "matched_text": "פַּחַד נְטִישָׁה"}])

for i in range(categories["PUNCTUATION"]):
    generate_record("PUNCTUATION", f"פחד-נטישה! {i}", [{"card_id": "Z901", "start": 0, "end": 9, "matched_text": "פחד-נטישה"}])

for i in range(categories["MIXED_RTL_LTR"]):
    generate_record("MIXED_RTL_LTR", f"טיפול CBT ממוקד {i}", [{"card_id": "Z904", "start": 6, "end": 9, "matched_text": "CBT"}])

for i in range(categories["OVERLAPPING_TERMS"]):
    # Assuming Z901 is פחד נטישה and Z905 is נטישה
    generate_record("OVERLAPPING_TERMS", f"פחד נטישה מתמשך {i}", [{"card_id": "Z901", "start": 0, "end": 9, "matched_text": "פחד נטישה"}])

for i in range(categories["UNSAFE_SHORT_ALIAS"]):
    # e.g., abbreviation that shouldn't match generically
    generate_record("UNSAFE_SHORT_ALIAS", f"דם {i}", []) # Expected non-match

for i in range(categories["NEGATIVE_FALSE_POSITIVE"]):
    generate_record("NEGATIVE_FALSE_POSITIVE", f"בפחדנטישהשלי {i}", [])

for i in range(categories["ALIAS_COLLISION"]):
    # Different concepts sharing an alias (e.g. "הזדהות" for Z902 and Z906)
    generate_record("ALIAS_COLLISION", f"הזדהות עמוקה {i}", [
        {"card_id": "Z902", "start": 0, "end": 6, "matched_text": "הזדהות"},
        {"card_id": "Z906", "start": 0, "end": 6, "matched_text": "הזדהות"}
    ])

os.makedirs("tests/fixtures", exist_ok=True)
with open("tests/fixtures/hebrew_alias_evaluation.jsonl", "w", encoding="utf-8") as f:
    for e in entries:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

print(f"Generated {len(entries)} items")
