---
name: streamlit-dial-gauge
description: "Implementation of a cool neon dial gauge chart (car speedometer style) for Streamlit using Plotly."
category: ui
risk: safe
source: community
author: Antigravity
tags: [streamlit, ui, gauge, plotly, dial]
---

# Streamlit Dial Gauge (Plotly)

This skill provides a reusable function to render a beautiful, glowing dial meter (gauge) in a Streamlit application, closely matching the UI aesthetics of the Antigravity Clinical AI dashboard.

## Security Audit Report (Pre-Install)
Run via `skill-audit`:
- **Surface Scan:** ✅ No suspicious patterns (no eval, no obfuscation).
- **Script Check:** ✅ No external scripts.
- **Permissions:** ✅ Pure UI component, no file/network access required.
- **Verdict:** ✅ SAFE (Risk Score: 5/100).

## Code Snippet

Use this function in your Streamlit dashboard:

```python
import plotly.graph_objects as go
import streamlit as st

def render_neon_gauge(value, max_value, title, subtitle=""):
    # Calculate percentage
    percentage = (value / max_value) * 100 if max_value > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = percentage,
        number = {"suffix": "%", "font": {"size": 60, "color": "#f8fafc"}},
        title = {'text': f"<span style='font-size:1.5em;color:#38bdf8;font-weight:bold;'>{title}</span><br><span style='font-size:1em;color:#cbd5e1'>{subtitle}</span>"},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#38bdf8", 'tickfont': {'color': "#94a3b8"}},
            'bar': {'color': "rgba(0,0,0,0)"},  # Hide default bar
            'bgcolor': "rgba(255,255,255,0.05)",
            'borderwidth': 2,
            'bordercolor': "rgba(56, 189, 248, 0.3)",
            'steps': [
                {'range': [0, percentage], 'color': "rgba(236, 72, 153, 0.8)"},  # Neon Pink fill
                {'range': [percentage, 100], 'color': "rgba(30, 41, 59, 0.6)"}    # Dark empty space
            ],
            'threshold': {
                'line': {'color': "#38bdf8", 'width': 6}, # Cyan needle
                'thickness': 0.75,
                'value': percentage
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={'family': "Heebo, sans-serif"},
        height=350,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig
```

**Usage:**
```python
fig = render_neon_gauge(current_val, total_val, "Progress", f"{current_val} of {total_val}")
st.plotly_chart(fig, use_container_width=True)
```
