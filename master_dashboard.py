# -*- coding: utf-8 -*-
import streamlit as st
import os
import sys
import time
import json
import subprocess
from pathlib import Path
import plotly.graph_objects as go

st.set_page_config(page_title="Clinical AI Pipeline Control", layout="wide", page_icon="⚡")

# --- Custom CSS for "Impeccable" UI ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Heebo', sans-serif;
    direction: rtl;
    text-align: right;
}

/* Stunning dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    color: #f8fafc;
}

/* Hide Streamlit header & footer */
header {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Glowing Headers */
h1 {
    font-weight: 800;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.2rem;
    font-size: 3.5rem !important;
}

.subtitle {
    text-align: center;
    color: #94a3b8;
    font-size: 1.2rem;
    margin-bottom: 3rem;
}

/* Metric Cards */
div[data-testid="metric-container"] {
    background-color: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 1.5rem;
    padding: 1.5rem 2rem;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
    transition: all 0.3s ease;
    text-align: center;
}

div[data-testid="metric-container"]:hover {
    transform: translateY(-5px);
    border-color: rgba(56, 189, 248, 0.3);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6);
}

div[data-testid="metric-container"] label {
    font-size: 1.1rem;
    color: #cbd5e1 !important;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 3.5rem;
    font-weight: 800;
    color: #ffffff;
    text-shadow: 0 0 20px rgba(255,255,255,0.2);
}

div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
    font-size: 1.1rem;
}

/* Custom Primary Button */
.stButton > button[kind="primary"] {
    background: linear-gradient(45deg, #ec4899, #8b5cf6);
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 2rem;
    padding: 0.75rem 2.5rem;
    font-size: 1.2rem;
    box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
    transition: all 0.3s ease;
    width: 100%;
}

.stButton > button[kind="primary"]:hover {
    transform: scale(1.02);
    box-shadow: 0 8px 25px rgba(236, 72, 153, 0.6);
}

/* Normal Button */
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.05);
    color: #cbd5e1;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 2rem;
    padding: 0.75rem 2.5rem;
    font-size: 1.2rem;
    transition: all 0.3s ease;
    width: 100%;
}

.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.1);
    border-color: rgba(255,255,255,0.3);
    color: white;
}

/* Progress bar styling */
.stProgress > div > div > div > div {
    background-image: linear-gradient(to right, #38bdf8, #818cf8);
    border-radius: 1rem;
}
.stProgress > div > div {
    border-radius: 1rem;
    background-color: rgba(255,255,255,0.1);
    height: 1.5rem;
}
.stProgress p {
    font-size: 1.2rem;
    font-weight: 600;
    color: #38bdf8;
    margin-bottom: 0.5rem;
}

hr {
    border-color: rgba(255,255,255,0.1);
    margin: 3rem 0;
}

.pulsing-text {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    color: #38bdf8;
    font-weight: bold;
    text-align: center;
    font-size: 1.5rem;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .6; }
}

