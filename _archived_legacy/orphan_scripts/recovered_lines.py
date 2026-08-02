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

    select, input[type="text"] {
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

    select {
      cursor: pointer;
      appearance: none;
      background-image:
        linear-gradient(45deg, transparent 50%, var(--olive-dark) 50%),
        linear-gradient(135deg, var(--olive-dark) 50%, transparent 50%);
      background-position:
        13px calc(50% - 2px),
        8px calc(50% - 2px);
      background-size: 5px 5px, 5px 5px;
      background-repeat: no-repeat;
      padding-left: 28px;
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
