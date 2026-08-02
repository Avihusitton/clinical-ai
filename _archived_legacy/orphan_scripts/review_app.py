# -*- coding: utf-8 -*-
"""
ממשק אישור אנושי מאוחד - Ponytail Doctrine
מאפשר לעבור בין אישור מושגים למילון לבין אישור קשרי מושג-מושג.
"""

from __future__ import annotations
import json
from pathlib import Path
import streamlit as st
import datetime as dt
import docx
from config import Config

# Must be the first Streamlit command
st.set_page_config(page_title="מסוף אישורים", layout="centered", page_icon="✅")

BASE_DIR = Path(__file__).parent
QUEUE_PATH = BASE_DIR / "data" / "concept_relationships_queue.json"
DRAFT_PATH = BASE_DIR / "out" / "glossary_draft.json"
GLOSSARY_PATH = BASE_DIR / "data" / "glossary.json"
EXERCISES_PATH = BASE_DIR / "data" / "exercises.json"

def load_json(path: Path, default=None):
    if default is None:
        default = [] if path.name == "concept_relationships_queue.json" else {}
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_context(file_name: str, terms: list[str]) -> list[str]:
    cfg = Config()
    doc_path = cfg.archive_dir / file_name
    if not doc_path.exists() or not doc_path.suffix.lower() == '.docx':
        return []
    try:
        doc = docx.Document(doc_path)
        contexts = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text: continue
            for term in terms:
                if term in text:
                    contexts.append(text)
                    break
        return contexts
    except Exception:
        return []

st.sidebar.title("🧭 ניווט")
mode = st.sidebar.radio("בחר מסך:", ["אישור מושגים (Glossary)", "אישור קשרים (Relationships)"])

# --- תצוגת סטטוס גלובלית בסרגל הצד ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 סטטוס מערכת")

queue_data = load_json(QUEUE_PATH, [])
draft_data = load_json(DRAFT_PATH, {})
glossary_data = load_json(GLOSSARY_PATH, {})
exercises_data = load_json(EXERCISES_PATH, {})

pending_rels = sum(1 for e in queue_data if e.get("status") == "pending")
approved_rels = sum(1 for e in queue_data if e.get("status") == "approved")

pending_concepts = len(draft_data.get("concepts", {}))
approved_concepts = len(glossary_data.get("concepts", {}))
approved_exercises = len(exercises_data.get("exercises", {}))

col1, col2 = st.sidebar.columns(2)
col1.metric("מושגים מאושרים", approved_concepts + approved_exercises)
col2.metric("קשרים מאושרים", approved_rels)

col3, col4 = st.sidebar.columns(2)
col3.metric("מושגים בהמתנה", pending_concepts)
col4.metric("קשרים בהמתנה", pending_rels)

st.sidebar.markdown("---")
with st.sidebar.expander("📖 רשימת מושגים מאושרים", expanded=False):
    if approved_concepts == 0 and approved_exercises == 0:
        st.caption("טרם אושרו מושגים או תרגילים.")
    else:
        for c in sorted(glossary_data.get("concepts", {}).keys()):
            st.markdown(f"<span style='color:#4CAF50'>■</span> {c}", unsafe_allow_html=True)
        for e in sorted(exercises_data.get("exercises", {}).keys()):
            st.markdown(f"<span style='color:#FF9800'>📝</span> {e}", unsafe_allow_html=True)

with st.sidebar.expander("⏳ רשימת מושגים להמשך אישור", expanded=False):
    if pending_concepts == 0:
        st.caption("אין מושגים ממתינים לאישור.")
    else:
        for c in sorted(draft_data.get("concepts", {}).keys()):
            st.markdown(f"<span style='color:#9E9E9E'>○</span> {c}", unsafe_allow_html=True)

if mode == "אישור קשרים (Relationships)":
    if "queue" not in st.session_state:
        st.session_state.queue = load_json(QUEUE_PATH, [])
    
    queue = st.session_state.queue
    pending = [(i, e) for i, e in enumerate(queue) if e["status"] == "pending"]
    
    st.title("🔗 אישור קשרי מושג-מושג")
    st.caption(
        f"סה\"כ בתור: {len(queue)} | ממתינים: {len(pending)} | "
        f"מאושרים: {sum(1 for e in queue if e['status'] == 'approved')} | "
        f"נדחו: {sum(1 for e in queue if e['status'] == 'rejected')}"
    )
    
    if not pending:
        st.success("אין הצעות (קשרים) ממתינות לבדיקה כרגע.")
    else:
        idx, edge = pending[0]
        st.markdown("---")
        st.subheader(f"{edge['concept_a']}   ---[{edge['type']}]-->   {edge['concept_b']}")
        st.markdown("**ציטוט מהמקור:**")
        st.info(edge.get("quote", "(אין ציטוט)"))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("הקשר טיפולי", edge.get("modality", "-"))
        with col2:
            st.metric("מספר שיעור", edge.get("lesson_number") or "-")
        with col3:
            st.metric("chunk_id", edge.get("chunk_id", "-")[:10] + "...")
            
        st.markdown("---")
        c1, c2 = st.columns(2)
        
        def decide(index, new_status):
            st.session_state.queue[index]["status"] = new_status
            st.session_state.queue[index]["decided_at"] = dt.datetime.now().isoformat()
            save_json(QUEUE_PATH, st.session_state.queue)
            
        if c1.button("✅ אשר קשר", use_container_width=True, type="primary"):
            decide(idx, "approved")
            st.rerun()
        if c2.button("❌ דחה קשר", use_container_width=True):
            decide(idx, "rejected")
            st.rerun()
            
        with st.expander("היסטוריית החלטות"):
            for e in [e for e in queue if e["status"] != "pending"][-20:]:
                icon = "✅" if e["status"] == "approved" else "❌"
                st.text(f"{icon} {e['concept_a']} --[{e['type']}]--> {e['concept_b']}")