.eta-box {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid #38bdf8;
    border-radius: 1.5rem;
    padding: 2rem;
    text-align: center;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
}
.eta-title {
    color: #94a3b8;
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.eta-value {
    color: #38bdf8;
    font-size: 3.5rem;
    font-weight: 800;
    text-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
}
.current-action {
    color: #f8fafc;
    font-size: 1.4rem;
    margin-top: 1rem;
    font-weight: 600;
    background: rgba(255,255,255,0.05);
    padding: 1.5rem;
    border-radius: 1rem;
    border: 1px dashed rgba(255,255,255,0.2);
}

.phase-indicator {
    display: inline-block;
    background: #ec4899;
    color: white;
    padding: 0.2rem 1rem;
    border-radius: 1rem;
    font-size: 1rem;
    font-weight: bold;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# -----------------
# Setup & Constants
# -----------------
INBOX_DIR = Path("docs_inbox")
ARCHIVE_DIR = Path("docs_archive")
ERROR_DIR = Path("docs_error")
STATUS_FILE = Path("out/pipeline_status.json")
GLOSSARY_FILE = Path("out/glossary_draft.json")

for d in [INBOX_DIR, ARCHIVE_DIR, ERROR_DIR]:
    d.mkdir(exist_ok=True)

# -----------------
# Helper Functions
# -----------------
def count_files(dir_path: Path) -> int:
    return len([f for f in dir_path.rglob("*.*") if f.is_file() and f.name != ".gitkeep"])

def get_pipeline_status():
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except:
            pass
    return {"status": "ממתין להתחלה"}

def render_neon_gauge(value, max_value, title, subtitle=""):
    percentage = (value / max_value) * 100 if max_value > 0 else 0
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percentage,
        number={"suffix": "%", "font": {"size": 50, "color": "#f8fafc"}},
        title={'text': f"<span style='font-size:1.4em;color:#38bdf8;font-weight:bold;'>{title}</span><br><br><span style='font-size:2.0em;color:#f8fafc;font-weight:bold;text-shadow:0px 0px 5px rgba(56,189,248,0.5);'>{subtitle}</span>"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#38bdf8", 'tickfont': {'color': "#94a3b8"}},
            'bar': {'color': "rgba(0,0,0,0)"},
            'bgcolor': "rgba(255,255,255,0.05)",
            'borderwidth': 2,
            'bordercolor': "rgba(56, 189, 248, 0.3)",
            'steps': [
                {'range': [0, percentage], 'color': "rgba(236, 72, 153, 0.8)"},
                {'range': [percentage, 100], 'color': "rgba(30, 41, 59, 0.6)"}
            ],
            'threshold': {
                'line': {'color': "#38bdf8", 'width': 6},
                'thickness': 0.75,
                'value': percentage
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={'family': "Heebo, sans-serif"}, height=300, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def start_pipeline(limit=None):
    cmd = [sys.executable, "run_full_pipeline.py"]
    if limit:
        cmd.extend(["--limit", str(limit)])
    if os.name == 'nt':
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(cmd)
    
    st.session_state.running = True
    st.session_state.start_time = time.time()
    
    # Preserve total API calls if exists
    total_calls = 0
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                total_calls = d.get("total_api_calls", 0)
        except:
            pass

    STATUS_FILE.parent.mkdir(exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "status": "מאתחל תהליך...",
            "total_api_calls": total_calls,
            "current_run_api_calls": 0
        }, f, ensure_ascii=False)
    time.sleep(1)
    st.rerun()

# -----------------
# UI Rendering
# -----------------
st.markdown("<h1>⚡ Clinical AI Command Center</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>מערכת שליטה מרכזית - חישובים ונתונים חזותיים בזמן אמת</p>", unsafe_allow_html=True)

# Initial State
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None

status_data = get_pipeline_status()
status_text = status_data.get("status", "ממתין להתחלה")
current_chunk = status_data.get("current_chunk", 0)
total_chunks = status_data.get("total_doc_chunks", 0)
current_file = status_data.get("current_file", "")
total_project_chunks = status_data.get("total_project_chunks", 0)
processed_project_chunks = status_data.get("processed_project_chunks", 0)
current_run_api_calls = status_data.get("current_run_api_calls", 0)
total_api_calls = status_data.get("total_api_calls", 0)

if "הסתיים בהצלחה" in status_text or "נכשל" in status_text:
    st.session_state.running = False
elif "ממתין" not in status_text and not st.session_state.running:
    # If the file says it's running but session state doesn't know, recover
    st.session_state.running = True

# Recover start time if needed
if st.session_state.running and not st.session_state.start_time:
    if STATUS_FILE.exists():
        st.session_state.start_time = STATUS_FILE.stat().st_mtime
    else:
        st.session_state.start_time = time.time()

# File counts
inbox_count = count_files(INBOX_DIR)
archive_count = count_files(ARCHIVE_DIR)
error_count = count_files(ERROR_DIR)
total_files = inbox_count + archive_count + error_count

# Calculate Phase and Details
current_phase = 0
exact_action = "מערכת בהמתנה."
concepts_count = 0
eta_str = "--:--"
elapsed_str = "00:00"
phase_badge = ""

if st.session_state.running:
    if "1/2" in status_text:
        current_phase = 1
        phase_badge = "שלב 1 מתוך 2: ניתוח ולמידה"
        if GLOSSARY_FILE.exists():
            try:
                with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    concepts_count = len(d.get("concepts", {}))
                exact_action = f"🧠 המנוע קורא את המסמכים... עד כה זוקקו <b>{concepts_count}</b> מושגים ותרגילים מהטקסטים!"
                if total_project_chunks > 0:
                    exact_action += f"<br><span style='font-size: 1.2rem; color: #f8fafc;'>סך הכל בפרויקט: <b>{processed_project_chunks}</b> מתוך <b>{total_project_chunks}</b> קטעי תוכן עובדו (נותרו עוד {total_project_chunks - processed_project_chunks})</span>"
                if total_chunks > 0:
                    exact_action += f"<br><span style='font-size: 1.1rem; color: #cbd5e1;'>מעבד כעת את <b>{current_file}</b>: קטע <b>{current_chunk - 1}</b> עובדו מתוך <b>{total_chunks}</b> (נותרו עוד {total_chunks - current_chunk + 1} במסמך זה)</span>"
            except:
                exact_action = "🧠 סורק מסמכים (חילוץ מושגים)..."
        else:
            exact_action = "🧠 מתחיל סריקת מסמכים ולמידת מושגים..."
            if total_project_chunks > 0:
                exact_action += f"<br><span style='font-size: 1.2rem; color: #f8fafc;'>סך הכל בפרויקט: <b>{processed_project_chunks}</b> מתוך <b>{total_project_chunks}</b> קטעי תוכן עובדו (נותרו עוד {total_project_chunks - processed_project_chunks})</span>"
            if total_chunks > 0:
                exact_action += f"<br><span style='font-size: 1.1rem; color: #cbd5e1;'>מעבד כעת את <b>{current_file}</b>: קטע <b>{current_chunk - 1}</b> עובדו מתוך <b>{total_chunks}</b> (נותרו עוד {total_chunks - current_chunk + 1} במסמך זה)</span>"

    elif "2/2" in status_text:
        current_phase = 2
        phase_badge = "שלב 2 מתוך 2: בניית הגרף (Neo4j)"
        exact_action = f"💾 מחבר נקודות ומזריק לגרף: מעבד ומעביר כעת לארכיון קובץ <b>{archive_count+1}</b> מתוך <b>{total_files}</b>"

    # ETA & Elapsed Calculation
    if st.session_state.start_time:
        elapsed = time.time() - st.session_state.start_time
        emins = int(elapsed // 60)
        esecs = int(elapsed % 60)
        elapsed_str = f"{emins:02d}:{esecs:02d}"
        
        if current_phase == 2 and archive_count > 0:
            time_per_file = elapsed / archive_count
            remaining = (total_files - archive_count) * time_per_file
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            eta_str = f"{mins:02d}:{secs:02d}"
        elif current_phase == 1:
            eta_str = "מחשב קצב..."
        else:
            eta_str = "בחישוב..."

# --- Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("📥 בהמתנה (Inbox)", f"{inbox_count}", delta="- מעובד ברקע" if st.session_state.running else None, delta_color="off")
col2.metric("✅ בארכיון (הושלם Neo4j)", f"{archive_count}")
col3.metric("🧠 מושגים שזוקקו", f"{concepts_count}", delta="עולה בזמן אמת" if current_phase == 1 else None, delta_color="normal")
col4.metric("🌐 קריאות API (ריצה נוכחית)", f"{current_run_api_calls}", delta=f"סה״כ פרויקט: {total_api_calls}", delta_color="off")

# --- Live Animated Dashboard ---
if st.session_state.running:
    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.markdown(f"<span class='phase-indicator'>{phase_badge}</span>", unsafe_allow_html=True)
        st.subheader("מצב עבודה (זמן אמת)")
        
        # Exact Action Box
        st.markdown(f"<div class='current-action pulsing-text'>{exact_action}</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Dial Gauge Meters
        if current_phase == 1 and total_project_chunks > 0:
            if total_chunks > 1:
                # Two gauges side-by-side: Project overall, and Current file
                g1, g2 = st.columns(2)
                with g1:
                    st.plotly_chart(render_neon_gauge(processed_project_chunks, total_project_chunks, "התקדמות פרויקט כוללת", f"{processed_project_chunks} / {total_project_chunks}"), width="stretch")
                with g2:
                    st.plotly_chart(render_neon_gauge(current_chunk - 1, total_chunks, f"מסמך נוכחי: {current_file}", f"{current_chunk - 1} / {total_chunks}"), width="stretch")
            else:
                st.plotly_chart(render_neon_gauge(processed_project_chunks, total_project_chunks, "התקדמות חילוץ מושגים", f"{processed_project_chunks} מתוך {total_project_chunks}"), width="stretch")
        elif current_phase == 2 and total_files > 0:
            st.plotly_chart(render_neon_gauge(archive_count, total_files, "התקדמות בניית גרף Neo4j", f"{archive_count} מתוך {total_files}"), width="stretch")
        else:
            # Fallback progress bar if no data yet
            display_text = status_text if "" not in status_text else "טוען נתונים..."
            st.progress(0.0, text=display_text)
        
    with c_right:
        st.markdown(f"""
        <div class="eta-box">
            <div class="eta-title">זמן שחלף</div>
            <div class="eta-value" style="font-size: 2.5rem;">⏳ {elapsed_str}</div>
            <hr style="margin: 1.5rem 0; opacity: 0.3;">
            <div class="eta-title">זמן משוער לסיום (ETA)</div>
            <div class="eta-value">⏱️ {eta_str}</div>
        </div>
        """, unsafe_allow_html=True)

# --- Controls ---
st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([1, 1, 1])

with c1:
    if st.button("🧪 טסט מהיר (קובץ בודד)", key="test_btn", disabled=st.session_state.running):
        start_pipeline(limit=1)

with c2:
    if st.button("🚀 הפעלת מנוע (כל הקבצים)!", type="primary", key="full_btn", disabled=st.session_state.running):
        start_pipeline()

with c3:
    if not st.session_state.running:
        st.markdown("<div style='text-align: center; color: #4ade80; font-size: 1.2rem; font-weight: bold; margin-top: 0.5rem;'>✓ המערכת בהמתנה ומוכנה לפעולה.</div>", unsafe_allow_html=True)

# --- Trigger Auto Refresh ---
if st.session_state.running:
    time.sleep(2)
    st.rerun()
