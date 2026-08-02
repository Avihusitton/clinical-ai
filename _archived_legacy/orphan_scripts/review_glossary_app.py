# -*- coding: utf-8 -*-
import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="אישור מושגים למילון", layout="centered", page_icon="📖")

BASE_DIR = Path(__file__).parent
DRAFT_PATH = BASE_DIR / "out" / "glossary_draft.json"
GLOSSARY_PATH = BASE_DIR / "data" / "glossary.json"

def load_json(path):
    if not path.exists():
        st.error(f"File not found: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            st.error(f"Error reading JSON from {path}: {e}")
            return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

st.title("📖 אישור מילון מושגים")

draft_data = load_json(DRAFT_PATH)
glossary_data = load_json(GLOSSARY_PATH)

if "concepts" not in draft_data or not draft_data["concepts"]:
    st.success("אין מושגים ממתינים לאישור בטיוטה!")
    st.stop()

draft_concepts = draft_data["concepts"]
total_pending = len(draft_concepts)
st.caption(f"ממתינים לאישור: {total_pending} מושגים")

# Get first concept
concept_name = list(draft_concepts.keys())[0]
concept_meta = draft_concepts[concept_name]

st.markdown("---")
st.subheader(f"מושג לבדיקה: **{concept_name}**")
st.markdown(f"**הגדרה:** {concept_meta.get('definition', '')}")

synonyms = concept_meta.get('synonyms', [])
if synonyms:
    st.markdown(f"**מילים נרדפות:** {', '.join(synonyms)}")

st.markdown("---")

# existing concepts to choose as parent
existing_concepts = glossary_data.get("concepts", {})
primary_choices = ["🌟 מושג יסוד (ראשי)"] + [f"↳ מושג משנה תחת: {k}" for k, v in existing_concepts.items() if not v.get("parent")]

selected_parent_str = st.selectbox("הגדר את סוג המושג (יסוד או משנה):", primary_choices)

col1, col2 = st.columns(2)

if col1.button("✅ אשר והכנס למילון", use_container_width=True, type="primary"):
    if selected_parent_str == "🌟 מושג יסוד (ראשי)":
        parent_val = None
    else:
        parent_val = selected_parent_str.replace("↳ מושג משנה תחת: ", "")
    
    if "concepts" not in glossary_data:
        glossary_data["concepts"] = {}
        
    glossary_data["concepts"][concept_name] = {
        "definition": concept_meta.get("definition", ""),
        "synonyms": synonyms,
        "parent": parent_val
    }
    
    del draft_concepts[concept_name]
    save_json(GLOSSARY_PATH, glossary_data)
    save_json(DRAFT_PATH, draft_data)
    st.rerun()

if col2.button("❌ לא מושג מיוחד (דחה)", use_container_width=True):
    del draft_concepts[concept_name]
    save_json(DRAFT_PATH, draft_data)
    st.rerun()
