# -*- coding: utf-8 -*-
"""Warm, dependency-free Hebrew workspace UI for the local Clinical AI app."""

from __future__ import annotations


def render_workspace_html() -> str:
    """Return the complete local workspace page."""

    return r"""<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>דרך | מרחב חשיבה קלינית</title>
  <style>
    :root {
      --paper: #f4efe4;
      --paper-deep: #e9dfce;
      --canvas: #fbf8f0;
      --ink: #243029;
      --muted: #6e756d;
      --olive: #68735a;
      --olive-dark: #46513e;
      --sage: #dce2d3;
      --clay: #a65f43;
      --clay-soft: #f0d8ca;
      --gold: #bd8d43;
      --line: rgba(58, 68, 57, .17);
      --line-strong: rgba(58, 68, 57, .30);
      --shadow: 0 22px 60px rgba(63, 52, 39, .11);
      --radius-lg: 28px;
      --radius-md: 18px;
      --radius-sm: 12px;
      color-scheme: light;
    }

    * { box-sizing: border-box; }

    html {
      min-height: 100%;
      direction: rtl;
      text-align: right;
      background: var(--paper);
    }

    body {
      min-height: 100vh;
      margin: 0;
      color: var(--ink);
      direction: rtl;
      text-align: right;
      font-family: "Segoe UI", Arial, sans-serif;
      background:
        radial-gradient(circle at 13% 7%, rgba(189, 141, 67, .13), transparent 26rem),
        radial-gradient(circle at 91% 94%, rgba(104, 115, 90, .15), transparent 29rem),
        linear-gradient(145deg, #f7f1e7 0%, var(--paper) 48%, #eee5d5 100%);
    }

    body::before {
      position: fixed;
      inset: 0;
      z-index: -1;
      content: "";
      opacity: .23;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(79, 83, 68, .055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(79, 83, 68, .04) 1px, transparent 1px);
      background-size: 27px 27px;
      mask-image: linear-gradient(to bottom, black, transparent 75%);
    }

    button, input, select, textarea { font: inherit; }
    button, select, label { -webkit-tap-highlight-color: transparent; }
    button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible,
    summary:focus-visible {
      outline: 3px solid rgba(166, 95, 67, .30);
      outline-offset: 2px;
    }

    .app-shell {
      display: grid;
      grid-template-columns: minmax(220px, 275px) minmax(420px, 1fr) minmax(205px, 250px);
      gap: 18px;
      width: min(1480px, 100%);
      min-height: 100vh;
      margin: 0 auto;
      padding: 18px;
      direction: rtl;
      text-align: right;
    }

    .panel {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: rgba(251, 248, 240, .84);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }

    .workspace-sidebar {
      display: flex;
      flex-direction: column;
      min-height: calc(100vh - 36px);
      overflow: hidden;
    }

    .brand {
      position: relative;
      padding: 27px 24px 23px;
      overflow: hidden;
      color: #f8f4e9;
      background:
        linear-gradient(150deg, rgba(70, 81, 62, .98), rgba(91, 99, 76, .96)),
        var(--olive-dark);
    }

    .brand::after {
      position: absolute;
      width: 150px;
      height: 150px;
      left: -55px;
      bottom: -74px;
      content: "";
      border: 1px solid rgba(255, 255, 255, .22);
      border-radius: 50%;
      box-shadow:
        0 0 0 17px rgba(255, 255, 255, .035),
        0 0 0 35px rgba(255, 255, 255, .025);
    }

    .brand-mark {
      display: flex;
      align-items: center;
      gap: 12px;
      position: relative;
      z-index: 1;
    }

    .brand-path {
      position: relative;
      width: 34px;
      height: 46px;
      flex: 0 0 auto;
      border-radius: 50% 50% 44% 44%;
      transform: rotate(8deg);
      background: linear-gradient(180deg, #ecd59e, var(--gold));
      clip-path: polygon(37% 0, 83% 0, 63% 41%, 81% 100%, 31% 100%, 46% 54%);
    }

    .brand h1 {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 2.15rem;
      font-weight: 500;
      line-height: .95;
    }

    .brand p {
      margin: 7px 0 0;
      color: rgba(255, 255, 255, .75);
      font-size: .88rem;
      letter-spacing: .015em;
    }

    .sidebar-section {
      padding: 20px 18px 17px;
      border-bottom: 1px solid var(--line);
    }

    .eyebrow {
      display: block;
      margin: 0 0 9px;
      color: var(--muted);
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .09em;
      text-transform: uppercase;
    }

    .profile-row {
      display: flex;
      gap: 8px;
      align-items: stretch;
    }

    input[type="text"] {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line-strong);
      border-radius: var(--radius-sm);
      color: var(--ink);
      direction: rtl;
      text-align: right;
      background: rgba(255, 255, 255, .58);
      padding: 9px 11px;
    }

    .add-user {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      margin-top: 9px;
    }

    .icon-button, .quiet-button, .primary-button {
      border: 0;
      cursor: pointer;
      transition: transform .16s ease, background .16s ease, opacity .16s ease;
    }

    .icon-button:hover, .quiet-button:hover, .primary-button:hover {
      transform: translateY(-1px);
    }

    .icon-button:disabled, .quiet-button:disabled, .primary-button:disabled {
      cursor: wait;
      opacity: .55;
      transform: none;
    }

    .icon-button {
      min-width: 42px;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      color: var(--olive-dark);
      background: var(--sage);
      font-size: 1.25rem;
      font-weight: 500;
    }

    .conversation-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 18px 18px 8px;
    }

    .conversation-heading h2 {
      margin: 0;
      font-size: 1rem;
      font-weight: 750;
    }

    .quiet-button {
      border: 1px solid var(--line-strong);
      border-radius: 999px;
      padding: 8px 12px;
      color: var(--olive-dark);
      background: transparent;
      font-size: .82rem;
      font-weight: 700;
    }

    .conversation-list {
      display: flex;
      flex: 1;
      flex-direction: column;
      gap: 6px;
      max-height: calc(100vh - 340px);
      min-height: 180px;
      padding: 4px 10px 20px;
      overflow-y: auto;
      scrollbar-width: thin;
      scrollbar-color: var(--paper-deep) transparent;
    }

    .conversation-item {
      width: 100%;
      border: 1px solid transparent;
      border-radius: 14px;
      padding: 12px 13px;
      cursor: pointer;
      color: var(--ink);
      direction: rtl;
      text-align: right;
      background: transparent;
    }

    .conversation-item:hover { background: rgba(104, 115, 90, .07); }

    .conversation-item.active {
      border-color: rgba(104, 115, 90, .24);
      background: var(--sage);
    }

    .conversation-item strong {
      display: block;
      overflow: hidden;
      font-size: .91rem;
      font-weight: 700;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .conversation-item span {
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font-size: .73rem;
    }

    .patient-item {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 8px;
    }

    .patient-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      border: 1px solid transparent;
      border-radius: 14px;
      padding: 10px 13px;
      cursor: pointer;
      color: var(--ink);
      font-weight: 700;
      background: transparent;
      font-family: inherit;
      font-size: .95rem;
    }
    
    .patient-header:hover { background: rgba(104, 115, 90, .07); }
    .patient-header.expanded {
      background: rgba(104, 115, 90, .12);
    }

    .patient-conversations {
      display: none;
      flex-direction: column;
      gap: 4px;
      padding-right: 15px;
      border-right: 2px solid var(--line);
      margin-right: 15px;
      margin-top: 5px;
    }
    .patient-conversations.open {
      display: flex;
    }

    .empty-state {
      margin: auto;
      padding: 22px 13px;
      color: var(--muted);
      line-height: 1.6;
      text-align: right;
      font-size: .87rem;
    }

    .local-note {
      display: flex;
      gap: 9px;
      align-items: flex-start;
      margin: auto 15px 15px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      color: var(--muted);
      background: rgba(233, 223, 206, .48);
      font-size: .76rem;
      line-height: 1.55;
    }

    .local-note .seed {
      color: var(--olive);
      font-size: 1rem;
      line-height: 1;
    }

    .conversation-main {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      grid-template-rows: auto minmax(320px, 1fr) auto;
      min-width: 0;
      min-height: calc(100vh - 36px);
      overflow: hidden;
    }

    .conversation-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      min-height: 87px;
      padding: 18px 25px;
      border-bottom: 1px solid var(--line);
    }

    .conversation-title {
      min-width: 0;
    }

    .conversation-title h2 {
      margin: 0;
      overflow: hidden;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(1.35rem, 2.2vw, 1.85rem);
      font-weight: 500;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .conversation-title p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: .82rem;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      flex: 0 0 auto;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 11px;
      color: var(--muted);
      background: rgba(255, 255, 255, .45);
      font-size: .75rem;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--gold);
      box-shadow: 0 0 0 4px rgba(189, 141, 67, .13);
    }

    .status-badge.ready .status-dot {
      background: var(--olive);
      box-shadow: 0 0 0 4px rgba(104, 115, 90, .14);
    }

    .message-timeline {
      position: relative;
      width: 100%;
      min-width: 0;
      min-height: 300px;
      padding: 28px clamp(18px, 4.5vw, 58px) 42px;
      overflow-y: auto;
      scroll-behavior: smooth;
      scrollbar-width: thin;
      scrollbar-color: var(--paper-deep) transparent;
    }

    .message-timeline::before {
      position: absolute;
      top: 34px;
      right: clamp(27px, calc(4.5vw + 10px), 68px);
      bottom: 34px;
      width: 1px;
      content: "";
      background: linear-gradient(var(--line-strong), transparent);
    }

    .timeline-welcome {
      position: relative;
      max-width: 590px;
      margin: 7vh auto 0;
      padding: 30px;
      border: 1px solid var(--line);
      border-radius: 26px 8px 26px 26px;
      background:
        radial-gradient(circle at 88% 0%, rgba(189, 141, 67, .12), transparent 13rem),
        rgba(255, 255, 255, .44);
    }

    .timeline-welcome h3 {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.55rem;
      font-weight: 500;
    }

    .timeline-welcome p {
      margin: 11px 0 0;
      color: var(--muted);
      line-height: 1.75;
    }

    .timeline-welcome .path-line {
      width: 55px;
      height: 3px;
      margin: 18px 0 0 auto;
      border-radius: 3px;
      background: linear-gradient(to left, var(--clay), var(--gold));
    }

    .message {
      position: relative;
      z-index: 1;
      min-width: 0;
      max-width: 100%;
      margin: 0 0 24px;
      padding-right: 33px;
    }

    .message::before {
      position: absolute;
      top: 5px;
      right: 0;
      width: 17px;
      height: 17px;
      content: "";
      border: 4px solid var(--canvas);
      border-radius: 50%;
      background: var(--olive);
      box-shadow: 0 0 0 1px var(--line-strong);
    }

    .message.user::before { background: var(--clay); }
    .message.clarification::before { background: var(--gold); }

    .message-label {
      display: flex;
      align-items: baseline;
      gap: 9px;
      margin-bottom: 7px;
      color: var(--muted);
      font-size: .72rem;
    }

    .message-label strong {
      color: var(--ink);
      font-size: .82rem;
    }

    .message-body {
      width: 100%;
      max-width: 760px;
      border: 1px solid var(--line);
      border-radius: 7px 18px 18px 18px;
      padding: 16px 18px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      line-height: 1.78;
      background: rgba(255, 255, 255, .48);
      text-align: right;
      direction: rtl;
    }

    .message.user .message-body {
      width: min(680px, 100%);
      max-width: 100%;
      border-color: rgba(166, 95, 67, .18);
      background: rgba(240, 216, 202, .47);
    }

    .message.clarification .message-body {
      border-color: rgba(189, 141, 67, .34);
      background:
        linear-gradient(90deg, rgba(189, 141, 67, .08), transparent),
        rgba(255, 252, 242, .74);
    }

    .clarification-ribbon {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin: -2px 0 10px;
      border-radius: 999px;
      padding: 5px 9px;
      color: #765823;
      background: rgba(189, 141, 67, .16);
      font-size: .73rem;
      font-weight: 700;
    }

    .answer-metrics {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 9px;
    }

    .answer-metric {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 9px;
      color: var(--muted);
      background: rgba(255, 255, 255, .35);
      font-size: .72rem;
    }

    .answer-metric.cost {
      color: var(--olive-dark);
      background: rgba(220, 226, 211, .66);
    }

    .evidence {
      width: 100%;
      max-width: 760px;
      margin-top: 9px;
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--muted);
      background: rgba(244, 239, 228, .55);
      font-size: .78rem;
    }

    .message.optimistic {
      opacity: 0.6;
    }
    
    .typing-indicator {
      display: inline-flex;
      gap: 4px;
      align-items: center;
      padding: 6px 4px;
    }
    
    .typing-indicator span {
      width: 6px;
      height: 6px;
      background: var(--muted);
      border-radius: 50%;
      animation: typing 1.4s infinite ease-in-out both;
    }
    
    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }

    .evidence summary {
      padding: 10px 13px;
      cursor: pointer;
      color: var(--olive-dark);
      font-weight: 700;
      list-style-position: inside;
    }

    .evidence-content {
      padding: 2px 13px 13px;
      line-height: 1.6;
    }

    .evidence-group {
      padding: 10px 0;
      border-top: 1px solid var(--line);
    }

    .evidence-group:first-child { border-top: 0; }
    .evidence-group strong { display: block; margin-bottom: 5px; color: var(--ink); }
    .evidence-group ul { margin: 0; padding-right: 18px; }

    .composer-wrap {
      position: relative;
      padding: 13px 20px 20px;
      border-top: 1px solid var(--line);
      background: linear-gradient(to bottom, rgba(251, 248, 240, .58), rgba(251, 248, 240, .96));
    }

    .privacy-warning {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      margin: 0 3px 10px;
      color: #7b644a;
      font-size: .73rem;
      line-height: 1.45;
    }

    .composer {
      position: relative;
      border: 1px solid var(--line-strong);
      border-radius: 21px;
      background: rgba(255, 255, 255, .68);
      box-shadow: 0 12px 35px rgba(65, 57, 44, .08);
      overflow: hidden;
    }

    textarea {
      display: block;
      width: 100%;
      min-height: 90px;
      max-height: 270px;
      resize: vertical;
      border: 0;
      outline: 0;
      padding: 16px 18px 8px;
      color: var(--ink);
      direction: rtl;
      text-align: right;
      line-height: 1.6;
      background: transparent;
    }

    textarea::placeholder { color: #969990; }

    .composer-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-height: 57px;
      padding: 8px 10px 10px 14px;
    }

    .composer-options {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      align-items: center;
    }

    .check-option {
      display: inline-flex;
      gap: 7px;
      align-items: center;
      cursor: pointer;
      color: var(--ink);
      font-size: .77rem;
    }

    input[type="checkbox"] {
      width: 17px;
      height: 17px;
      margin: 0;
      accent-color: var(--olive);
      cursor: pointer;
    }

    .model-select {
      width: auto;
      min-width: 148px;
      min-height: 34px;
      border-radius: 999px;
      padding-top: 5px;
      padding-bottom: 5px;
      color: var(--olive-dark);
      background-color: var(--sage);
      font-size: .74rem;
    }

    .primary-button {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      justify-content: center;
      min-width: 105px;
      min-height: 42px;
      border-radius: 14px;
      padding: 9px 17px;
      color: #fffaf0;
      background: linear-gradient(145deg, var(--clay), #8f4d37);
      box-shadow: 0 8px 18px rgba(166, 95, 67, .21);
      font-weight: 750;
    }

    .primary-button .arrow {
      font-size: 1.05rem;
      transform: translateY(-1px);
    }

    .error-banner {
      margin: 0 0 10px;
      border: 1px solid rgba(166, 95, 67, .28);
      border-radius: 12px;
      padding: 10px 12px;
      color: #773f30;
      background: rgba(240, 216, 202, .68);
      font-size: .8rem;
      line-height: 1.5;
    }

    .insight-panel {
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: calc(100vh - 36px);
      border: 0;
      background: transparent;
      box-shadow: none;
    }

    .insight-card {
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      background: rgba(251, 248, 240, .76);
      box-shadow: 0 14px 40px rgba(63, 52, 39, .075);
    }

    .insight-card h3 {
      margin: 0 0 13px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.12rem;
      font-weight: 500;
    }

    .cost-value {
      margin: 4px 0;
      color: var(--olive-dark);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 2rem;
      line-height: 1;
    }

    .cost-caption, .insight-copy {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: .75rem;
      line-height: 1.6;
    }

    .setting {
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }

    .setting:first-of-type { border-top: 0; padding-top: 0; }

    .setting-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 7px;
      margin-bottom: 5px;
      font-size: .79rem;
      font-weight: 700;
    }

    .setting-status {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      color: var(--olive);
      font-size: .68rem;
    }

    .mini-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }

    .setting p {
      margin: 0;
      color: var(--muted);
      font-size: .71rem;
      line-height: 1.55;
    }

    .boundary-card {
      margin-top: auto;
      color: #755f45;
      background:
        linear-gradient(155deg, rgba(240, 216, 202, .34), rgba(251, 248, 240, .82));
    }

    .boundary-mark {
      display: grid;
      width: 36px;
      height: 36px;
      margin-bottom: 11px;
      place-items: center;
      border: 1px solid rgba(166, 95, 67, .23);
      border-radius: 50%;
      color: var(--clay);
      font-family: Georgia, serif;
      font-weight: 700;
    }

    .hidden { display: none !important; }

    .toast {
      position: fixed;
      z-index: 20;
      left: 24px;
      bottom: 24px;
      max-width: min(380px, calc(100vw - 32px));
      border: 1px solid var(--line-strong);
      border-radius: 14px;
      padding: 12px 15px;
      color: var(--ink);
      background: var(--canvas);
      box-shadow: var(--shadow);
      font-size: .82rem;
      line-height: 1.5;
      animation: rise .2s ease-out;
    }

    @keyframes rise {
      from { opacity: 0; transform: translateY(7px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 1120px) {
      .app-shell {
        grid-template-columns: minmax(210px, 250px) minmax(430px, 1fr);
      }

      .insight-panel {
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        min-height: auto;
      }

      .boundary-card { margin-top: 0; }
    }

    @media (max-width: 760px) {
      .app-shell {
        display: flex;
        flex-direction: column;
        min-height: auto;
        padding: 8px;
      }

      .workspace-sidebar, .conversation-main { min-height: auto; }
      .conversation-list { max-height: 220px; min-height: 90px; }
      .local-note { display: none; }
      .conversation-main { min-height: 74vh; }
      .conversation-header { min-height: 76px; padding: 15px 17px; }
      .status-badge { display: none; }
      .message-timeline { min-height: 340px; max-height: 58vh; padding: 20px 15px 30px; }
      .message-timeline::before { right: 24px; }
      .message { padding-right: 32px; }
      .timeline-welcome { margin-top: 2vh; padding: 23px; }
      .composer-wrap { padding: 10px; }
      .composer-toolbar { align-items: flex-end; }
      .composer-options { align-items: flex-start; flex-direction: column; }
      .insight-panel { display: grid; grid-template-columns: 1fr; }
      .toast { right: 16px; left: 16px; bottom: 16px; }
    }

    /* Intake Modal */
    .intake-modal-backdrop {
      position: fixed; inset: 0; background: rgba(36, 48, 41, 0.4);
      backdrop-filter: blur(4px); z-index: 999;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; pointer-events: none; transition: opacity 0.2s;
    }
    .intake-modal-backdrop.open {
      opacity: 1; pointer-events: auto;
    }
    .intake-modal {
      background: var(--paper); border: 1px solid var(--line-strong);
      border-radius: var(--radius-lg); padding: 24px; width: min(600px, 90vw);
      box-shadow: var(--shadow);
      transform: translateY(10px) scale(0.98); transition: transform 0.2s;
    }
    .intake-modal-backdrop.open .intake-modal {
      transform: translateY(0) scale(1);
    }
    .intake-modal h2 { margin: 0 0 16px; font-family: Georgia, serif; font-size: 1.4rem; color: var(--ink); }
    .intake-modal label { display: block; margin-bottom: 6px; font-weight: bold; color: var(--ink); font-size: 0.9rem; }
    .intake-modal textarea { width: 100%; min-height: 180px; margin-bottom: 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; background: rgba(255, 255, 255, 0.5); font-family: inherit; resize: vertical; }
    .intake-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
    .intake-option { display: flex; gap: 10px; padding: 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); cursor: pointer; background: rgba(255, 255, 255, 0.3); }
    .intake-option:hover { background: rgba(255, 255, 255, 0.6); }
    .intake-option input { margin-top: 2px; }
    .intake-option strong { display: block; font-size: 0.95rem; color: var(--ink); }
    .intake-option small { display: block; color: var(--muted); font-size: 0.8rem; margin-top: 4px; line-height: 1.4; }
    .intake-actions { display: flex; justify-content: flex-end; gap: 12px; }

    .intake-tabs { display: flex; gap: 15px; margin-bottom: 15px; border-bottom: 1px solid var(--line); padding-bottom: 5px; }
    .intake-tab { background: none; border: none; font-size: 1.05rem; color: var(--muted); cursor: pointer; padding: 5px 10px; border-bottom: 2px solid transparent; transition: all 0.2s; }
    .intake-tab:hover { color: var(--ink); }
    .intake-tab.active { color: var(--ink); border-bottom-color: var(--clay); font-weight: bold; }
    
    .intake-tab-content { display: none; }
    .intake-tab-content.active { display: block; }
    
    .drop-zone { border: 2px dashed var(--line-strong); border-radius: var(--radius-sm); min-height: 150px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; background: rgba(255, 255, 255, 0.4); cursor: pointer; transition: all 0.2s; padding: 20px; gap: 10px; margin-bottom: 15px; }
    .drop-zone:hover { background: rgba(255, 255, 255, 0.7); border-color: var(--clay); }
    .drop-zone.dragover { background: rgba(166, 95, 67, 0.1); border-color: var(--clay); }
    .drop-zone input[type="file"] { display: none; }
    
    .file-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; }
    .file-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: rgba(255, 255, 255, 0.6); border: 1px solid var(--line); border-radius: var(--radius-sm); font-size: 0.9rem; }
    .file-item button { background: transparent; border: none; color: #a00; font-weight: bold; cursor: pointer; }
    
    .inbox-section { border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; }
    .inbox-file-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; max-height: 200px; overflow-y: auto; padding-left: 5px; }
    .inbox-file-item { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: rgba(255, 255, 255, 0.4); font-size: 0.85rem; }
    .inbox-file-item label { flex: 1; display: flex; align-items: center; gap: 8px; margin: 0; font-weight: normal; font-size: 0.85rem; }
    .inbox-file-item select { padding: 4px; border-radius: 4px; border: 1px solid var(--line); font-size: 0.8rem; }
  </style>

</head>
<body>
  <main class="app-shell">
    <aside class="panel workspace-sidebar" aria-label="סביבות עבודה ושיחות">
      <header class="brand">
        <div class="brand-mark">
          <span class="brand-path" aria-hidden="true"></span>
          <div>
            <h1>דרך</h1>
            <p>מרחב חשיבה קלינית</p>
          </div>
        </div>
      </header>

      <section class="sidebar-section">
        <div class="conversation-heading" style="padding: 0; margin-bottom: 10px;">
          <h2 class="eyebrow" style="margin: 0;">מטפלים</h2>
          <button id="showAddTherapistButton" class="quiet-button" type="button">+ מטפל חדש</button>
        </div>
        <div style="display: flex; gap: 5px; align-items: stretch; margin-bottom: 10px;">
          <select id="therapistSelect" class="model-select" style="flex: 1; font-size: 0.9rem; padding: 8px;"></select>
          <button id="editTherapistButton" class="icon-button" style="min-width: 42px; min-height: 42px; padding: 0; font-size: 1rem; display: flex; align-items: center; justify-content: center;" type="button" title="עריכת שם מטפל" aria-label="עריכת שם מטפל">✏️</button>
          <button id="deleteTherapistButton" class="icon-button" style="min-width: 42px; min-height: 42px; padding: 0; font-size: 1rem; display: flex; align-items: center; justify-content: center; color: var(--danger);" type="button" title="מחיקת מטפל" aria-label="מחיקת מטפל">🗑️</button>
        </div>
        <div class="add-user hidden" id="addTherapistForm">
          <input id="newTherapistName" type="text" maxlength="60" autocomplete="off"
                 placeholder="שם המטפל" aria-label="שם מטפל חדש">
          <button id="addTherapistButton" class="icon-button" type="button"
                  title="הוספת מטפל" aria-label="הוספת מטפל">V</button>
        </div>
      </section>

      <section class="sidebar-section">
        <div class="conversation-heading" style="padding: 0; margin-bottom: 10px;">
          <h2 class="eyebrow" style="margin: 0;">מטופלים</h2>
          <button id="showAddPatientButton" class="quiet-button" type="button">+ מטופל חדש</button>
        </div>
        <div class="add-user hidden" id="addPatientForm">
          <input id="newPatientName" type="text" maxlength="60" autocomplete="off"
                 placeholder="שם בדוי למטופל" aria-label="שם מטופל חדש">
          <button id="addPatientButton" class="icon-button" type="button"
                  title="הוספת מטופל" aria-label="הוספת מטופל">V</button>
        </div>
      </section>

      <nav id="patientList" class="conversation-list" aria-label="רשימת מטופלים">
        <div class="empty-state">טוען מטופלים…</div>
      </nav>


      <section class="sidebar-section" style="border-bottom: 0; padding-bottom: 0;">
        <button id="showIntakeModalButton" class="quiet-button" style="width: 100%; text-align: right; background: rgba(189, 141, 67, 0.1); display: flex; align-items: center; gap: 10px; border-color: rgba(189, 141, 67, 0.3);" type="button">
          <span style="font-size: 1.2rem;">📥</span>
          <span>הזנת חומרים למערכת</span>
        </button>

        <details class="inbox-section">
          <summary class="quiet-button" style="width: 100%; text-align: right; display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border: none; font-weight: bold;">
            <span>📂 קבצים בתיקיית קלט</span>
            <button id="refreshInboxButton" type="button" class="icon-button" style="min-width: 24px; min-height: 24px; font-size: 0.8rem; padding: 0;" title="רענן" aria-label="רענן">🔄</button>
          </summary>
          <div id="inboxFileList" class="inbox-file-list"></div>
          <button id="submitInboxButton" class="primary-button hidden" style="width: 100%; margin-top: 10px; font-size: 0.85rem; padding: 6px;" type="button">הזן נבחרים</button>
          <div id="inboxProgress" class="inbox-progress hidden" style="margin-top: 10px; padding: 10px; background: rgba(189, 141, 67, 0.1); border-radius: 8px; font-size: 0.85rem; text-align: center; border: 1px solid rgba(189, 141, 67, 0.3);">
            <div style="margin-bottom: 5px;">מעבד קבצים... <span id="inboxProgressText">0 / 0</span></div>
            <div style="width: 100%; background: #e0e0e0; height: 6px; border-radius: 3px; overflow: hidden;">
              <div id="inboxProgressBar" style="width: 0%; height: 100%; background: var(--olive); transition: width 0.3s ease;"></div>
            </div>
          </div>
        </details>
      </section>

      <div class="local-note">

        <span class="seed" aria-hidden="true">■</span>
        <span>הפרופילים מפרידים בין מרחבי העבודה במחשב זה. הם אינם מנגנון אבטחה או התחברות.</span>
      </div>
    </aside>

    <section class="panel conversation-main" aria-label="שיחה">
      <header class="conversation-header">
        <div class="conversation-title">
          <span class="eyebrow">רצף טיפולי מתמשך</span>
          <h2 id="activeConversationTitle">שיחה חדשה</h2>
          <p id="activeConversationMeta">ההקשר נבנה בהדרגה לאורך השיחה</p>
        </div>
        <div id="systemStatus" class="status-badge">
          <span class="status-dot" aria-hidden="true"></span>
          <span>בודק את המערכת…</span>
        </div>
      </header>

      <div id="messageTimeline" class="message-timeline" aria-live="polite">
        <div class="timeline-welcome">
          <h3>מתחילים מן השאלה הנכונה</h3>
          <p>כתבו שאלה על השיטה או עדכון המשך בשיחה קיימת. המערכת תאתר הקשר מצומצם מן הידע הקנוני, ואם חסר מידע מהותי היא תחזור אליכם בשאלות הבהרה.</p>
          <div class="path-line" aria-hidden="true"></div>
        </div>
      </div>

      <footer class="composer-wrap">
        <div id="composerError" class="error-banner hidden" role="alert"></div>
        <div class="privacy-warning">
          <span aria-hidden="true">◇</span>
          <span>אין להזין שמות, פרטי קשר או כל פרט מזהה. סביבת הפיתוח המקומית אינה מיועדת לתיעוד קליני חי.</span>
        </div>
        <div class="composer">
          <textarea id="question" maxlength="100000"
                    placeholder="כתבו שאלה או עדכון להמשך התהליך…"
                    aria-label="השאלה או העדכון"></textarea>
          <div class="composer-toolbar">
            <div class="composer-options">
              <label class="check-option" for="useAi">
                <input id="useAi" type="checkbox" checked>
                <span>ניסוח מקצועי בעזרת AI</span>
              </label>
              <select id="aiModel" class="model-select" aria-label="בחירת מודל">
                <option value="auto" selected>בחירה אוטומטית (מומלץ)</option>
              </select>
              <label class="check-option" for="confirmNoPatientData">
                <input id="confirmNoPatientData" type="checkbox">
                <span>ללא פרטים מזהים</span>
              </label>
            </div>
            <button id="askButton" class="primary-button" type="button">
              <span>שליחה</span><span class="arrow" aria-hidden="true">←</span>
            </button>
          </div>
        </div>
      </footer>
    </section>

    <aside class="insight-panel" aria-label="מידע על השיחה">
      <section class="insight-card">
        <span class="eyebrow">עלות השיחה</span>
        <div id="conversationCost" class="cost-value">₪0.0000</div>
        <p class="cost-caption">סכום משוער של כל תשובות העוזר בשיחה הנוכחית, בשקלים.</p>
      </section>

      <section class="insight-card">
        <h3>איך המענה נבנה</h3>
        <div class="setting">
          <div class="setting-title">
            <span>מילון דרך</span>
            <span class="setting-status"><span class="mini-dot"></span> קנוני</span>
          </div>
          <p>נשלפים רק המושגים וההקשרים הרלוונטיים לשאלה הנוכחית.</p>
        </div>
        <div class="setting">
          <div class="setting-title">
            <span>רצף השיחה</span>
            <span class="setting-status"><span class="mini-dot"></span> פעיל</span>
          </div>
          <p>עדכונים קודמים מאפשרים למענה להתייחס להתקדמות לאורך זמן.</p>
        </div>
        <div class="setting">
          <div class="setting-title">
            <span>שיקול דעת</span>
            <span class="setting-status"><span class="mini-dot"></span> אנושי</span>
          </div>
          <p>המענה הוא כלי חשיבה על השיטה, ואינו מחליף אחריות מקצועית.</p>
        </div>
      </section>

      <section class="insight-card boundary-card">
        <div class="boundary-mark" aria-hidden="true">ד</div>
        <h3>גבולות המרחב</h3>
        <p class="insight-copy">המערכת המקומית שומרת את השיחות במחשב לצורך רצף עבודה. אין להשתמש בה כעת עם מידע מזהה או כתיעוד רפואי.</p>
      </section>
    </aside>
  </main>


  <div id="intakeModal" class="intake-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="intakeTitle">
    <div class="intake-modal">
      <h2 id="intakeTitle">הזנת חומרים למערכת</h2>
      
      <div class="intake-tabs">
        <button type="button" class="intake-tab active" data-tab="file">העלאת קבצים</button>
        <button type="button" class="intake-tab" data-tab="text">הדבקת טקסט</button>
      </div>

      <div id="intakeTabFile" class="intake-tab-content active">
        <div id="intakeDropZone" class="drop-zone">
          <span style="font-size: 2rem; color: var(--clay);">📄</span>
          <span>גרור קבצים לכאן או לחץ לבחירה</span>
          <small style="color: var(--muted);">PDF, Word, טקסט</small>
          <input type="file" id="intakeFileInput" multiple accept=".pdf,.docx,.doc,.txt">
        </div>
        <div id="intakeFileList" class="file-list"></div>
      </div>

      <div id="intakeTabText" class="intake-tab-content">
        <label for="intakeContent">תוכן החומר:</label>
        <textarea id="intakeContent" placeholder="הדבק כאן את תוכן המסמך או הסיכום..."></textarea>
      </div>
      
      <label>סיווג רמת החומר (סדר):</label>
      <div class="intake-options">
        <label class="intake-option">
          <input type="radio" name="intakeOrder" value="1" checked>
          <div>
            <strong>סדר ראשון: חומר מקורי של השיטה</strong>
            <small>יעבור ניתוח AI עמוק לבניית רשת המושגים.</small>
          </div>
        </label>
        <label class="intake-option">
          <input type="radio" name="intakeOrder" value="2">
          <div>
            <strong>סדר שני: פרשנות וסיכומי סטודנטים</strong>
            <small>יקבל סמכות משנית וירחיב על מושגי המקור מבלי לדרוס אותם.</small>
          </div>
        </label>
        <label class="intake-option">
          <input type="radio" name="intakeOrder" value="3">
          <div>
            <strong>סדר שלישי: מידע רקע כללי</strong>
            <small>ישמש כהקשר נוסף בלבד ולא כידע קנוני.</small>
          </div>
        </label>
      </div>
      
      <div class="intake-actions">
        <button id="closeIntakeModalButton" class="quiet-button" type="button">ביטול</button>
        <button id="submitIntakeButton" class="primary-button" type="button">הזן למערכת</button>
      </div>
    </div>
  </div>

  <div id="toast"
 class="toast hidden" role="status" aria-live="polite"></div>

  <script>
    (() => {
      "use strict";

      const state = {
        therapists: [],
        activeTherapistId: "",
        patients: [],
        activePatientId: "",
        activeConversationId: "",
        activeConversation: null,
        aiAvailable: true,
        busy: false
      };

      const byId = (id) => document.getElementById(id);
      const therapistSelect = byId("therapistSelect");
      const editTherapistButton = byId("editTherapistButton");
      const addTherapistForm = byId("addTherapistForm");
      const showAddTherapistButton = byId("showAddTherapistButton");
      const newTherapistName = byId("newTherapistName");
      const addTherapistButton = byId("addTherapistButton");
      const patientList = byId("patientList");
      const timeline = byId("messageTimeline");
      const questionInput = byId("question");
      const askButton = byId("askButton");
      const useAi = byId("useAi");
      const aiModel = byId("aiModel");
      const privacyCheck = byId("confirmNoPatientData");
      const addPatientForm = byId("addPatientForm");
      const showAddPatientButton = byId("showAddPatientButton");
      const newPatientName = byId("newPatientName");

      function safeArray(value) {
        return Array.isArray(value) ? value : [];
      }

      function pickObject(payload, key) {
        if (payload && typeof payload[key] === "object" && !Array.isArray(payload[key])) {
          return payload[key];
        }
        return payload && typeof payload === "object" ? payload : {};
      }

      async function api(url, options = {}) {
        const response = await fetch(url, {
          cache: "no-store",
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
          }
        });
        let data = {};
        try {
          data = await response.json();
        } catch {
          data = {};
        }
        if (!response.ok) {
          if (data && data.status === "conversation_or_patient_not_found") {
            state.activeConversationId = null;
            state.activePatientId = null;
            saveState();
            window.location.reload();
            return;
          }
          const error = new Error(data.answer_text || data.message || "לא ניתן להשלים את הפעולה.");
          error.payload = data;
          throw error;
        }
        return data;
      }

      function formatDate(value) {
        if (!value) return "";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "";
        return new Intl.DateTimeFormat("he-IL", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit"
        }).format(date);
      }

      function formatDuration(milliseconds) {
        const number = Number(milliseconds || 0);
        if (!Number.isFinite(number) || number <= 0) return "פחות משנייה";
        if (number < 1000) return `${Math.round(number)} אלפיות שנייה`;
        if (number < 10000) return `${(number / 1000).toFixed(1)} שנ׳`;
        return `${Math.round(number / 1000)} שנ׳`;
      }

      function formatShekels(value) {
        const amount = Number(value || 0);
        if (!Number.isFinite(amount) || amount <= 0) return "₪0.0000";
        if (amount < 1) return `₪${amount.toFixed(4)}`;
        return `₪${amount.toFixed(2)}`;
      }

      function metadataFor(message) {
        const metadata = message && typeof message.metadata === "object"
          ? message.metadata : {};
        const generation = metadata && typeof metadata.generation === "object"
          ? metadata.generation : {};
        return {
          ...metadata,
          ...generation,
          response_type:
            metadata.response_type ||
            message.response_type ||
            generation.response_type ||
            ""
        };
      }

      function costFor(message) {
        if (!message || message.role === "user") return 0;
        const metadata = metadataFor(message);
        const value =
          metadata.cost_ils ??
          metadata.estimated_cost_ils ??
          metadata.cost_nis ??
          0;
        const cost = Number(value);
        return Number.isFinite(cost) ? cost : 0;
      }

      function showToast(message) {
        const toast = byId("toast");
        toast.textContent = message;
        toast.classList.remove("hidden");
        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 3200);
      }

      function showComposerError(message) {
        const banner = byId("composerError");
        banner.textContent = message;
        banner.classList.remove("hidden");
      }

      function clearComposerError() {
        byId("composerError").classList.add("hidden");
        byId("composerError").textContent = "";
      }

      function setBusy(busy) {
        state.busy = busy;
        askButton.disabled = busy;
        addTherapistButton.disabled = busy;
        byId("addPatientButton").disabled = busy;
        askButton.querySelector("span").textContent = busy ? "בונה מענה…" : "שליחה";
      }
      
      function showLoadingMessage() {
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "message system";
        loadingDiv.id = "temporaryLoadingMessage";
        loadingDiv.innerHTML = `
          <div class="message-meta">מערכת</div>
          <div class="message-body" style="text-align: right; direction: rtl;">
            <div class="typing-indicator" style="display: inline-block;">
              <span></span><span></span><span></span>
            </div>
            <span id="loadingProgressText" style="margin-right: 8px; font-size: 0.9em; color: var(--muted);">הסוכן מנתח את הבקשה ומעבד את התשובה...</span>
          </div>
        `;
        timeline.append(loadingDiv);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      function removeLoadingMessage() {
        const el = byId("temporaryLoadingMessage");
        if (el) el.remove();
      }
      
      function appendOptimisticMessage(content) {
        const msgDiv = document.createElement("div");
        msgDiv.className = "message user optimistic";
        msgDiv.id = "temporaryUserMessage";
        msgDiv.innerHTML = `
          <div class="message-meta">אני</div>
          <div class="message-body">${escapeHtml(content)}</div>
        `;
        timeline.append(msgDiv);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      function removeOptimisticMessage() {
        const el = byId("temporaryUserMessage");
        if (el) el.remove();
      }

      async function renderPatients() {
        patientList.replaceChildren();
        if (!state.patients.length) {
          patientList.innerHTML = '<div class="empty-state">עדיין אין מטופלים.</div>';
          state.activePatientId = "";
          return;
        }

        for (const patient of state.patients) {
          const patientId = String(patient.id || "");
          
          const item = document.createElement("div");
          item.className = "patient-item";

          const header = document.createElement("div");
          header.className = "patient-header";
          
          const headerText = document.createElement("span");
          headerText.textContent = String(patient.name || "מטופל אנונימי");
          headerText.style.flex = "1";
          
          const editPatientBtn = document.createElement("button");
          editPatientBtn.className = "quiet-button";
          editPatientBtn.innerHTML = "✏️";
          editPatientBtn.style.padding = "2px 6px";
          editPatientBtn.style.fontSize = "0.9rem";
          editPatientBtn.title = "עריכת שם מטופל";
          editPatientBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const newName = prompt("הכנס שם חדש למטופל:", patient.name);
            if (newName && newName.trim() !== "" && newName !== patient.name) {
              setBusy(true);
              try {
                await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patientId)}`, {
                  method: "PUT",
                  body: JSON.stringify({name: newName.trim()})
                });
                await loadWorkspace();
              } catch(err) {
                showToast(err.message);
              } finally {
                setBusy(false);
              }
            }
          });
          
          header.append(headerText, editPatientBtn);
          
          const convContainer = document.createElement("div");
          convContainer.className = "patient-conversations";
          
          // New conversation button specifically for this patient
          const newConvBtn = document.createElement("button");
          newConvBtn.className = "conversation-item";
          newConvBtn.style.color = "var(--olive)";
          newConvBtn.innerHTML = "<strong>+ שיחה חדשה</strong>";
          newConvBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            await createConversation(patientId);
          });
          convContainer.append(newConvBtn);

          // Render the conversations dynamically when opened
          const patientConversations = patient.conversations || [];
          for (const conv of patientConversations) {
            const convBtn = document.createElement("button");
            convBtn.type = "button";
            convBtn.className = "conversation-item";
            convBtn.style.display = "flex";
            convBtn.style.justifyContent = "space-between";
            convBtn.style.alignItems = "center";
            convBtn.style.textAlign = "right";

            if (String(conv.id) === state.activeConversationId && patientId === state.activePatientId) {
              convBtn.classList.add("active");
              header.classList.add("expanded");
              convContainer.classList.add("open");
            }
            
            const infoDiv = document.createElement("div");
            infoDiv.style.flex = "1";
            
            const title = document.createElement("strong");
            title.textContent = String(conv.title || "שיחה");
            const meta = document.createElement("span");
            const count = Number(conv.message_count ?? safeArray(conv.messages).length);
            const date = formatDate(conv.updated_at);
            meta.textContent = `${count} הודעות${date ? ` · ${date}` : ""}`;
            meta.style.display = "block";
            
            infoDiv.append(title, meta);

            const deleteConvBtn = document.createElement("div");
            deleteConvBtn.innerHTML = "🗑️";
            deleteConvBtn.style.fontSize = "1.2rem";
            deleteConvBtn.style.padding = "4px";
            deleteConvBtn.style.color = "var(--danger)";
            deleteConvBtn.style.cursor = "pointer";
            deleteConvBtn.title = "מחיקת שיחה";
            
            deleteConvBtn.addEventListener("click", async (e) => {
              e.stopPropagation();
              if (confirm(`האם למחוק את השיחה "${title.textContent}"?`)) {
                setBusy(true);
                try {
                  await api(`/api/conversation?therapist_id=${encodeURIComponent(state.activeTherapistId)}&patient_id=${encodeURIComponent(patientId)}&conversation_id=${encodeURIComponent(conv.id)}`, { method: "DELETE" });
                  if (state.activeConversationId === String(conv.id)) {
                    state.activeConversationId = "";
                    window.localStorage.removeItem("derech.activeConversationId");
                    timeline.replaceChildren();
                  }
                  await updateState();
                } catch (err) {
                  alert("שגיאה במחיקת שיחה");
                } finally {
                  setBusy(false);
                }
              }
            });

            convBtn.append(infoDiv, deleteConvBtn);
            
            convBtn.addEventListener("click", (e) => {
              e.stopPropagation();
              state.activePatientId = patientId;
              window.localStorage.setItem("derech.activePatientId", patientId);
              selectConversation(patientId, String(conv.id));
            });
            convContainer.append(convBtn);
          }

          header.addEventListener("click", () => {
            const isOpen = convContainer.classList.contains("open");
            if (!isOpen) {
               // close others
               document.querySelectorAll(".patient-conversations").forEach(el => el.classList.remove("open"));
               document.querySelectorAll(".patient-header").forEach(el => el.classList.remove("expanded"));
               
               convContainer.classList.add("open");
               header.classList.add("expanded");
               state.activePatientId = patientId;
               window.localStorage.setItem("derech.activePatientId", patientId);
            } else {
               convContainer.classList.remove("open");
               header.classList.remove("expanded");
            }
          });

          item.append(header, convContainer);
          patientList.append(item);
        }
      }

      function evidenceData(message) {
        const metadata = message && typeof message.metadata === "object"
          ? message.metadata : {};
        const evidence = metadata.evidence && typeof metadata.evidence === "object"
          ? metadata.evidence : {};
        return {
          matches: safeArray(message.matches || metadata.matches || evidence.matches),
          relations: safeArray(
            message.canonical_relations ||
            metadata.canonical_relations ||
            evidence.canonical_relations ||
            evidence.relations
          ),
          sources: safeArray(
            message.approved_source_evidence ||
            metadata.approved_source_evidence ||
            evidence.approved_source_evidence
          )
        };
      }

      function evidenceList(title, items, describe) {
        const group = document.createElement("div");
        group.className = "evidence-group";
        const heading = document.createElement("strong");
        heading.textContent = title;
        group.append(heading);
        if (!items.length) {
          const empty = document.createElement("span");
          empty.textContent = "לא נשמרו פריטים להצגה.";
          group.append(empty);
          return group;
        }
        const list = document.createElement("ul");
        for (const item of items.slice(0, 24)) {
          const row = document.createElement("li");
          row.textContent = describe(item);
          list.append(row);
        }
        group.append(list);
        return group;
      }

      function buildEvidence(message) {
        const data = evidenceData(message);
        const details = document.createElement("details");
        details.className = "evidence";
        const summary = document.createElement("summary");
        summary.textContent = "פרטי הראיות והקשרים ששימשו למענה";
        const content = document.createElement("div");
        content.className = "evidence-content";
        content.append(
          evidenceList("ידע קנוני מאושר", data.matches, (item) =>
            `${item.entry_name || item.name || "מושג"}${item.card_id ? ` (${item.card_id})` : ""}`
          ),
          evidenceList("קשרים מאושרים", data.relations, (item) =>
            [
              item.source_name || item.source_label || "",
              item.relation_label || item.relation_type || "קשור אל",
              item.target_name || item.target_label || ""
            ].filter(Boolean).join(" — ")
          ),
          evidenceList("מראי־מקום מאושרים", data.sources, (item) =>
            [
              item.source_document_id || item.entry_name || "מקור שיטה",
              item.evidence_locator || "",
              item.source_authority || ""
            ].filter(Boolean).join(" — ")
          )
        );
        details.append(summary, content);
        return details;
      }

      function buildMessage(message) {
        const isAssistant = message.role === "assistant";
        const metadata = metadataFor(message);
        const isClarification =
          isAssistant &&
          ["needs_clarification", "clarification"].includes(String(metadata.response_type));
        const article = document.createElement("article");
        article.className = `message ${isAssistant ? "assistant" : "user"}`;
        if (isClarification) article.classList.add("clarification");

        const label = document.createElement("div");
        label.className = "message-label";
        const author = document.createElement("strong");
        author.textContent = isAssistant
          ? (isClarification ? "שאלת הבהרה" : "דרך")
          : "העדכון שלך";
        const time = document.createElement("span");
        time.textContent = formatDate(message.created_at);
        label.append(author, time);

        const body = document.createElement("div");
        body.className = "message-body";
        if (isClarification) {
          const ribbon = document.createElement("div");
          ribbon.className = "clarification-ribbon";
          ribbon.textContent = "נדרש עוד מידע לפני גיבוש כיוון";
          body.append(ribbon);
        }
        const content = document.createElement("div");
        content.textContent = String(message.content || message.answer_text || "");
        body.append(content);

        article.append(label, body);

        if (isAssistant) {
          const metrics = document.createElement("div");
          metrics.className = "answer-metrics";
          const cost = document.createElement("span");
          cost.className = "answer-metric cost";
          cost.textContent = `עלות ${formatShekels(costFor(message))}`;
          const duration = document.createElement("span");
          duration.className = "answer-metric";
          duration.textContent = `זמן הפקה ${formatDuration(metadata.elapsed_ms)}`;
          metrics.append(cost, duration);
          if (metadata.quality_reviewed) {
            const reviewed = document.createElement("span");
            reviewed.className = "answer-metric";
            reviewed.textContent = "עבר בקרת איכות";
            metrics.append(reviewed);
          }
          article.append(metrics, buildEvidence(message));
        }
        return article;
      }

      function renderConversation() {
        const conversation = state.activeConversation;
        if (!conversation) {
          byId("activeConversationTitle").textContent = "שיחה חדשה";
          byId("activeConversationMeta").textContent = "ההקשר נבנה בהדרגה לאורך השיחה";
          byId("conversationCost").textContent = "₪0.0000";
          timeline.innerHTML = `
            <div class="timeline-welcome">
              <h3>מתחילים מן השאלה הנכונה</h3>
              <p>כתבו שאלה על השיטה או עדכון המשך בשיחה קיימת. המערכת תאתר הקשר מצומצם מן הידע הקנוני, ואם חסר מידע מהותי היא תחזור אליכם בשאלות הבהרה.</p>
              <div class="path-line" aria-hidden="true"></div>
            </div>`;
          return;
        }

        const messages = safeArray(conversation.messages);
        byId("activeConversationTitle").textContent =
          String(conversation.title || "שיחה חדשה");
        byId("activeConversationMeta").textContent = messages.length
          ? `${messages.length} הודעות · נשמר מקומית`
          : "ההקשר נבנה בהדרגה לאורך השיחה";

        timeline.replaceChildren();
        if (!messages.length) {
          timeline.innerHTML = `
            <div class="timeline-welcome">
              <h3>השיחה מוכנה</h3>
              <p>אפשר להתחיל בשאלה, או לתאר עדכון שאינו כולל פרטים מזהים. אם חסר מידע מכריע, תופיע שאלת הבהרה לפני גיבוש האסטרטגיה.</p>
              <div class="path-line" aria-hidden="true"></div>
            </div>`;
        } else {
          for (const message of messages) timeline.append(buildMessage(message));
        }

        const total = messages.reduce((sum, message) => sum + costFor(message), 0);
        byId("conversationCost").textContent = formatShekels(total);
        requestAnimationFrame(() => {
          timeline.scrollTop = timeline.scrollHeight;
        });
      }

      async function fetchModels() {
        console.log("Fetching models...");
        try {
          const mPayload = await api("/api/models");
          console.log("Models payload:", mPayload);
          if (mPayload.models) {
            const select = byId("aiModel");
            // Keep the 'auto' option, remove others
            select.innerHTML = '<option value="auto" selected>בחירה אוטומטית (מומלץ)</option>';
            if (mPayload.models.pro) {
              const opt = document.createElement("option");
              opt.value = mPayload.models.pro.id;
              opt.textContent = `${mPayload.models.pro.name} · מעמיק`;
              select.appendChild(opt);
            }
            if (mPayload.models.fast) {
              const opt = document.createElement("option");
              opt.value = mPayload.models.fast.id;
              opt.textContent = `${mPayload.models.fast.name} · מהיר`;
              select.appendChild(opt);
            }
          }
        } catch (e) {
          console.error("Failed to load models", e);
        }
      }

      async function loadWorkspace() {
        fetchModels();
        try {
          const tPayload = await api("/api/therapists");
          state.therapists = safeArray(tPayload.therapists || tPayload);
        } catch (e) {
          state.therapists = [];
        }

        const savedTherapistId = window.localStorage.getItem("derech.activeTherapistId") || "";
        state.activeTherapistId = state.therapists.some((t) => String(t.id) === savedTherapistId)
          ? savedTherapistId
          : String(state.therapists[0]?.id || "");

        therapistSelect.replaceChildren();
        if (state.therapists.length) {
          for (const t of state.therapists) {
            const opt = document.createElement("option");
            opt.value = t.id;
            opt.textContent = t.name;
            therapistSelect.append(opt);
          }
          therapistSelect.value = state.activeTherapistId;
          therapistSelect.disabled = false;
        } else {
          const opt = document.createElement("option");
          opt.textContent = "אין מטפלים";
          therapistSelect.append(opt);
          therapistSelect.disabled = true;
          state.patients = [];
          renderPatients();
          return;
        }

        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients`);
          state.patients = safeArray(payload.patients || payload);
        } catch (e) {
          state.patients = [];
        }

        // For each patient, load their conversations so we can render the accordion fully
        for (const patient of state.patients) {
          try {
            const convPayload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patient.id)}/conversations`);
            patient.conversations = safeArray(convPayload.conversations || convPayload);
          } catch (e) {
            patient.conversations = [];
          }
        }

        const savedPatientId = window.localStorage.getItem("derech.activePatientId") || "";
        state.activePatientId = state.patients.some((p) => String(p.id) === savedPatientId)
          ? savedPatientId
          : String(state.patients[0]?.id || "");

        // If we have a patient, we also try to restore their active conversation
        if (state.activePatientId) {
          const savedConversationId = window.localStorage.getItem(`derech.activeConversationId.${state.activePatientId}`) || "";
          state.activeConversationId = savedConversationId;
          if (state.activeConversationId) {
            await loadConversation(state.activePatientId, state.activeConversationId);
          }
        }
        
        renderPatients();
        if (!state.activeConversationId) renderConversation();
      }

      async function loadConversation(patientId, conversationId) {
        if (!state.activeTherapistId || !patientId || !conversationId) return;
        try {
          const payload = await api(`/api/conversation?therapist_id=${encodeURIComponent(state.activeTherapistId)}&patient_id=${encodeURIComponent(patientId)}&conversation_id=${encodeURIComponent(conversationId)}`);
          if (payload.conversation) {
             state.activeConversation = payload.conversation;
             state.activeConversationId = String(conversationId);
             window.localStorage.setItem(`derech.activeConversationId.${patientId}`, state.activeConversationId);
             renderPatients();
             renderConversation();
          }
        } catch (e) {
          console.error(e);
        }
      }

      async function selectConversation(patientId, conversationId) {
        if (state.busy || (conversationId === state.activeConversationId && patientId === state.activePatientId)) return;
        clearComposerError();
        try {
          await loadConversation(patientId, conversationId);
        } catch (error) {
          showToast(error.message);
        }
      }

      async function createPatient() {
        const name = newPatientName.value.trim();
        if (!name || state.busy) {
          if (!name) showToast("יש להזין שם למטופל החדש.");
          return;
        }
        setBusy(true);
        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients`, {
            method: "POST",
            body: JSON.stringify({name})
          });
          const patient = pickObject(payload, "patient");
          newPatientName.value = "";
          addPatientForm.classList.add("hidden");
          state.activePatientId = String(patient.id || "");
          window.localStorage.setItem("derech.activePatientId", state.activePatientId);
          await loadWorkspace();
          showToast("המטופל נוסף בהצלחה.");
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function createConversation(patientId) {
        if (!patientId) {
          showToast("יש להוסיף או לבחור מטופל לפני פתיחת שיחה.");
          return;
        }
        if (state.busy) return;
        setBusy(true);
        clearComposerError();
        try {
          const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(patientId)}/conversations`, {
            method: "POST",
            body: JSON.stringify({
              title: "שיחה חדשה"
            })
          });
          const conversation = pickObject(payload, "conversation");
          const conversationId = String(conversation.id || "");
          state.activePatientId = patientId;
          await loadWorkspace();
          await selectConversation(patientId, conversationId);
          questionInput.focus();
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      async function ensureConversation() {
        if (state.activeConversationId) return state.activeConversationId;
        const payload = await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}/patients/${encodeURIComponent(state.activePatientId)}/conversations`, {
          method: "POST",
          body: JSON.stringify({
            title: "שיחה חדשה"
          })
        });
        const conversation = pickObject(payload, "conversation");
        const conversationId = String(conversation.id || "");
        state.activeConversationId = conversationId;
        await loadWorkspace();
        return conversationId;
      }

      async function ask() {
        const question = questionInput.value.trim();
        clearComposerError();
        if (state.busy) return;
        if (!state.activePatientId) {
          showComposerError("יש להוסיף או לבחור מטופל לפני שליחת שאלה.");
          return;
        }
        if (!question) {
          showComposerError("יש לכתוב שאלה או עדכון.");
          questionInput.focus();
          return;
        }
        if (!privacyCheck.checked) {
          showComposerError("יש לאשר שהטקסט אינו כולל שמות או פרטים מזהים.");
          privacyCheck.focus();
          return;
        }

        setBusy(true);
        appendOptimisticMessage(question);
        questionInput.value = "";
        showLoadingMessage();
        
        try {
          const conversationId = await ensureConversation();
          
          const res = await fetch("/api/ask", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              therapist_id: state.activeTherapistId,
              patient_id: state.activePatientId,
              conversation_id: conversationId,
              question,
              use_ai: useAi.checked,
              ai_model: aiModel.value === "auto" ? null : aiModel.value,
              auto_route: aiModel.value === "auto",
              confirmed_no_patient_data: true
            })
          });

          if (res.status === 401) {
            showAuthScreen();
            throw new Error("פג תוקף החיבור.");
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let buffer = "";
          let finalPayload = null;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            
            let newlineIndex;
            while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
              const line = buffer.slice(0, newlineIndex).trim();
              buffer = buffer.slice(newlineIndex + 1);
              if (!line) continue;
              
              try {
                const data = JSON.parse(line);
                if (data.progress) {
                  const textSpan = document.getElementById("loadingProgressText");
                  if (textSpan) {
                    textSpan.textContent = data.progress;
                  }
                } else if (data.status) {
                  finalPayload = data;
                }
              } catch (e) {
                console.error("Parse error", e);
              }
            }
          }
          
          if (!finalPayload) {
            throw new Error("לא התקבלה תשובה תקינה מהשרת.");
          }
          const payload = finalPayload;

          if (payload.status_code && payload.status_code !== 200) {
             throw new Error(payload.answer_text || "שגיאה בשרת.");
          }
          if (payload.status && !["answered", "ok"].includes(payload.status)) {
            throw new Error(payload.answer_text || "לא ניתן להשלים את המענה.");
          }
          removeOptimisticMessage();
          removeLoadingMessage();
          await loadWorkspace();
          await selectConversation(state.activePatientId, conversationId);
        } catch (error) {
          showComposerError(error.message);
          questionInput.value = question;
          removeOptimisticMessage();
          removeLoadingMessage();
        } finally {
          setBusy(false);
        }
      }

      async function checkHealth() {
        const status = byId("systemStatus");
        try {
          const data = await api("/api/health");
          state.aiAvailable = Boolean(data.ai_available);
          useAi.disabled = !state.aiAvailable;
          aiModel.disabled = !state.aiAvailable || !useAi.checked;
          if (!state.aiAvailable) useAi.checked = false;
          status.classList.toggle("ready", Boolean(data.neo4j_running));
          status.querySelector("span:last-child").textContent =
            data.neo4j_running ? "רשת הידע מחוברת" : "רשת הידע אינה זמינה";
        } catch {
          status.querySelector("span:last-child").textContent = "המנוע המקומי אינו זמין";
          useAi.disabled = true;
          aiModel.disabled = true;
        }
      }

      therapistSelect.addEventListener("change", async () => {
        state.activeTherapistId = therapistSelect.value;
        window.localStorage.setItem("derech.activeTherapistId", state.activeTherapistId);
        state.activePatientId = "";
        state.activeConversationId = "";
        await loadWorkspace();
      });

      editTherapistButton.addEventListener("click", async () => {
        if (!state.activeTherapistId || state.busy) return;
        const currentTherapist = state.therapists.find(t => String(t.id) === state.activeTherapistId);
        if (!currentTherapist) return;
        
        const newName = prompt("הכנס שם חדש למטפל:", currentTherapist.name);
        if (newName && newName.trim() !== "" && newName !== currentTherapist.name) {
          setBusy(true);
          try {
            await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}`, {
              method: "PUT",
              body: JSON.stringify({name: newName.trim()})
            });
            await loadWorkspace();
          } catch(err) {
            showToast(err.message);
          } finally {
            setBusy(false);
          }
        }
      });

      const deleteTherapistBtn = byId("deleteTherapistButton");
      if (deleteTherapistBtn) {
        deleteTherapistBtn.addEventListener("click", async () => {
          if (!state.activeTherapistId || state.busy) return;
          const currentTherapist = state.therapists.find(t => String(t.id) === state.activeTherapistId);
          if (!currentTherapist) return;
          
          if (confirm(`האם אתה בטוח שברצונך למחוק את המטפל "${currentTherapist.name}"? פעולה זו תמחק גם את כל המטופלים והשיחות המשויכים אליו.`)) {
            setBusy(true);
            try {
              await api(`/api/therapists/${encodeURIComponent(state.activeTherapistId)}`, {
                method: "DELETE"
              });
              state.activeTherapistId = "";
              window.localStorage.removeItem("derech.activeTherapistId");
              state.activePatientId = "";
              state.activeConversationId = "";
              await loadWorkspace();
            } catch(err) {
              showToast(err.message);
            } finally {
              setBusy(false);
            }
          }
        });
      }

      showAddTherapistButton.addEventListener("click", () => {
        addTherapistForm.classList.toggle("hidden");
        if (!addTherapistForm.classList.contains("hidden")) {
          newTherapistName.focus();
        }
      });

      async function createTherapist() {
        const name = newTherapistName.value.trim();
        if (!name || state.busy) {
          if (!name) showToast("יש להזין שם למטפל החדש.");
          return;
        }
        setBusy(true);
        try {
          const payload = await api("/api/therapists", {
            method: "POST",
            body: JSON.stringify({name})
          });
          const therapist = pickObject(payload, "therapist");
          newTherapistName.value = "";
          addTherapistForm.classList.add("hidden");
          state.activeTherapistId = String(therapist.id || "");
          window.localStorage.setItem("derech.activeTherapistId", state.activeTherapistId);
          await loadWorkspace();
          showToast("המטפל נוסף בהצלחה.");
        } catch (error) {
          showToast(error.message);
        } finally {
          setBusy(false);
        }
      }

      addTherapistButton.addEventListener("click", createTherapist);
      newTherapistName.addEventListener("keydown", (event) => {
        if (event.key === "Enter") createTherapist();
      });

      showAddPatientButton.addEventListener("click", () => {
        addPatientForm.classList.toggle("hidden");
        if (!addPatientForm.classList.contains("hidden")) {
          newPatientName.focus();
        }
      });
      
      byId("addPatientButton").addEventListener("click", createPatient);
      newPatientName.addEventListener("keydown", (event) => {
        if (event.key === "Enter") createPatient();
      });
      askButton.addEventListener("click", ask);
      questionInput.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") ask();
      });
      useAi.addEventListener("change", () => {
        aiModel.disabled = !state.aiAvailable || !useAi.checked;
      });

      Promise.allSettled([checkHealth(), loadWorkspace()]).then((results) => {
        const workspaceResult = results[1];
        if (workspaceResult.status === "rejected") {
          showToast("לא ניתן לטעון את מרחב העבודה המקומי.");
        }
      });

      // Intake logic
      const intakeModal = byId("intakeModal");
      const showIntakeModalButton = byId("showIntakeModalButton");
      const closeIntakeModalButton = byId("closeIntakeModalButton");
      const submitIntakeButton = byId("submitIntakeButton");
      const intakeContent = byId("intakeContent");

      showIntakeModalButton.addEventListener("click", () => {
        intakeModal.classList.add("open");
        intakeContent.focus();
      });

      closeIntakeModalButton.addEventListener("click", () => {
        intakeModal.classList.remove("open");
      });
      
      intakeModal.addEventListener("click", (e) => {
        if (e.target === intakeModal) {
          intakeModal.classList.remove("open");
        }
      });

      // Intake Tabs Logic
      const intakeTabs = document.querySelectorAll('.intake-tab');
      const intakeTabContents = document.querySelectorAll('.intake-tab-content');
      let activeIntakeTab = 'file';

      intakeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          intakeTabs.forEach(t => t.classList.remove('active'));
          intakeTabContents.forEach(c => c.classList.remove('active'));
          
          tab.classList.add('active');
          activeIntakeTab = tab.dataset.tab;
          
          if (activeIntakeTab === 'file') {
            byId('intakeTabFile').classList.add('active');
          } else {
            byId('intakeTabText').classList.add('active');
          }
        });
      });

      // File Drag & Drop Logic
      const dropZone = byId('intakeDropZone');
      const fileInput = byId('intakeFileInput');
      const fileListEl = byId('intakeFileList');
      let intakeFiles = [];

      function renderIntakeFiles() {
        fileListEl.innerHTML = '';
        intakeFiles.forEach((file, index) => {
          const item = document.createElement('div');
          item.className = 'file-item';
          const nameSpan = document.createElement('span');
          nameSpan.textContent = file.name;
          const removeBtn = document.createElement('button');
          removeBtn.type = 'button';
          removeBtn.textContent = '×';
          removeBtn.addEventListener('click', () => {
            intakeFiles.splice(index, 1);
            renderIntakeFiles();
          });
          item.append(nameSpan, removeBtn);
          fileListEl.append(item);
        });
      }

      dropZone.addEventListener('click', () => fileInput.click());
      
      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      });
      dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      });
      async function processDropItems(items) {
        const promises = [];
        
        async function traverseFileTree(item, path) {
          path = path || "";
          if (item.isFile) {
            promises.push(new Promise((resolve) => {
              item.file(file => {
                const ext = file.name.split('.').pop().toLowerCase();
                if (['pdf', 'doc', 'docx', 'txt'].includes(ext)) {
                  intakeFiles.push(file);
                }
                resolve();
              });
            }));
          } else if (item.isDirectory) {
            const dirReader = item.createReader();
            const readEntries = () => new Promise((resolve) => {
              dirReader.readEntries(entries => {
                if (entries.length === 0) resolve([]);
                else readEntries().then(more => resolve(entries.concat(more)));
              });
            });
            const entries = await readEntries();
            for (let i = 0; i < entries.length; i++) {
              await traverseFileTree(entries[i], path + item.name + "/");
            }
          }
        }

        for (let i = 0; i < items.length; i++) {
          const item = items[i].webkitGetAsEntry();
          if (item) {
            await traverseFileTree(item);
          }
        }
        
        await Promise.all(promises);
        renderIntakeFiles();
      }

      dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.items) {
          setBusy(true);
          await processDropItems(e.dataTransfer.items);
          setBusy(false);
        } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          intakeFiles.push(...Array.from(e.dataTransfer.files).filter(f => ['pdf', 'doc', 'docx', 'txt'].includes(f.name.split('.').pop().toLowerCase())));
          renderIntakeFiles();
        }
      });
      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          intakeFiles.push(...Array.from(e.target.files));
          renderIntakeFiles();
        }
        fileInput.value = ''; // reset
      });

      submitIntakeButton.addEventListener("click", async () => {
        const order = document.querySelector('input[name="intakeOrder"]:checked').value;
        
        if (activeIntakeTab === 'file' && intakeFiles.length === 0) {
          showToast("נא לבחור קבצים לפני השליחה.");
          return;
        }
        if (activeIntakeTab === 'text' && !intakeContent.value.trim()) {
          showToast("נא להזין תוכן לפני השליחה.");
          return;
        }

        setBusy(true);
        submitIntakeButton.disabled = true;
        submitIntakeButton.textContent = "שולח...";
        
        try {
          if (activeIntakeTab === 'file') {
            const formData = new FormData();
            intakeFiles.forEach(f => formData.append('files', f));
            formData.append('order', order);
            
            const response = await fetch("/api/intake/upload", {
              method: "POST",
              body: formData
            });
            if (!response.ok) {
              const err = await response.json().catch(() => ({}));
              throw new Error(err.message || "שגיאה בהעלאת קבצים");
            }
            showToast("הקבצים הועלו בהצלחה.");
            intakeFiles = [];
            renderIntakeFiles();
            intakeModal.classList.remove("open");
            loadInboxFiles();
          } else {
            const text = intakeContent.value.trim();
            await api("/api/intake", {
              method: "POST",
              body: JSON.stringify({ content: text, order: parseInt(order, 10) })
            });
            showToast("החומר נקלט בהצלחה בתיקיית המערכת (Inbox) וימתין לעיבוד.");
            intakeContent.value = "";
            intakeModal.classList.remove("open");
            loadInboxFiles();
          }
        } catch(err) {
          showToast("שגיאה בהזנת החומר: " + err.message);
        } finally {
          setBusy(false);
          submitIntakeButton.disabled = false;
          submitIntakeButton.textContent = "הזן למערכת";
        }
      });

      // Inbox Section Logic
      const inboxFileListEl = byId('inboxFileList');
      const submitInboxButton = byId('submitInboxButton');
      const refreshInboxButton = byId('refreshInboxButton');
      let currentInboxFiles = [];

      async function loadInboxFiles() {
        try {
          const res = await fetch("/api/inbox/files");
          if (!res.ok) return;
          const data = await res.json();
          currentInboxFiles = data.files || [];
          renderInboxFiles();
        } catch(e) {
          console.error(e);
        }
      }

      function renderInboxFiles() {
        inboxFileListEl.innerHTML = '';
        if (currentInboxFiles.length === 0) {
          inboxFileListEl.innerHTML = '<div class="empty-state">אין קבצים ממתינים בקלט.</div>';
          submitInboxButton.classList.add('hidden');
          return;
        }
        submitInboxButton.classList.remove('hidden');
        currentInboxFiles.forEach((filename, idx) => {
          const item = document.createElement('div');
          item.className = 'inbox-file-item';
          
          const label = document.createElement('label');
          const cb = document.createElement('input');
          cb.type = 'checkbox';
          cb.checked = true;
          cb.dataset.filename = filename;
          
          const nameSpan = document.createElement('span');
          nameSpan.textContent = filename;
          nameSpan.style.overflow = 'hidden';
          nameSpan.style.textOverflow = 'ellipsis';
          nameSpan.style.whiteSpace = 'nowrap';
          
          label.append(cb, nameSpan);
          
          const select = document.createElement('select');
          select.dataset.idx = idx;
          select.innerHTML = `
            <option value="1">סדר 1</option>
            <option value="2">סדר 2</option>
            <option value="3">סדר 3</option>
          `;
          
          item.append(label, select);
          inboxFileListEl.append(item);
        });
      }

      refreshInboxButton.addEventListener('click', (e) => {
        e.stopPropagation();
        loadInboxFiles();
      });

      submitInboxButton.addEventListener('click', async () => {
        const checkboxes = inboxFileListEl.querySelectorAll('input[type="checkbox"]:checked');
        if (checkboxes.length === 0) {
          showToast("לא נבחרו קבצים להזנה.");
          return;
        }
        
        const filesToProcess = Array.from(checkboxes).map(cb => {
          const filename = cb.dataset.filename;
          const itemEl = cb.closest('.inbox-file-item');
          const selectEl = itemEl.querySelector('select');
          return { filename, order: parseInt(selectEl.value, 10) };
        });
        
        setBusy(true);
        submitInboxButton.disabled = true;
        submitInboxButton.textContent = "מזין...";
        
        try {
          await api("/api/inbox/process", {
            method: "POST",
            body: JSON.stringify({ files: filesToProcess })
          });
          showToast("הקבצים נשלחו לעיבוד בהצלחה.");
          loadInboxFiles();
        } catch(err) {
          showToast("שגיאה בעיבוד קבצי קלט: " + err.message);
        } finally {
          setBusy(false);
          submitInboxButton.disabled = false;
          submitInboxButton.textContent = "הזן נבחרים";
        }
      });
      
      // Load initial inbox state
      loadInboxFiles();

      // Progress polling logic
      const inboxProgressEl = byId('inboxProgress');
      const inboxProgressTextEl = byId('inboxProgressText');
      const inboxProgressBarEl = byId('inboxProgressBar');
      
      async function pollInboxProgress() {
        try {
          const res = await fetch("/api/inbox/progress");
          if (res.ok) {
            const data = await res.json();
            if (data.status === 'processing' || data.status === 'starting') {
              inboxProgressEl.classList.remove('hidden');
              inboxProgressTextEl.textContent = `${data.processed} / ${data.total}`;
              const pct = data.total > 0 ? (data.processed / data.total) * 100 : 0;
              inboxProgressBarEl.style.width = `${pct}%`;
            } else {
              inboxProgressEl.classList.add('hidden');
            }
          } else {
            inboxProgressEl.classList.add('hidden');
          }
        } catch(e) {
          inboxProgressEl.classList.add('hidden');
        }
        setTimeout(pollInboxProgress, 2000);
      }
      
      // Start polling
      pollInboxProgress();

    })();

  
  </script>
</body>
</html>
"""