elif mode == "אישור מושגים (Glossary)":
    st.title("📖 אישור מילון מושגים")
    
    # הנתונים כבר נטענו למעלה עבור סרגל הצד
    # נשתמש בהם ישירות

    
    if "concepts" in draft_data and draft_data["concepts"]:
        draft_concepts = draft_data["concepts"]
        existing_glossary = glossary_data.get("concepts", {})
        existing_exercises = exercises_data.get("exercises", {})
        
        keys_to_remove = []
        for d_name, d_meta in draft_concepts.items():
            if d_name in existing_glossary:
                current_syns = set(existing_glossary[d_name].get("synonyms", []))
                new_syns = set(d_meta.get("synonyms", []))
                existing_glossary[d_name]["synonyms"] = sorted(list(current_syns | new_syns))
                keys_to_remove.append(d_name)
            elif d_name in existing_exercises:
                current_syns = set(existing_exercises[d_name].get("synonyms", []))
                new_syns = set(d_meta.get("synonyms", []))
                existing_exercises[d_name]["synonyms"] = sorted(list(current_syns | new_syns))
                keys_to_remove.append(d_name)
                
        if keys_to_remove:
            for k in keys_to_remove:
                del draft_concepts[k]
            save_json(GLOSSARY_PATH, glossary_data)
            save_json(EXERCISES_PATH, exercises_data)
            save_json(DRAFT_PATH, draft_data)
            st.rerun()
            
    if "concepts" not in draft_data or not draft_data["concepts"]:
        st.success("אין מושגים ממתינים לאישור בטיוטה כרגע.")
    else:
        draft_concepts = draft_data["concepts"]
        
        if "glossary_idx" not in st.session_state:
            st.session_state.glossary_idx = 0
            
        current_idx = st.session_state.glossary_idx % len(draft_concepts)
        concept_name = list(draft_concepts.keys())[current_idx]
        concept_meta = draft_concepts[concept_name]
        
        st.caption(f"ממתינים לאישור: {len(draft_concepts)} מושגים")
        
        st.markdown("---")
        st.subheader(f"מושג לבדיקה: **{concept_name}**")
        st.markdown(f"**הגדרה:** {concept_meta.get('definition', '')}")
        synonyms = concept_meta.get('synonyms', [])
        if synonyms:
            st.markdown(f"**מילים נרדפות:** {', '.join(synonyms)}")
        
        # Show context
        source_doc = draft_data.get("source_document", "")
        if source_doc:
            with st.expander("🔍 רקע והקשר מתוך מסמך המקור"):
                terms_to_search = [concept_name] + synonyms
                contexts = get_context(source_doc, terms_to_search)
                if contexts:
                    st.caption(f"נמצאו {len(contexts)} אזכורים (מציג עד 3). מקור: {source_doc}")
                    for ctx in contexts[:3]:
                        highlighted = ctx
                        for term in terms_to_search:
                            highlighted = highlighted.replace(term, f"**{term}**")
                        st.info(highlighted)
                else:
                    st.write(f"לא נמצא הקשר ברור במסמך המקור ({source_doc}).")
        
        st.markdown("---")
        
        existing_concepts = glossary_data.get("concepts", {})
        primary_choices = ["✨ מושג ראשי (הורה)", "📄 דף עבודה / תרגיל"] + [f"🔗 מושג משני של: {k}" for k, v in existing_concepts.items() if not v.get("parent")]
        
        default_idx = 0
        if concept_meta.get("type") == "exercise":
            default_idx = 1
        elif concept_meta.get("parent"):
            parent_name = concept_meta["parent"]
            target_str = f"🔗 מושג משני של: {parent_name}"
            if target_str in primary_choices:
                default_idx = primary_choices.index(target_str)
                
        selected_parent_str = st.selectbox("הגדר את סוג המושג:", primary_choices, index=default_idx)
        
        col1, col2, col3 = st.columns(3)
        if col1.button("✅ אשר והכנס", use_container_width=True, type="primary"):
            if selected_parent_str == "📄 דף עבודה / תרגיל":
                if "exercises" not in exercises_data:
                    exercises_data["exercises"] = {}
                exercises_data["exercises"][concept_name] = {
                    "definition": concept_meta.get("definition", ""),
                    "synonyms": synonyms
                }
                save_json(EXERCISES_PATH, exercises_data)
            else:
                parent_val = None if selected_parent_str == "✨ מושג ראשי (הורה)" else selected_parent_str.replace("🔗 מושג משני של: ", "")
                if "concepts" not in glossary_data:
                    glossary_data["concepts"] = {}
                glossary_data["concepts"][concept_name] = {
                    "definition": concept_meta.get("definition", ""),
                    "synonyms": synonyms,
                    "parent": parent_val
                }
                save_json(GLOSSARY_PATH, glossary_data)
                
            del draft_concepts[concept_name]
            save_json(DRAFT_PATH, draft_data)
            # If we deleted an item and the index is now out of bounds, modulus will fix it on next render.
            st.rerun()
            
        if col2.button("❌ דחה (לא מושג)", use_container_width=True):
            del draft_concepts[concept_name]
            save_json(DRAFT_PATH, draft_data)
            st.rerun()
            
        if col3.button("⏭️ דלג לבנתיים", use_container_width=True):
            st.session_state.glossary_idx += 1
            st.rerun()