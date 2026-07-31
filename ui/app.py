import base64
import json
import time
import hashlib
import hmac
import html
import os
import re
import secrets
import uuid
from datetime import date, timedelta
from urllib.parse import quote_plus, urlparse

import psycopg2
import requests
import streamlit as st
import streamlit.components.v1 as components



RASA_BASE_URL = os.getenv("RASA_BASE_URL", "http://localhost:5005").rstrip("/")
RASA_API_URL = f"{RASA_BASE_URL}/webhooks/rest/webhook"

AUTH_COOKIE_NAME = "eco_travel_auth"
AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 3
AUTH_COOKIE_SECRET = os.getenv(
    "AUTH_COOKIE_SECRET",
    "",
).strip()


st.set_page_config(
    page_title="Eco-Travel Advisor",
    page_icon="🌿",
    layout="wide",
)


st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400..900&display=swap');

:root {
    --bg: #f4f9f5;
    --sidebar: #ecf4ee;
    --surface: #ffffff;
    --surface-raised: #ffffff;
    --surface-soft: #e8f2ea;
    --border: rgba(21, 71, 43, 0.14);
    --border-strong: rgba(21, 71, 43, 0.26);
    --text: #16281d;
    --muted: #5c7264;
    --brand: #15803d;
    --brand-strong: #22c55e;
    --brand-soft: rgba(34, 197, 94, 0.12);
    --sand: #a3823c;
    --amber: #b45309;
    --danger: #dc2626;
    --radius: 16px;
    --radius-small: 12px;
}

html,
body,
[data-testid="stAppViewContainer"] {
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(
            circle at 50% -20%,
            rgba(22, 163, 74, 0.10),
            transparent 38%
        ),
        var(--bg);
    color: var(--text);
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--border);
}
.chat-row {
    display: flex;
    gap: 12px;
    margin: 18px 0;
    align-items: flex-start;
}

.avatar-bot,
.avatar-user {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    flex-shrink: 0;
}

.avatar-bot {
    background:
        linear-gradient(
            145deg,
            #8be8b8,
            var(--brand-strong)
        );
    color: #0c3b22;
    border: 1px solid rgba(255, 255, 255, 0.55);
    box-shadow: 0 8px 22px rgba(22, 163, 74, 0.22);
}

.avatar-user {
    background: var(--surface-soft);
    color: var(--text);
    border: 1px solid var(--border-strong);
}

.message-box {
    padding: 14px 16px;
    border-radius: var(--radius-small);
    background: var(--surface-raised);
    color: var(--text);
    max-width: 920px;
    line-height: 1.55;
}

.summary-box {
    padding: 18px;
    border-radius: var(--radius-small);
    background: var(--surface-raised);
    border: 1px solid var(--border);
    color: var(--text);
    max-width: 1050px;
    line-height: 1.6;
}

.summary-title {
    font-size: 1.08rem;
    font-weight: 900;
    color: var(--amber);
    margin-bottom: 12px;
}

.plan-route {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.2rem;
    font-weight: 900;
    color: var(--text);
    margin-bottom: 4px;
}

.plan-route-arrow {
    color: var(--brand);
    font-weight: 400;
}

.plan-subtitle {
    color: var(--muted);
    font-size: 0.88rem;
    margin-bottom: 16px;
}

.plan-section-label {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.72rem;
    font-weight: 800;
    color: var(--muted);
    margin: 18px 0 8px 0;
}

.plan-total-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 16px;
    padding: 12px 14px;
    border-radius: var(--radius-small);
    background: var(--brand-soft);
}

.plan-total-row.over-budget {
    background: rgba(239, 125, 125, 0.14);
}

.plan-total-amount {
    font-size: 1.15rem;
    font-weight: 900;
    color: var(--text);
}

.plan-total-badge {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    background: var(--brand-strong);
    color: #0c3b22;
}

.plan-total-badge.over-budget {
    background: var(--danger);
    color: #ffffff;
}

.plan-question {
    margin-top: 18px;
    color: var(--muted);
    font-style: italic;
}

.plan-highlights-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 14px 0 0;
}

.plan-highlight-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(21, 71, 43, 0.03);
}

.plan-highlight-card.carbon {
    border-color: rgba(22, 163, 74, 0.28);
    background: rgba(22, 163, 74, 0.055);
}

.plan-highlight-card.hotel {
    grid-column: 1 / -1;
    border-color: rgba(247, 195, 95, 0.26);
    background: rgba(247, 195, 95, 0.045);
}

.plan-highlight-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    flex: 0 0 auto;
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    background: var(--surface-soft);
    font-size: 1.05rem;
}

.plan-highlight-copy {
    min-width: 0;
}

.plan-highlight-label {
    margin-bottom: 2px;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}

.plan-highlight-value {
    color: var(--text);
    font-size: 1.02rem;
    font-weight: 900;
    overflow-wrap: anywhere;
}

.plan-highlight-subvalue {
    margin-top: 2px;
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.plan-facts-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 14px;
}

.plan-fact-card.wide {
    grid-column: 1 / -1;
}

/* Journey chain: origin, each leg's vehicle, and any transfer port. */
.journey-chain {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 2px;
    margin: 4px 0 10px;
}

.journey-stop {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 7px 12px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface);
}

.journey-flag {
    font-size: 1.05rem;
    line-height: 1;
}

.journey-city {
    color: var(--text);
    font-size: 0.95rem;
    font-weight: 850;
    white-space: nowrap;
}

.journey-leg {
    display: inline-flex;
    align-items: center;
    min-width: 46px;
    padding: 0 4px;
}

.journey-leg::before,
.journey-leg::after {
    content: "";
    flex: 1;
    height: 2px;
    border-radius: 2px;
    background: repeating-linear-gradient(
        90deg,
        rgba(22, 163, 74, 0.55) 0 5px,
        transparent 5px 9px
    );
}

.journey-leg-icon {
    padding: 0 4px;
    font-size: 1.05rem;
    line-height: 1;
}

@media (max-width: 600px) {
    .journey-leg {
        min-width: 34px;
    }

    .journey-city {
        font-size: 0.88rem;
    }
}

.plan-fact-card {
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(21, 71, 43, 0.03);
}

.plan-fact-label {
    margin-bottom: 3px;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.plan-fact-value {
    color: var(--text);
    font-size: 0.96rem;
    font-weight: 850;
    overflow-wrap: anywhere;
}

.car-route-panel {
    margin: 14px 0;
    padding: 16px;
    border: 1px solid rgba(22, 163, 74, 0.28);
    border-radius: 14px;
    background:
        linear-gradient(
            145deg,
            rgba(22, 163, 74, 0.08),
            rgba(255, 255, 255, 0.018)
        );
}

.car-route-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
}

.car-route-kicker {
    color: var(--brand);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.car-route-title {
    margin-top: 2px;
    color: var(--text);
    font-size: 1rem;
    font-weight: 900;
}

.car-route-badge {
    flex: 0 0 auto;
    padding: 5px 9px;
    border: 1px solid rgba(22, 163, 74, 0.25);
    border-radius: 999px;
    color: var(--brand);
    background: rgba(22, 163, 74, 0.08);
    font-size: 0.70rem;
    font-weight: 850;
}

.car-metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
}

.car-metric {
    min-width: 0;
    padding: 11px 12px;
    border: 1px solid var(--border);
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.75);
}

.car-metric-label {
    margin-bottom: 3px;
    color: var(--muted);
    font-size: 0.65rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.car-metric-value {
    color: var(--text);
    font-size: 0.96rem;
    font-weight: 900;
    overflow-wrap: anywhere;
}

.car-route-assumption {
    margin-top: 10px;
    color: var(--muted);
    font-size: 0.77rem;
    line-height: 1.45;
}

.ferry-route-panel {
    margin-top: 12px;
    padding: 13px;
    border: 1px solid rgba(2, 132, 199, 0.30);
    border-radius: 12px;
    background:
        linear-gradient(
            135deg,
            rgba(186, 230, 253, 0.40),
            rgba(240, 249, 255, 0.92)
        );
}

.ferry-route-label {
    margin-bottom: 10px;
    color: #0369a1;
    font-size: 0.68rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.ferry-route-flow {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: stretch;
    gap: 8px;
}

.ferry-port {
    min-width: 0;
    padding: 10px 11px;
    border: 1px solid rgba(2, 132, 199, 0.25);
    border-radius: 10px;
    background: rgba(2, 132, 199, 0.08);
}

.ferry-port-label {
    margin-bottom: 3px;
    color: var(--muted);
    font-size: 0.62rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.ferry-port-name {
    color: var(--text);
    font-size: 0.85rem;
    font-weight: 850;
    overflow-wrap: anywhere;
}

.ferry-flow-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 54px;
    color: #0284c7;
    font-size: 1.35rem;
}

.ferry-facts {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin-top: 8px;
}

.ferry-fact {
    padding: 9px 10px;
    border-radius: 9px;
    background: rgba(2, 132, 199, 0.07);
}

.ferry-fact-label {
    color: var(--muted);
    font-size: 0.62rem;
    font-weight: 800;
    text-transform: uppercase;
}

.ferry-fact-value {
    margin-top: 2px;
    color: var(--text);
    font-size: 0.82rem;
    font-weight: 850;
}

.ferry-disclosure {
    margin-top: 9px;
    color: #075985;
    font-size: 0.72rem;
    line-height: 1.45;
}

.car-route-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
}

.car-route-source {
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.4;
}

.car-route-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    min-height: 38px;
    padding: 8px 12px;
    border: 1px solid rgba(22, 163, 74, 0.34);
    border-radius: 10px;
    color: #0c3b22 !important;
    background: var(--brand-strong);
    font-size: 0.78rem;
    font-weight: 900;
    text-decoration: none !important;
    transition:
        transform 160ms ease,
        filter 160ms ease;
}

.car-route-link:hover {
    transform: translateY(-1px);
    filter: brightness(1.05);
}

div[class*="st-key-quick_reply_row"] {
    max-width: 560px;
    margin: 12px 0 12px 48px;
}

div[class*="st-key-transport_card_"] {
    max-width: 1050px;
    margin: 0 0 4px 0;
}

.section-title {
    margin: 24px 0 8px 48px;
    font-size: 1.05rem;
    font-weight: 900;
    color: var(--text);
}

.transport-card {
    padding: 16px;
    border-radius: var(--radius-small);
    margin: 12px 0 12px 48px;
    border-left: 8px solid;
    background: var(--surface-raised);
    color: var(--text);
    max-width: 1050px;
}

.transport-green {
    border-color: #22c55e;
}

.transport-amber {
    border-color: #f59e0b;
}

.transport-red {
    border-color: #ef4444;
}

.transport-title {
    font-size: 1.05rem;
    font-weight: 900;
    margin-bottom: 8px;
}

.metric-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 8px;
}

.metric {
    padding: 6px 10px;
    border-radius: 6px;
    background: var(--surface-soft);
    color: var(--text);
    font-size: 0.9rem;
}

.source-text {
    margin-top: 10px;
    color: var(--muted);
    line-height: 1.5;
}

.hotel-card {
    padding: 14px 16px;
    border-radius: var(--radius-small);
    background: var(--brand-soft);
    border: 1px solid var(--border-strong);
    color: var(--text);
    margin: 10px 0 12px 48px;
    max-width: 1050px;
    line-height: 1.55;
}

.activity-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0 18px 48px;
    max-width: 1050px;
}

.activity-pill {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--text);
    border: 1px solid var(--border-strong);
}

.handover-box {
    padding: 16px;
    border-radius: var(--radius-small);
    background: var(--surface-raised);
    border: 1px solid var(--border-strong);
    color: var(--text);
    margin: 12px 0 12px 48px;
    max-width: 1050px;
    line-height: 1.55;
}

.handover-title {
    font-weight: 900;
    color: var(--amber);
    margin-bottom: 8px;
}

.handover-status {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 6px;
    background: var(--brand-soft);
    color: var(--amber);
    font-weight: 800;
    margin-bottom: 12px;
}

.context-grid {
    display: grid;
    grid-template-columns: minmax(150px, 220px) 1fr;
    gap: 8px 16px;
}

.context-label {
    font-weight: 800;
    color: var(--amber);
}

.context-value {
    color: var(--text);
    overflow-wrap: anywhere;
}

.history-item {
    padding: 12px;
    margin-bottom: 8px;
    border-radius: var(--radius-small);
    background: var(--surface-raised);
    border: 1px solid var(--border);
    color: var(--text);
    line-height: 1.55;
    overflow-wrap: anywhere;
}

.history-speaker {
    color: var(--amber);
    font-weight: 900;
    margin-bottom: 6px;
}

.sidebar-code {
    background: var(--sidebar);
    padding: 14px;
    border-radius: var(--radius-small);
    color: var(--text);
    font-family: monospace;
    line-height: 1.6;
}

.stButton > button {
    border-radius: 8px;
    min-height: 42px;
}

*:focus-visible {
    outline: 3px solid var(--amber) !important;
    outline-offset: 3px !important;
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
    }
}

.chat-row {
    width: 100% !important;
    max-width: none !important;
    margin: 10px 0 !important;
    gap: 10px !important;
}

.chat-row.user-row {
    justify-content: flex-end !important;
    align-items: flex-start;
}

.chat-row.user-row .avatar-user {
    order: 2;
}

.chat-row.user-row .message-box {
    order: 1;
}

.message-box {
    padding: 13px 16px !important;
    border-radius: 16px !important;
    line-height: 1.55 !important;
    letter-spacing: -0.01em;
}

.message-box.bot-message {
    max-width: min(760px, 72vw) !important;
    background:
        linear-gradient(
            145deg,
            var(--surface-raised),
            var(--surface)
        ) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    box-shadow:
        0 14px 34px rgba(31, 63, 45, 0.090) !important;
}

.message-box.user-message {
    max-width: min(460px, 58vw) !important;
    background: var(--brand-soft) !important;
    border: 1px solid rgba(22, 163, 74, 0.32) !important;
    color: var(--text) !important;
    text-align: left;
    box-shadow:
        0 12px 28px rgba(31, 63, 45, 0.072) !important;
}

.avatar-bot,
.avatar-user {
    width: 34px !important;
    height: 34px !important;
    border-radius: 9px !important;
    font-size: 0.86rem !important;
}

.selection-chip-row {
    width: 100% !important;
    max-width: none !important;
    justify-content: flex-end !important;
    margin: 10px 0 !important;
}

.selection-chip {
    max-width: min(460px, 58vw);
    padding: 10px 13px !important;
}

[data-testid="stMainBlockContainer"],
.block-container {
    width: 100%;
    max-width: 1180px;
    margin: 0 auto;
    padding-left: 2rem;
    padding-right: 2rem;
}

@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

.brand-header {
    display: flex;
    align-items: center;
    gap: 18px;
    margin: 0.5rem 0 1.25rem;
}

.brand-mark {
    width: 58px;
    height: 58px;
    flex: 0 0 58px;
    display: grid;
    place-items: center;
    border-radius: 18px;
    background:
        linear-gradient(
            145deg,
            #8be8b8,
            var(--brand-strong)
        );
    color: #0c3b22;
    border: 1px solid rgba(255, 255, 255, 0.55);
    box-shadow:
        0 16px 36px rgba(22, 163, 74, 0.22);
}

.brand-mark svg {
    width: 30px;
    height: 30px;
    stroke: currentColor;
}

.brand-mark-emoji {
    font-size: 30px;
    line-height: 1;
}

.brand-eyebrow {
    margin-bottom: 4px;
    color: var(--brand);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.brand-title {
    margin: 0;
    color: var(--text);
    font-size: clamp(2rem, 4vw, 3rem);
    font-weight: 780;
    line-height: 1.05;
    letter-spacing: -0.045em;
}

.brand-subtitle {
    max-width: 720px;
    margin: 8px 0 0;
    color: var(--muted);
    font-size: 1rem;
    line-height: 1.55;
}

@media (max-width: 640px) {
    .brand-header {
        align-items: flex-start;
        gap: 14px;
    }

    .brand-mark {
        width: 48px;
        height: 48px;
        flex-basis: 48px;
        border-radius: 15px;
    }

    .brand-mark svg {
        width: 25px;
        height: 25px;
    }

    .brand-mark-emoji {
        font-size: 25px;
    }

    .brand-title {
        font-size: 1.85rem;
    }
}

.privacy-note {
    margin: 0 0 1.4rem;
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-small);
    background: rgba(22, 163, 74, 0.06);
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.5;
}

.trip-progress {
    margin: 0.25rem 0 1.5rem;
}

.trip-progress-meta {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    color: var(--muted);
    font-size: 0.82rem;
}

.trip-progress-meta strong {
    color: var(--text);
}

.trip-progress-track {
    height: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface-soft);
}

.trip-progress-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(
        90deg,
        var(--brand-strong),
        #8be8b8
    );
}

.sidebar-user-card {
    margin-bottom: 10px;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: linear-gradient(
        145deg,
        var(--surface-raised),
        var(--surface)
    );
    box-shadow: 0 12px 28px rgba(31, 63, 45, 0.081);
}

.sidebar-user-row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.sidebar-user-avatar {
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    background: linear-gradient(
        145deg,
        #8be8b8,
        var(--brand-strong)
    );
    color: #0c3b22;
    font-weight: 900;
}

.sidebar-user-copy {
    min-width: 0;
}

.sidebar-user-name,
.sidebar-user-email {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sidebar-user-name {
    color: var(--text);
    font-weight: 800;
}

.sidebar-user-email {
    margin-top: 3px;
    color: var(--muted);
    font-size: 0.78rem;
}

[data-baseweb="input"],
[data-baseweb="textarea"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    background: var(--surface) !important;
}

[data-baseweb="input"]:focus-within,
[data-baseweb="textarea"]:focus-within {
    border-color: rgba(22, 163, 74, 0.65) !important;
    box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.10);
}

[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    color: var(--text) !important;
    background: transparent !important;
}

[data-testid="stChatInput"] {
    border: 1px solid var(--border-strong);
    border-radius: 16px;
    background: var(--surface-raised);
    box-shadow: 0 14px 36px rgba(31, 63, 45, 0.108);
}

[data-baseweb="tab-list"] {
    gap: 6px;
    padding: 5px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
}

[data-baseweb="tab"] {
    height: 42px;
    border-radius: 10px;
    color: var(--muted);
    font-weight: 750;
}

[data-baseweb="tab"][aria-selected="true"] {
    background: var(--brand-soft);
    color: var(--brand);
}

[data-baseweb="tab-highlight"] {
    display: none;
}

.saved-trip-card {
    margin: 10px 0;
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
}

.saved-trip-title {
    margin-bottom: 7px;
    color: var(--brand);
    font-weight: 800;
}

.saved-trip-details {
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.55;
}

.saved-trip-details strong {
    color: var(--text);
}

/* Sidebar structure helpers */
.sidebar-gap {
    height: 6px;
}

.sidebar-section-label {
    margin: 22px 0 6px;
    padding-left: 2px;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.11em;
    text-transform: uppercase;
}

.sidebar-footnote {
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.74rem;
    line-height: 1.5;
}

/* Subtle, full-width Log out button under the user card */
[data-testid="stSidebar"]
div[class*="st-key-sidebar_logout_small"] .stButton > button,
div[class*="st-key-sidebar_logout_small"] .stButton > button {
    min-height: 38px !important;
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--muted) !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}

div[class*="st-key-sidebar_logout_small"] .stButton > button:hover {
    border-color: rgba(220, 38, 38, 0.45) !important;
    background: rgba(220, 38, 38, 0.06) !important;
    color: var(--danger) !important;
    transform: none !important;
}

/* Live trip summary rail, pinned in the right margin */
.trip-rail {
    position: fixed;
    top: 96px;
    right: 24px;
    width: 300px;
    max-height: calc(100vh - 128px);
    overflow-y: auto;
    padding: 20px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background:
        linear-gradient(
            160deg,
            #ffffff,
            #f2fbf5 60%,
            #eaf7ee 100%
        );
    box-shadow: 0 18px 40px rgba(31, 63, 45, 0.10);
    z-index: 30;
}

.trip-rail-eyebrow {
    color: var(--brand);
    font-size: 0.66rem;
    font-weight: 900;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.trip-rail-title {
    margin: 3px 0 16px;
    color: var(--text);
    font-size: 1.15rem;
    font-weight: 900;
    letter-spacing: -0.02em;
}

.trip-rail-route {
    display: grid;
    grid-template-columns: 26px 1fr;
    gap: 4px 12px;
    margin-bottom: 6px;
}

.trip-rail-pin {
    display: grid;
    place-items: center;
    font-size: 1.05rem;
    line-height: 1;
}

.trip-rail-connector {
    display: grid;
    place-items: center;
}

.trip-rail-connector span {
    width: 2px;
    height: 20px;
    border-radius: 2px;
    background:
        repeating-linear-gradient(
            180deg,
            rgba(22, 163, 74, 0.55) 0 4px,
            transparent 4px 8px
        );
}

.trip-rail-endpoint-label {
    color: var(--muted);
    font-size: 0.62rem;
    font-weight: 850;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}

.trip-rail-endpoint-value {
    color: var(--text);
    font-size: 1.02rem;
    font-weight: 850;
    line-height: 1.25;
    overflow-wrap: anywhere;
}

.trip-rail-endpoint-value.pending {
    color: #9fb3a6;
    font-weight: 750;
}

.trip-rail-divider {
    height: 1px;
    margin: 16px 0;
    background: var(--border);
}

.trip-rail-facts {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.trip-rail-fact {
    display: grid;
    grid-template-columns: 30px 1fr;
    align-items: center;
    gap: 12px;
}

.trip-rail-fact-icon {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: var(--brand-soft);
    font-size: 0.95rem;
}

.trip-rail-fact-label {
    color: var(--muted);
    font-size: 0.62rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.trip-rail-fact-value {
    color: var(--text);
    font-size: 0.92rem;
    font-weight: 800;
    overflow-wrap: anywhere;
}

.trip-rail-fact-value.pending {
    color: #9fb3a6;
    font-weight: 700;
}

.trip-rail-foot {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px dashed var(--border-strong);
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.5;
}

/* Hide the rail when the viewport is too narrow to hold it beside the chat */
@media (max-width: 1500px) {
    .trip-rail {
        display: none;
    }
}

/* Keep the main content clear of the rail on wide screens */
@media (min-width: 1501px) {
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-right: 360px !important;
    }

    [data-testid="stBottomBlockContainer"] {
        padding-right: 340px !important;
    }
}

</style>
""")

def build_postgres_config():
    database_url = os.getenv("NEON_DATABASE_URL", "").strip()

    if not database_url:
        return None

    parsed_url = urlparse(database_url)

    return {
        "dbname": parsed_url.path.lstrip("/"),
        "user": parsed_url.username,
        "password": parsed_url.password,
        "host": parsed_url.hostname,
        "port": parsed_url.port or 5432,
        "sslmode": "require",
        "connect_timeout": 5,
    }


POSTGRES_CONFIG = build_postgres_config()


def create_connection():
    try:
        return psycopg2.connect(
            **POSTGRES_CONFIG
        )

    except psycopg2.Error as error:
        print(
            "Database connection error:",
            type(error).__name__,
            error,
        )
        return None


def get_neon_connection():
    conn = create_connection()

    if not conn:
        raise RuntimeError("Could not connect to Neon database.")

    return conn


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    iterations = 200000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()

    return f"pbkdf2_sha256${iterations}${salt}${password_hash}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$")
        iterations = int(iterations)

        if algorithm != "pbkdf2_sha256":
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()

        return hmac.compare_digest(
            actual_hash,
            expected_hash,
        )

    except Exception:
        return False

def create_auth_token(user_id):
    if not AUTH_COOKIE_SECRET:
        return None

    payload = {
        "user_id": int(user_id),
        "expires_at": (
            int(time.time())
            + AUTH_COOKIE_MAX_AGE
        ),
    }

    payload_bytes = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    encoded_payload = (
        base64.urlsafe_b64encode(payload_bytes)
        .decode("utf-8")
        .rstrip("=")
    )

    signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{encoded_payload}.{signature}"


def verify_auth_token(token):
    if not token or not AUTH_COOKIE_SECRET:
        return None

    try:
        encoded_payload, received_signature = (
            token.split(".", 1)
        )

        expected_signature = hmac.new(
            AUTH_COOKIE_SECRET.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            received_signature,
            expected_signature,
        ):
            return None

        padding = "=" * (
            -len(encoded_payload) % 4
        )

        payload = json.loads(
            base64.urlsafe_b64decode(
                encoded_payload + padding
            ).decode("utf-8")
        )

        if int(payload["expires_at"]) <= int(time.time()):
            return None

        return int(payload["user_id"])

    except Exception:
        return None


def ensure_users_table():
    if not POSTGRES_CONFIG:
        st.error(
            "NEON_DATABASE_URL was not found. "
            "Add it to Colab Secrets first."
        )
        return False

    if st.session_state.get("database_schema_ready"):
        return True

    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS app_users (
                        id BIGSERIAL PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_trips (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES app_users(id) ON DELETE CASCADE,
                        selected_mode TEXT NOT NULL,
                        route TEXT,
                        trip_type TEXT,
                        travel_dates TEXT,
                        estimated_total TEXT,
                        carbon_estimate TEXT,
                        plan_summary TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)

        st.session_state.database_schema_ready = True
        return True

    except Exception as error:
        print(
            "Database setup error:",
            type(error).__name__,
            error,
        )

        st.error(
            "The database is temporarily unavailable. "
            "Please try again shortly."
        )

        return False


def create_neon_user(email, display_name, password):
    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_users (
                        email,
                        display_name,
                        password_hash
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (
                        email,
                        display_name,
                        hash_password(password),
                    ),
                )

        return True, "Account created."

    except psycopg2.errors.UniqueViolation:
        return False, "This email is already registered."

    except Exception as error:
        print(
            "Account creation error:",
            type(error).__name__,
            error,
        )

        return (
            False,
            "Account could not be created. Please try again.",
        )


def authenticate_neon_user(email, password):
    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        email,
                        display_name,
                        password_hash
                    FROM app_users
                    WHERE lower(email) = lower(%s)
                    LIMIT 1;
                    """,
                    (email,),
                )

                row = cursor.fetchone()

        if not row:
            return None

        user_id, user_email, display_name, stored_hash = row

        if not verify_password(password, stored_hash):
            return None

        return {
            "id": user_id,
            "email": user_email,
            "display_name": display_name,
        }

    except Exception as error:
        print(
            "Login database error:",
            type(error).__name__,
            error,
        )

        st.error(
            "The login service is temporarily unavailable. "
            "Please try again."
        )

        return None

def get_neon_user_by_id(user_id):
    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        email,
                        display_name
                    FROM app_users
                    WHERE id = %s
                    LIMIT 1;
                    """,
                    (user_id,),
                )

                row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "email": row[1],
            "display_name": row[2],
        }

    except Exception as error:
        print(
            "Persistent login lookup error:",
            type(error).__name__,
            error,
        )
        return None


def set_auth_cookie(token):
    components.html(
        f"""
<script>
const cookieName = {json.dumps(AUTH_COOKIE_NAME)};
const cookieValue = {json.dumps(token)};
const maxAge = {AUTH_COOKIE_MAX_AGE};

window.parent.document.cookie =
    cookieName + "=" + cookieValue
    + "; Path=/"
    + "; Max-Age=" + maxAge
    + "; SameSite=Lax"
    + "; Secure";

window.parent.location.reload();
</script>
""",
        height=0,
    )


def delete_auth_cookie():
    components.html(
        f"""
<script>
const cookieName = {json.dumps(AUTH_COOKIE_NAME)};

window.parent.document.cookie =
    cookieName
    + "=; Path=/"
    + "; Max-Age=0"
    + "; SameSite=Lax"
    + "; Secure";

window.parent.location.reload();
</script>
""",
        height=0,
    )


def restore_user_from_auth_cookie():
    try:
        token = st.context.cookies.get(
            AUTH_COOKIE_NAME
        )
    except Exception:
        return False

    user_id = verify_auth_token(token)

    if not user_id:
        return False

    user = get_neon_user_by_id(user_id)

    if not user:
        return False

    st.session_state.authenticated_user = user
    return True


def user_initials(display_name, email):
    source = display_name or email or "User"
    parts = re.findall(r"[A-Za-z0-9]+", source)

    if not parts:
        return "U"

    if len(parts) == 1:
        return parts[0][:2].upper()

    return (parts[0][0] + parts[-1][0]).upper()


def parse_selected_trip_summary(text):
    def find_value(pattern):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "selected_mode": find_value(r"Selected trip plan:\s*(.+)"),
        "route": find_value(r"Route:\s*(.+)"),
        "trip_type": find_value(r"Trip type:\s*(.+)"),
        "travel_dates": find_value(r"Dates:\s*(.+)"),
        "estimated_total": find_value(r"Estimated trip total:\s*([^,\n]+)"),
        "carbon_estimate": find_value(
            r"Transport carbon estimate:\s*([^\n]+)"
        ),
    }


def save_selected_trip_to_neon(text):
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    user_id = current_user.get("id")

    if not user_id:
        return

    if st.session_state.get("last_saved_trip_text") == text:
        return

    if not ensure_users_table():
        return

    parsed_trip = parse_selected_trip_summary(text)

    if not parsed_trip["selected_mode"]:
        return

    current_trip_record_id = st.session_state.get(
        "current_trip_record_id"
    )

    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                if current_trip_record_id:
                    cursor.execute(
                        """
                        UPDATE user_trips
                        SET
                            selected_mode = %s,
                            route = %s,
                            trip_type = %s,
                            travel_dates = %s,
                            estimated_total = %s,
                            carbon_estimate = %s,
                            plan_summary = %s
                        WHERE id = %s
                          AND user_id = %s
                        RETURNING id;
                        """,
                        (
                            parsed_trip["selected_mode"],
                            parsed_trip["route"],
                            parsed_trip["trip_type"],
                            parsed_trip["travel_dates"],
                            parsed_trip["estimated_total"],
                            parsed_trip["carbon_estimate"],
                            text,
                            current_trip_record_id,
                            user_id,
                        ),
                    )

                    updated_row = cursor.fetchone()

                    if updated_row:
                        st.session_state.last_saved_trip_text = text
                        load_user_trips.clear()
                        return

                cursor.execute(
                    """
                    INSERT INTO user_trips (
                        user_id,
                        selected_mode,
                        route,
                        trip_type,
                        travel_dates,
                        estimated_total,
                        carbon_estimate,
                        plan_summary
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        user_id,
                        parsed_trip["selected_mode"],
                        parsed_trip["route"],
                        parsed_trip["trip_type"],
                        parsed_trip["travel_dates"],
                        parsed_trip["estimated_total"],
                        parsed_trip["carbon_estimate"],
                        text,
                    ),
                )

                inserted_row = cursor.fetchone()

                if inserted_row:
                    st.session_state.current_trip_record_id = inserted_row[0]

        st.session_state.last_saved_trip_text = text
        load_user_trips.clear()

    except Exception as error:
        print(
            "Trip save error:",
            type(error).__name__,
            error,
        )

        st.warning(
            "The selected trip could not be saved. "
            "Please try again."
        )

@st.cache_data(ttl=300, show_spinner=False)
def load_user_trips(user_id, limit=10):
    if not user_id:
        return []

    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        selected_mode,
                        route,
                        trip_type,
                        travel_dates,
                        estimated_total,
                        carbon_estimate
                    FROM user_trips
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )

                return cursor.fetchall()

    except Exception:
        return []


def delete_user_trip(trip_id):
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    user_id = current_user.get("id")

    if not user_id:
        return False

    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM user_trips
                    WHERE id = %s
                      AND user_id = %s;
                    """,
                    (
                        trip_id,
                        user_id,
                    ),
                )

        if st.session_state.get("current_trip_record_id") == trip_id:
            st.session_state.current_trip_record_id = None
            st.session_state.last_saved_trip_text = None

        load_user_trips.clear()
        return True

    except Exception as error:
        print(
            "Trip deletion error:",
            type(error).__name__,
            error,
        )

        st.warning(
            "The trip could not be deleted. "
            "Please try again."
        )

        return False


def update_neon_user_profile(display_name, email):
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    user_id = current_user.get("id")

    if not user_id:
        return False, "No logged-in user found.", None

    clean_name = display_name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return False, "Display name cannot be empty.", None

    if "@" not in clean_email:
        return False, "Please enter a valid email address.", None

    try:
        with get_neon_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE app_users
                    SET
                        display_name = %s,
                        email = %s
                    WHERE id = %s
                    RETURNING id, email, display_name;
                    """,
                    (
                        clean_name,
                        clean_email,
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        if not row:
            return False, "User account could not be updated.", None

        updated_user = {
            "id": row[0],
            "email": row[1],
            "display_name": row[2],
        }

        return True, "Account settings updated.", updated_user

    except psycopg2.errors.UniqueViolation:
        return False, "This email is already used by another account.", None

    except Exception as error:
        print(
            "Account update error:",
            type(error).__name__,
            error,
        )

        return (
            False,
            "Account settings could not be updated. "
            "Please try again.",
            None,
        )

def clear_login_session():
    st.session_state.authenticated_user = None
    st.session_state.messages = []
    st.session_state.handover_active = False
    st.session_state.conversation_finished = False
    st.session_state.current_trip_record_id = None
    st.session_state.last_saved_trip_text = None
    st.session_state.sender_id = (
        f"streamlit_user_{uuid.uuid4().hex}"
    )

def render_user_panel():
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    display_name = current_user.get("display_name", "User")
    email = current_user.get("email", "Not available")
    initials = user_initials(display_name, email)

    st.html(f"""
    <div class="sidebar-user-card">
        <div class="sidebar-user-row">
            <div
                class="sidebar-user-avatar"
                aria-hidden="true"
            >
                {html.escape(initials)}
            </div>

            <div class="sidebar-user-copy">
                <div class="sidebar-user-name">
                    {html.escape(display_name)}
                </div>

                <div class="sidebar-user-email">
                    {html.escape(email)}
                </div>
            </div>
        </div>
    </div>
    """)

    if st.button(
        "Log out",
        key="sidebar_logout_small",
        use_container_width=True,
    ):
        clear_login_session()
        delete_auth_cookie()
        st.stop()

    st.html('<div class="sidebar-gap"></div>')

    if st.button(
        "＋  Plan a new trip",
        key="sidebar_new_trip",
        type="primary",
        use_container_width=True,
        help="Clear the current conversation and start a fresh plan.",
    ):
        reset_chat()
        st.rerun()

    st.html('<div class="sidebar-section-label">Your account</div>')

    with st.expander(
        "My trips",
        expanded=False,
    ):
        trips = load_user_trips(current_user.get("id"))

        if not trips:
            st.caption(
                "No selected trips saved yet. Confirm a selected plan to save one."
            )

        for trip in trips:
            (
                trip_id,
                selected_mode,
                route,
                trip_type,
                travel_dates,
                estimated_total,
                carbon_estimate,
            ) = trip

            st.html(f"""
            <div class="saved-trip-card">
                <div class="saved-trip-title">
                    {html.escape(selected_mode or "Selected")} plan
                </div>

                <div class="saved-trip-details">
                    <strong>
                        {html.escape(route or "Route not available")}
                    </strong><br>
                    {html.escape(travel_dates or "Dates not available")}<br>
                    {html.escape(trip_type or "Trip type not available")}<br>
                    Total: {html.escape(estimated_total or "Not available")}<br>
                    CO2e: {html.escape(carbon_estimate or "Not available")}
                </div>
            </div>
            """)

            if st.button(
                "Delete trip",
                key=f"delete_trip_{trip_id}",
                use_container_width=True,
            ):
                if delete_user_trip(trip_id):
                    st.rerun()

    with st.expander(
        "Account settings",
        expanded=False,
    ):
        new_display_name = st.text_input(
            "Display name",
            value=display_name,
            key="account_settings_display_name",
        )

        new_email = st.text_input(
            "Email",
            value=email,
            key="account_settings_email",
        )

        if st.button(
            "Save account",
            key="save_account_settings",
            use_container_width=True,
        ):
            success, message, updated_user = update_neon_user_profile(
                new_display_name,
                new_email,
            )

            if not success:
                st.error(message)
            else:
                st.session_state.authenticated_user = updated_user
                st.success(message)
                st.rerun()

def render_brand_header(subtitle):
    st.html(f"""
<header class="brand-header">
    <div class="brand-mark" aria-hidden="true">
        <span class="brand-mark-emoji">🌿</span>
    </div>

    <div>
        <div class="brand-eyebrow">
            Sustainable travel planner
        </div>

        <h1 class="brand-title">
            Eco-Travel Advisor
        </h1>

        <p class="brand-subtitle">
            {html.escape(subtitle)}
        </p>
    </div>
</header>
""")



def render_login_screen():
    render_brand_header(
        "Sign in to start a personalised, "
        "lower-impact travel planning session."
    )

    if not ensure_users_table():
        st.stop()

    login_tab, register_tab = st.tabs([
        "Log in",
        "Create account",
    ])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input(
                "Email",
                placeholder="student@example.com",
            )

            password = st.text_input(
                "Password",
                type="password",
            )

            keep_logged_in = st.checkbox(
                "Keep me logged in on this device",
                key="keep_logged_in",
            )

            privacy_ok = st.checkbox(
                "I understand that this prototype only asks "
                "for trip-planning information and I should "
                "not enter sensitive personal data."
            )

            submitted = st.form_submit_button(
                "Log in",
                use_container_width=True,
            )

        if submitted:
            if not privacy_ok:
                st.warning(
                    "Please confirm the privacy reminder before continuing."
                )
                return

            user = authenticate_neon_user(
                email.strip(),
                password,
            )

            if not user:
                st.error("Incorrect email or password.")
                return

            st.session_state.authenticated_user = user
            reset_chat()

            if keep_logged_in:
                token = create_auth_token(user["id"])

                if not token:
                    st.warning(
                        "Persistent login is temporarily unavailable."
                    )
                    st.rerun()

                set_auth_cookie(token)
                st.stop()

            st.rerun()

    with register_tab:
        with st.form("register_form"):
            display_name = st.text_input(
                "Display name",
                placeholder="Student User",
            )

            email = st.text_input(
                "Email address",
                placeholder="student@example.com",
            )

            password = st.text_input(
                "Create password",
                type="password",
            )

            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )

            privacy_ok = st.checkbox(
                "I understand that only necessary trip data "
                "should be used in this prototype.",
                key="register_privacy_ok",
            )

            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if submitted:
            clean_email = email.strip().lower()
            clean_name = display_name.strip()

            if not clean_name:
                st.error("Please enter a display name.")
                return

            if "@" not in clean_email:
                st.error("Please enter a valid email address.")
                return

            if len(password) < 6:
                st.error("Password should be at least 6 characters.")
                return

            if password != confirm_password:
                st.error("Passwords do not match.")
                return

            if not privacy_ok:
                st.warning(
                    "Please confirm the privacy reminder before continuing."
                )
                return

            created, message = create_neon_user(
                clean_email,
                clean_name,
                password,
            )

            if not created:
                st.error(message)
                return

            user = authenticate_neon_user(
                clean_email,
                password,
            )

            st.session_state.authenticated_user = user
            reset_chat()
            st.rerun()

def reset_chat():
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    user_key = str(
        current_user.get("id", "guest")
    )

    st.session_state.sender_id = (
        f"streamlit_user_{user_key}_{uuid.uuid4().hex}"
    )

    st.session_state.handover_active = False
    st.session_state.conversation_finished = False

    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I can help you plan a more "
                "sustainable trip. Tell me your route and "
                "I will compare trains, buses, driving and "
                "flying by cost, travel time and carbon "
                "footprint, then suggest eco-friendly "
                "hotels and activities."
            ),
            "buttons": [
                {
                    "title": "Plan a trip",
                    "payload": "/plan_trip",
                }
            ],
        }
    ]


if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if not st.session_state.authenticated_user:
    restore_user_from_auth_cookie()

if not st.session_state.authenticated_user:
    render_login_screen()
    st.stop()

if "sender_id" not in st.session_state:
    st.session_state.sender_id = (
        f"streamlit_user_{uuid.uuid4().hex}"
    )

if "messages" not in st.session_state:
    reset_chat()

if "handover_active" not in st.session_state:
    st.session_state.handover_active = False

if "conversation_finished" not in st.session_state:
    st.session_state.conversation_finished = False

if "current_trip_record_id" not in st.session_state:
    st.session_state.current_trip_record_id = None

if "last_saved_trip_text" not in st.session_state:
    st.session_state.last_saved_trip_text = None


def send_to_rasa(message):
    payload = {
        "sender": st.session_state.sender_id,
        "message": message,
    }

    try:
        response = requests.post(
            RASA_API_URL,
            json=payload,
            timeout=8,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as error:
        print(
            "Rasa connection error:",
            type(error).__name__,
            error,
        )

        return [{
            "text": (
                "The travel assistant is temporarily unavailable. "
                "Please try again."
            )
        }]


def add_rasa_responses(responses):
    text_buffer = []

    for item in responses:
        text = item.get("text")
        buttons = item.get("buttons", [])
        custom = item.get("custom") or {}

        if text and str(text).startswith("Selected trip plan:"):
            save_selected_trip_to_neon(str(text))

        if custom.get("type") == "human_handover":
            st.session_state.handover_active = True

            text_buffer = []

            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    text
                    or "Simulated advisor handover has been prepared."
                ),
                "buttons": [],
                "custom": custom,
            })
            continue

        if (
            text
            and "simulated advisor handover is now prepared"
            in text.lower()
        ):
            st.session_state.handover_active = True

        if (
            text
            and text.lower().startswith("goodbye")
        ):
            st.session_state.conversation_finished = True

        if buttons:
            if text:
                text_buffer.append(text)

            combined_text = "\n".join(
                text_buffer
            ).strip()

            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    combined_text
                    or "Please choose an option:"
                ),
                "buttons": buttons,
            })

            text_buffer = []

        elif text:
            text_buffer.append(text)

    if text_buffer:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "\n".join(text_buffer),
            "buttons": [],
        })

    if not responses:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "No response",
            "buttons": [],
        })


def submit_user_message(
    text,
    display_text=None,
):
    if not text.strip():
        return

    shown_text = (
        display_text
        if display_text
        else text
    )

    st.session_state.messages.append({
        "role": "user",
        "content": shown_text,
        "buttons": [],
    })

    with st.spinner("Thinking..."):
      responses = send_to_rasa(text)

    add_rasa_responses(responses)

def submit_chat_input():
    text = st.session_state.get("main_chat_input", "")

    if text:
        submit_user_message(text)

# Calendar date selection
def latest_requested_date_type():
    for message in reversed(st.session_state.messages):
        if message.get("role") != "assistant":
            continue

        text = str(message.get("content", "")).lower()

        if "when would you like to depart" in text:
            return "departure"

        if "when would you like to return" in text:
            return "return"

        return None

    return None

def tracker_departure_date():
    url = (
        f"{RASA_BASE_URL}/conversations/"
        f"{st.session_state.sender_id}/tracker"
    )

    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()

        value = (
            response.json()
            .get("slots", {})
            .get("departure_date")
        )

        return date.fromisoformat(str(value))

    except (
        requests.exceptions.RequestException,
        TypeError,
        ValueError,
    ):
        return None


def fetch_trip_slots():
    """Read the current trip slots from the Rasa tracker.

    Returns a dict of the planning slots, or an empty dict when the
    tracker cannot be reached so the summary rail degrades gracefully.
    """
    url = (
        f"{RASA_BASE_URL}/conversations/"
        f"{st.session_state.sender_id}/tracker"
    )

    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        slots = response.json().get("slots", {}) or {}

    except (requests.exceptions.RequestException, ValueError):
        return {}

    keys = (
        "origin",
        "destination",
        "trip_type",
        "departure_date",
        "return_date",
        "budget",
        "sustainability_level",
        "selected_transport_mode",
        "selected_hotel_name",
    )

    return {key: slots.get(key) for key in keys}


def format_summary_date(value):
    try:
        return date.fromisoformat(str(value)).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return None


def pretty_date_range(value):
    """Format both ends of a "<date> to <date>" range."""
    text = str(value or "").strip()
    match = re.match(r"^(.+?)\s+to\s+(.+)$", text, flags=re.IGNORECASE)

    if not match:
        return pretty_date(text)

    return (
        f"{pretty_date(match.group(1))} "
        f"\u2192 {pretty_date(match.group(2))}"
    )


def clean_port_name(value):
    """"Barcelona Ferry Port" reads better as just "Barcelona"."""
    return re.sub(
        r"\s*(ferry\s*)?port$",
        "",
        str(value or "").strip(),
        flags=re.IGNORECASE,
    ).strip()


def build_journey_chain(origin, destination, mode, ferry_route=""):
    """Berlin -> train -> Barcelona -> ferry -> Mallorca.

    Falls back to a single leg when the route needs no crossing.
    """
    base_mode, _, via_port = str(mode or "").partition(" via ")
    base_mode = base_mode.strip()
    via_port = clean_port_name(via_port)

    # The car route names its ports in a separate field instead.
    if not via_port and ferry_route:
        match = re.match(
            r"\s*(.+?)\s+to\s+(.+)",
            str(ferry_route),
        )
        if match:
            via_port = clean_port_name(match.group(1))

    stops = [(city_flag(origin), origin)]
    legs = [transport_icon(base_mode)]

    if via_port:
        stops.append(("&#9875;", via_port))
        legs.append("&#9972;")

    stops.append((city_flag(destination), destination))

    parts = []

    for index, (flag, city) in enumerate(stops):
        if index:
            parts.append(
                "<span class='journey-leg' aria-hidden='true'>"
                f"<span class='journey-leg-icon'>{legs[index - 1]}</span>"
                "</span>"
            )

        parts.append(
            "<span class='journey-stop'>"
            f"<span class='journey-flag' aria-hidden='true'>{flag}</span>"
            f"<span class='journey-city'>{html.escape(str(city))}</span>"
            "</span>"
        )

    return (
        "<div class='journey-chain' role='img' aria-label='"
        f"{html.escape(str(origin))} to {html.escape(str(destination))}"
        f"{' via ' + html.escape(via_port) if via_port else ''}'>"
        + "".join(parts)
        + "</div>"
    )


def pretty_date(value):
    """Render an ISO date as "01 Aug 2026", leaving anything else alone."""
    text = str(value or "").strip()

    try:
        return date.fromisoformat(text).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return text


def humanize_slot(value):
    """Turn a raw slot value like 'rural_eco_tour' into 'Rural Eco Tour'."""
    text = str(value or "").strip().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.title()

def render_date_picker():
    requested = latest_requested_date_type()

    if not requested or st.session_state.handover_active:
        return

    today = date.today()
    maximum = today + timedelta(days=730)

    if requested == "departure":
        label = "Select departure date"
        button_label = "Use departure date"
        minimum = today

    else:
        label = "Select return date"
        button_label = "Use return date"
        minimum = max(
            today,
            tracker_departure_date() or today,
        )

    default = min(
        minimum + timedelta(days=1),
        maximum,
    )

    form_key = (
        f"date_picker_{st.session_state.sender_id}_"
        f"{requested}_{len(st.session_state.messages)}"
    )

    with st.form(form_key):
        selected = st.date_input(
            label,
            value=default,
            min_value=minimum,
            max_value=maximum,
            format="DD/MM/YYYY",
            help="Choose your travel date from the calendar.",
        )

        submitted = st.form_submit_button(
            button_label,
            use_container_width=True,
        )

    if submitted:
        submit_user_message(
            selected.isoformat(),
            display_text=selected.strftime("%d %B %Y"),
        )
        st.rerun()

latest_message = (
    st.session_state.messages[-1]
    if st.session_state.messages
    else {}
)

latest_text = str(
    latest_message.get("content", "")
).lower()

latest_buttons = latest_message.get(
    "buttons",
    [],
)

cancel_already_visible = any(
    button.get("payload") == "/cancel_change"
    for button in latest_buttons
)

change_prompt_active = (
    latest_message.get("role") == "assistant"
    and any(
        phrase in latest_text
        for phrase in (
            "please enter the new",
            "please choose a new transport option",
            "please choose a new eco hotel",
            "please choose a new hotel",
        )
    )
)

if (
    change_prompt_active
    and not cancel_already_visible
    and not st.session_state.handover_active
    and not st.session_state.conversation_finished
):
    if st.button(
        "Cancel change",
        key="cancel_active_change",
        use_container_width=True,
    ):
        submit_user_message(
            "/cancel_change",
            display_text="Cancel change",
        )
        st.rerun()

def parse_transport_line(line):
    pattern = (
        r"^\d+\.\s*(.*?)\s*\|\s*"
        r"Price:\s*€?([0-9.]+)\s*\|\s*"
        r"Carbon:\s*([0-9.]+)\s*kg CO2e\s*\|\s*"
        r"Label:\s*(green|amber|red)\s*\|\s*"
        r"Score:\s*([0-9.]+)\s*\|\s*"
        r"Source:\s*(.*)$"
    )

    match = re.match(
        pattern,
        line.strip(),
        re.IGNORECASE,
    )

    if not match:
        return None

    return {
        "mode": match.group(1).strip(),
        "price": match.group(2).strip(),
        "carbon": match.group(3).strip(),
        "label": match.group(4).lower().strip(),
        "score": match.group(5).strip(),
        "source": match.group(6).strip(),
    }


def render_activities(activities):
    activity_html = "".join(
        (
            "<span class='activity-pill'>"
            f"{html.escape(activity.lstrip('- ').strip())}"
            "</span>"
        )
        for activity in activities
    )

    st.html(f"""
<div class="activity-list">
    {activity_html}
</div>
""")

# Compact results interface styles
st.html("""
<style>
.result-summary,.metric-help,.result-card,.environment-note{
    max-width:1050px;margin:12px 0 18px 48px;border-radius:8px;
    background:#ffffff;color:var(--text)
}
.result-summary{border:1px solid var(--border);overflow:hidden}
.result-head{padding:16px 18px;border-bottom:1px solid var(--border)}
.result-route{font-size:1.25rem;font-weight:900}
.result-kicker{color:var(--amber);font-size:.78rem;font-weight:900;text-transform:uppercase}
.fact-grid,.card-metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))}
.fact,.card-metric{padding:12px 15px;border-right:1px solid var(--border)}
.fact:last-child,.card-metric:last-child{border-right:0}
.fact-label{color:#64748b;font-size:.76rem}
.fact-value{font-weight:800;margin-top:3px}
.budget-alert{
    margin:14px 18px;padding:12px 14px;background:#fef2f2;
    border-left:5px solid #ef4444;border-radius:6px;
    color:#7f1d1d;line-height:1.5
}
.budget-alert strong{color:#b91c1c}
.summary-details,.card-details{margin:12px 18px;color:#475569}
.summary-details summary,.card-details summary,
.metric-help summary,.environment-note summary{
    cursor:pointer;font-weight:800
}
.metric-help,.environment-note{
    padding:12px 14px;border:1px solid var(--border);color:var(--muted)
}
.metric-help div,.environment-note div{margin-top:8px;line-height:1.5}
.result-card{
    position:relative;
    overflow:hidden;
    padding:18px 20px 16px 20px;
    border:1px solid var(--border);
    border-radius:var(--radius-small);
    box-shadow:0 10px 28px rgba(31, 63, 45, 0.081);
}

.result-card::before{
    content:"";
    position:absolute;
    inset:0 auto 0 0;
    width:7px;
}

.result-card.green{
    background:
        linear-gradient(135deg,rgba(34,197,94,.16),#ffffff 42%,#ffffff);
    border-color:rgba(34,197,94,.65);
}

.result-card.green::before{background:#22c55e}

.result-card.amber{
    background:
        linear-gradient(135deg,rgba(245,158,11,.16),#ffffff 42%,#ffffff);
    border-color:rgba(245,158,11,.72);
}

.result-card.amber::before{background:#f59e0b}

.result-card.red{
    background:
        linear-gradient(135deg,rgba(239,68,68,.14),#ffffff 42%,#ffffff);
    border-color:rgba(239,68,68,.72);
}

.result-card.red::before{background:#ef4444}

.card-head{
    display:flex;justify-content:space-between;gap:10px;
    align-items:center;flex-wrap:wrap
}

.card-title{
    font-weight:900;
    font-size:1.12rem;
    display:flex;
    gap:10px;
    align-items:center;
}

.mode-icon{
    font-size:1.25rem;
    line-height:1;
}
.badges{display:flex;gap:6px;flex-wrap:wrap}
.badge {
    min-height: 34px;
    padding: 8px 14px !important;
    border-radius: 999px;
    font-size: 0.92rem !important;
    font-weight: 900;
    line-height: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
}
.badges {
    gap: 10px !important;
    align-items: center;
}

.card-title {
    font-size: 1.35rem !important;
}

.mode-icon {
    font-size: 1.6rem !important;
}
.green-badge,.ok-badge{background:#dcfce7;color:#166534}
.amber-badge{
    background:#fef3c7;
    color:#92400e
}

.recommended-badge{
    background:#d4af37;
    color:#17130a;
    border:1px solid #f4d675;
    box-shadow:0 0 0 1px rgba(212,175,55,.18)
}
.ferry-badge{
    background:#e0f2fe;
    color:#0369a1;
    border:1px solid rgba(3,105,161,.35)
}
.red-badge,.over-badge{background:rgba(239,125,125,0.16);color:var(--danger)}
.card-metrics{
    grid-template-columns:repeat(3,minmax(0,1fr));
    margin-top:13px;border-block:1px solid var(--border)
}
.card-metrics.car-card-metrics{
    grid-template-columns:repeat(4,minmax(0,1fr));
}
.hotel-carousel{
    display:flex;gap:12px;max-width:1050px;
    margin:12px 0 20px 48px;overflow-x:auto;
    padding-bottom:10px;scroll-snap-type:x mandatory
}
.hotel-slide{
    flex:0 0 min(350px,84vw);scroll-snap-align:start;
    padding:15px;border:1px solid #86efac;border-radius:8px;
    background:#f0fdf4;color:#14532d;line-height:1.5
}
.hotel-slide strong{display:block;margin-bottom:8px}
.hotel-line{margin-top:5px}
@media(max-width:760px){
    .result-summary,.metric-help,.result-card,
    .hotel-carousel,.environment-note{margin-left:0}
    .fact-grid{grid-template-columns:1fr 1fr}
    .card-metrics{grid-template-columns:1fr}
    .card-metrics.car-card-metrics{grid-template-columns:1fr}
}
</style>
""")

st.html("""
<style>
.result-summary,
.metric-help,
.environment-note {
    width: 100% !important;
    max-width: 1050px !important;
    margin: 12px 0 18px 0 !important;
}

.result-card {
    position: relative;
    overflow: hidden;
    width: 100% !important;
    max-width: 1050px !important;
    padding: 0 !important;
    margin: 12px 0 8px 0 !important;
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.32) !important;
    border-left: 0 !important;
    box-shadow: 0 16px 36px rgba(31, 63, 45, 0.099);
}

.result-card::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 8px;
}

.result-card.green {
    background:
        linear-gradient(135deg, rgba(34, 197, 94, 0.14), #ffffff 32%, #ffffff 100%) !important;
    border-color: rgba(34, 197, 94, 0.48) !important;
}

.result-card.green::before {
    background: #22c55e;
}

.result-card.amber {
    background:
        linear-gradient(135deg, rgba(245, 158, 11, 0.14), #ffffff 32%, #ffffff 100%) !important;
    border-color: rgba(245, 158, 11, 0.55) !important;
}

.result-card.amber::before {
    background: #f59e0b;
}

.result-card.red {
    background:
        linear-gradient(135deg, rgba(239, 68, 68, 0.12), #ffffff 32%, #ffffff 100%) !important;
    border-color: rgba(239, 68, 68, 0.55) !important;
}

.result-card.red::before {
    background: #ef4444;
}

.card-inner {
    padding: 18px 20px 16px 28px;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.18rem !important;
    font-weight: 900;
    color: var(--text);
}

.mode-icon {
    font-size: 1.35rem;
    line-height: 1;
}

.card-metrics {
    margin-top: 16px !important;
    border: 1px solid rgba(148, 163, 184, 0.24) !important;
    border-radius: 10px;
    overflow: hidden;
    background: rgba(21, 71, 43, 0.03);
}

.card-metric {
    min-height: 96px;
    padding: 18px 16px !important;
    border-right: 1px solid rgba(148, 163, 184, 0.26) !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    text-align: center;
}

.fact-label {
    color: #3f4f46 !important;
    opacity: 1 !important;
    font-weight: 900;
    font-size: 0.96rem !important;
    line-height: 1.15;
}

.fact-value {
    color: #111c15 !important;
    font-weight: 900 !important;
    font-size: 1.45rem !important;
    line-height: 1.1;
    margin-top: 0 !important;
}

.card-details {
    margin: 14px 0 0 0 !important;
    padding-top: 12px;
    border-top: 1px solid rgba(148, 163, 184, 0.22);
}

.hotel-option-card {
    width: 100% !important;
    max-width: 1050px !important;
    margin: 12px 0 8px 0 !important;
    border-radius: 12px;
    border: 1px solid rgba(34, 197, 94, 0.5);
    background:
        linear-gradient(135deg, rgba(34, 197, 94, 0.12), #f0fdf4 38%, #ffffff 100%);
    color: #14532d;
    box-shadow: 0 14px 30px rgba(31, 63, 45, 0.081);
    padding: 18px 20px;
    line-height: 1.55;
}

.hotel-option-title {
    font-size: 1.12rem;
    font-weight: 900;
    color: #14532d;
    margin-bottom: 12px;
}

.stButton > button,
.stFormSubmitButton > button {
    min-height: 46px;
    border-radius: 12px !important;
    padding: 0.65rem 1rem !important;
    font-weight: 750 !important;
    letter-spacing: -0.01em;
    border: 1px solid var(--border-strong) !important;
    background: var(--surface-raised) !important;
    color: var(--text) !important;
    box-shadow: none !important;
    transition:
        transform 160ms ease,
        border-color 160ms ease,
        background 160ms ease,
        box-shadow 160ms ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(22, 163, 74, 0.55) !important;
    background: var(--surface-soft) !important;
    box-shadow:
        0 10px 24px rgba(31, 63, 45, 0.081) !important;
}

[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
    background:
        linear-gradient(
            135deg,
            #79e3ad,
            var(--brand-strong)
        ) !important;
    color: #0c3b22 !important;
    border-color: transparent !important;
    box-shadow:
        0 10px 26px rgba(22, 163, 74, 0.22) !important;
}

[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
    background:
        linear-gradient(
            135deg,
            #8ceabb,
            #4fd493
        ) !important;
}

.stButton > button:disabled {
    opacity: 0.48;
    transform: none;
    box-shadow: none !important;
}

@media(max-width:760px) {
    .hotel-option-card {
        margin-left: 0;
    }
}

.chat-row {
    max-width: 1050px;
}

.chat-row.user-row {
    justify-content: flex-end;
}

.chat-row.user-row .avatar-user {
    order: 2;
}

.selection-chip-row {
    max-width: 1050px;
    display: flex;
    justify-content: flex-end;
    margin: 14px 0;
}

.selection-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 11px 14px;
    border-radius: 999px;
    background: #ffffff;
    color: var(--text);
    border: 1px solid rgba(34, 197, 94, 0.40);
    font-weight: 850;
    box-shadow: 0 10px 22px rgba(31, 63, 45, 0.054);
}

.selection-chip::before {
    content: "✓";
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 999px;
    background: #22c55e;
    color: #052e16;
    font-size: 0.85rem;
    font-weight: 900;
}

.step-box {
    max-width: 1050px;
    margin: 16px 0 22px 0;
    padding: 16px 18px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.10), #ffffff 38%, #ffffff 100%);
    color: var(--text);
    border: 1px solid rgba(34, 197, 94, 0.42);
    box-shadow: 0 14px 28px rgba(31, 63, 45, 0.072);
}

.step-kicker {
    color: #15803d;
    font-size: 0.78rem;
    font-weight: 900;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.step-title {
    font-size: 1.08rem;
    font-weight: 900;
    margin-bottom: 4px;
}

.step-copy {
    color: #475569;
    line-height: 1.5;
}

/* Transport card and button as one surface */
div[class*="st-key-transport_card_"] {
    width: 100% !important;
    max-width: 1050px !important;
    margin: 12px 0 22px !important;
    border-radius: 14px;
    transition:
        transform 180ms ease,
        box-shadow 180ms ease,
        filter 180ms ease;
}

div[class*="st-key-transport_card_"]
[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

div[class*="st-key-transport_card_"] .result-card {
    margin: 0 !important;
    border-radius: 14px 14px 0 0 !important;
    border-bottom: 0 !important;
    box-shadow: none !important;
}

div[class*="st-key-transport_card_"] .stButton {
    margin: 0 !important;
}

div[class*="st-key-transport_card_"] .stButton > button {
    width: 100% !important;
    min-height: 52px;
    margin: 0 !important;
    border-radius: 0 0 14px 14px !important;
    border-top: 1px solid rgba(148, 163, 184, 0.18) !important;
    box-shadow: none !important;
}

div[class*="st-key-transport_card_"]:hover,
div[class*="st-key-transport_card_"]:focus-within {
    transform: translateY(-4px);
    filter: brightness(1.04);
    box-shadow:
        0 22px 48px rgba(31, 63, 45, 0.135),
        0 0 0 1px rgba(22, 163, 74, 0.20);
}

.result-summary,
.metric-help,
.environment-note,
.result-card,
.hotel-option-card,
.step-box,
.summary-box,
.hotel-carousel {
    width: 100% !important;
    max-width: 1050px !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    box-sizing: border-box !important;
}

.chat-row,
.selection-chip-row {
    width: 100% !important;
    max-width: 1050px !important;
    box-sizing: border-box !important;
}

.chat-row.user-row,
.selection-chip-row {
    justify-content: flex-end !important;
}

.avatar-user {
    background:
        linear-gradient(
            145deg,
            var(--surface-soft),
            var(--surface-raised)
        ) !important;
    color: var(--brand) !important;
    border:
        1px solid rgba(22, 163, 74, 0.38) !important;
    box-shadow:
        0 8px 22px rgba(31, 63, 45, 0.099) !important;
}

/* Narrow and centred chat input */
[data-testid="stBottomBlockContainer"] {
    width: calc(100% - 32px) !important;
    max-width: 980px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

[data-testid="stChatInput"] {
    width: 100% !important;
    max-width: 100% !important;
}

/* Centred and clearer quick choices */
div[class*="st-key-quick_reply_"] {
    width: 100% !important;
    max-width: 960px !important;
    margin: 18px auto 26px !important;
}

div[class*="st-key-quick_reply_options_"]::before {
    content: "Choose an option";
    display: block;
    margin: 0 0 10px 2px;
    color: var(--muted);
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: 0.03em;
}

div[class*="st-key-quick_reply_options_"]
.stButton > button[kind="secondary"] {
    min-height: 56px;
    border: 1px solid rgba(22, 163, 74, 0.38) !important;
    background:
        linear-gradient(
            145deg,
            rgba(22, 163, 74, 0.10),
            var(--surface-raised)
        ) !important;
}

div[class*="st-key-quick_reply_options_"]
.stButton > button[kind="secondary"]:hover {
    transform: translateY(-3px);
    border-color: var(--brand) !important;
    background: rgba(22, 163, 74, 0.16) !important;
    box-shadow:
        0 14px 28px rgba(31, 63, 45, 0.108) !important;
}

/* Hotel card and selection button as one surface */
div[class*="st-key-hotel_card_"] {
    width: 100% !important;
    max-width: 1120px !important;
    margin: 14px auto 24px !important;
    border-radius: 14px;
    transition:
        transform 180ms ease,
        box-shadow 180ms ease,
        filter 180ms ease;
}

div[class*="st-key-hotel_card_"]
[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

div[class*="st-key-hotel_card_"] article {
    margin: 0 !important;
    border-radius: 14px 14px 0 0 !important;
    border-bottom: 0 !important;
    box-shadow: none !important;
}

div[class*="st-key-hotel_card_"] .stButton {
    margin: 0 !important;
}

div[class*="st-key-hotel_card_"] .stButton > button {
    width: 100% !important;
    min-height: 52px;
    margin: 0 !important;
    border-radius: 0 0 14px 14px !important;
    border-top:
        1px solid rgba(148, 163, 184, 0.18) !important;
    box-shadow: none !important;
}

div[class*="st-key-hotel_card_"]:hover,
div[class*="st-key-hotel_card_"]:focus-within {
    transform: translateY(-4px);
    filter: brightness(1.04);
    box-shadow:
        0 22px 48px rgba(31, 63, 45, 0.135),
        0 0 0 1px rgba(22, 163, 74, 0.20);
}

/* One centred content axis on wide screens */
[data-testid="stMainBlockContainer"],
.block-container {
    max-width: 1240px !important;
}

.result-summary,
.metric-help,
.environment-note,
.result-card,
.hotel-option-card,
.step-box,
.summary-box,
.hotel-carousel,
.chat-row,
.selection-chip-row,
.section-title,
div[class*="st-key-transport_card_"],
div[class*="st-key-hotel_card_"] {
    width: 100% !important;
    max-width: 1120px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    box-sizing: border-box !important;
}

.confirmed-plan-card {
    padding: 0 !important;
    overflow: hidden;
    border-color: rgba(22, 163, 74, 0.46) !important;
    background:
        linear-gradient(
            145deg,
            rgba(22, 163, 74, 0.10),
            var(--surface-raised) 42%,
            var(--surface) 100%
        ) !important;
    box-shadow:
        0 20px 44px rgba(31, 63, 45, 0.108) !important;
}

.confirmed-plan-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 16px 20px;
    background:
        linear-gradient(
            90deg,
            rgba(22, 163, 74, 0.20),
            rgba(22, 163, 74, 0.05)
        );
    border-bottom: 1px solid rgba(22, 163, 74, 0.22);
}

.confirmed-plan-kicker {
    color: var(--brand);
    font-size: 0.70rem;
    font-weight: 900;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}

.confirmed-plan-title {
    margin-top: 2px;
    color: var(--text);
    font-size: 1.05rem;
    font-weight: 900;
}

.confirmed-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
    padding: 7px 11px;
    border-radius: 999px;
    color: #0c3b22;
    background: var(--brand-strong);
    font-size: 0.78rem;
    font-weight: 900;
}

.confirmed-status-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.35);
}

.confirmed-plan-body {
    padding: 20px;
}

.confirmed-route-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(150px, 0.8fr) minmax(0, 1fr);
    align-items: center;
    gap: 18px;
    padding: 18px;
    border: 1px solid rgba(22, 163, 74, 0.20);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.75);
}

.confirmed-city {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-areas:
        "flag label"
        "flag city"
        "flag date";
    align-items: center;
    column-gap: 11px;
}

.confirmed-city.destination {
    grid-template-columns: 1fr auto;
    grid-template-areas:
        "label flag"
        "city flag"
        "date flag";
    text-align: right;
}

.confirmed-flag {
    grid-area: flag;
    font-size: 2rem;
    line-height: 1;
    filter: saturate(0.95);
}

.confirmed-city-label {
    grid-area: label;
    color: var(--brand);
    font-size: 0.66rem;
    font-weight: 900;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

.confirmed-city-name {
    grid-area: city;
    color: var(--text);
    font-size: 1.22rem;
    font-weight: 900;
    overflow-wrap: anywhere;
}

.confirmed-city-date {
    grid-area: date;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    justify-self: start;
    margin-top: 7px;
    padding: 5px 8px;
    border: 1px solid rgba(22, 163, 74, 0.18);
    border-radius: 8px;
    background: rgba(22, 163, 74, 0.07);
    color: var(--text);
    font-size: 0.78rem;
    font-weight: 750;
}

.confirmed-city.destination .confirmed-city-date {
    justify-self: end;
}

.confirmed-date-label {
    color: var(--brand);
    font-size: 0.64rem;
    font-weight: 900;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.confirmed-route-track {
    display: flex;
    align-items: center;
    min-width: 0;
    color: var(--brand);
}

.confirmed-route-line {
    height: 1px;
    flex: 1;
    background:
        repeating-linear-gradient(
            90deg,
            rgba(22, 163, 74, 0.65) 0 6px,
            transparent 6px 11px
        );
}

.confirmed-route-dot {
    width: 7px;
    height: 7px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--brand);
    box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.12);
}

.confirmed-mode-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    margin: 0 8px;
    border: 1px solid rgba(22, 163, 74, 0.28);
    border-radius: 50%;
    background: var(--surface-raised);
    font-size: 1rem;
}

.confirmed-trip-meta {
    margin: 10px 0 16px;
    color: var(--muted);
    font-size: 0.86rem;
    text-align: center;
}

.confirmed-details-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}

.confirmed-detail {
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(21, 71, 43, 0.03);
}

.confirmed-detail.carbon {
    border-color: rgba(22, 163, 74, 0.28);
    background: rgba(22, 163, 74, 0.055);
}

.confirmed-detail.hotel {
    border-color: rgba(247, 195, 95, 0.26);
    background: rgba(247, 195, 95, 0.045);
}

.confirmed-detail.wide {
    grid-column: 1 / -1;
}

.confirmed-detail-label {
    margin-bottom: 3px;
    color: var(--muted);
    font-size: 0.68rem;
    font-weight: 850;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.confirmed-detail-value {
    color: var(--text);
    font-weight: 750;
    overflow-wrap: anywhere;
}

.confirmed-experiences {
    max-width: none !important;
    margin-left: 0 !important;
}

@media (max-width: 760px) {
    [data-testid="stBottomBlockContainer"] {
        width: calc(100% - 20px) !important;
    }

    div[class*="st-key-quick_reply_options_"]
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 10px !important;
    }

    div[class*="st-key-quick_reply_options_"]
    [data-testid="stColumn"] {
        flex: 1 1 calc(50% - 5px) !important;
        min-width: calc(50% - 5px) !important;
    }

    .confirmed-plan-banner {
        align-items: flex-start;
    }

    .confirmed-route-card {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .confirmed-city,
    .confirmed-city.destination {
        grid-template-columns: auto 1fr;
        grid-template-areas:
            "flag label"
            "flag city"
            "flag date";
        text-align: left;
    }

    .confirmed-city.destination .confirmed-city-date {
        justify-self: start;
    }

    .confirmed-route-track {
        width: min(220px, 70%);
        margin: 0 auto;
    }

    .confirmed-details-grid {
        grid-template-columns: 1fr;
    }

    .confirmed-detail.wide {
        grid-column: auto;
    }

    .plan-highlights-grid,
    .plan-facts-grid {
        grid-template-columns: 1fr;
    }

    .plan-highlight-card.hotel {
        grid-column: auto;
    }

    .car-metrics-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ferry-route-flow,
    .ferry-facts {
        grid-template-columns: 1fr;
    }

    .ferry-flow-icon {
        min-height: 34px;
        transform: rotate(90deg);
    }

    .car-route-footer {
        align-items: stretch;
        flex-direction: column;
    }

    .car-route-link {
        width: 100%;
    }
}

</style>
""")


def _trip_context(lines):
    result = {
        "route": "Trip recommendations",
        "distance": "N/A",
        "budget": "N/A",
        "stay": "N/A",
        "trip_type": "General trip",
        "priority": "N/A",
    }

    for line in lines:
        route = re.search(
            r"recommendations for (.+?) to (.+?)\.?$",
            line,
            re.I,
        )

        if route:
            result["route"] = (
                f"{route.group(1).strip()} → "
                f"{route.group(2).strip()}"
            )

        context = re.search(
            r"route distance is ([0-9.,]+) km, "
            r"budget reference is €([0-9.,]+), "
            r"stay length is ([0-9]+) nights?, "
            r"trip type is ([^,]+), "
            r"and sustainability priority is ([^.]+)",
            line,
            re.I,
        )

        if context:
            result.update(
                distance=f"{context.group(1)} km",
                budget=f"€{context.group(2)}",
                stay=(
                    f"{context.group(3)} night"
                    if context.group(3) == "1"
                    else f"{context.group(3)} nights"
                ),
                trip_type=context.group(4).strip(),
                priority=context.group(5).strip().title(),
            )

    return result


def _selected_transport_after(message_index):
    later_messages = st.session_state.messages[
        message_index + 1:
    ]

    for message in later_messages:
        text = str(
            message.get("content", "")
        ).strip()

        lower_text = text.lower()

        if lower_text.startswith("selected transport:"):
            first_line = text.splitlines()[0]
            return first_line.split(":", 1)[-1].strip()

    return None


def _selected_hotel_after(message_index):
    later_messages = st.session_state.messages[
        message_index + 1:
    ]

    for message in later_messages:
        text = str(
            message.get("content", "")
        ).strip()

        lower_text = text.lower()

        if lower_text.startswith("selected hotel:"):
            first_line = text.splitlines()[0]
            return first_line.split(":", 1)[-1].strip()

    return None


def _is_current_action_message(message_index):
    return (
        message_index == len(st.session_state.messages) - 1
        and not st.session_state.handover_active
        and not st.session_state.conversation_finished
    )

def _latest_assistant_text():
    if not st.session_state.messages:
        return ""

    latest_message = st.session_state.messages[-1]

    if latest_message.get("role") != "assistant":
        return ""

    return str(latest_message.get("content", "")).lower()


def _transport_reselection_active():
    return "choose a new transport option" in _latest_assistant_text()



st.html("""
<style>
/* ── Transport cards: tighter grouping and entrance motion ───────── */

/* Cards read as one stack rather than four separate blocks. */
div[class*="st-key-transport_card_"] {
    margin: 0 auto 12px !important;
}

.card-inner {
    padding: 14px 18px 12px 24px;
}

.card-metrics {
    margin-top: 12px !important;
    border-radius: 9px;
}

.card-metric {
    min-height: 72px;
    padding: 12px 12px !important;
    gap: 5px;
}

.fact-label {
    font-size: 0.8rem !important;
    font-weight: 800;
}

.fact-value {
    font-size: 1.24rem !important;
}

.card-title {
    font-size: 1.1rem !important;
}

.mode-icon {
    font-size: 1.25rem;
}

.card-details {
    margin-top: 10px !important;
    padding-top: 9px;
}

.badge {
    min-height: 28px;
    padding: 5px 11px !important;
    font-size: 0.8rem !important;
}

.badges {
    gap: 7px !important;
}

/* Entrance: cards rise into place one after another. Fill mode is
   backwards so the hover lift still works once the animation ends. */
@keyframes card-rise {
    from {
        opacity: 0;
        transform: translateY(16px) scale(0.99);
    }
}

/* Relative carbon bar: how this option compares with the worst one. */
.carbon-bar {
    height: 6px;
    margin-top: 12px;
    border-radius: 999px;
    background: rgba(21, 71, 43, 0.09);
    overflow: hidden;
}

.carbon-bar > span {
    display: block;
    height: 100%;
    border-radius: inherit;
    animation: bar-grow 760ms cubic-bezier(.22, .9, .3, 1) backwards;
}

@keyframes bar-grow {
    from {
        width: 0 !important;
    }
}

.result-card.green .carbon-bar > span {
    background: linear-gradient(90deg, #4ade80, #22c55e);
}

.result-card.amber .carbon-bar > span {
    background: linear-gradient(90deg, #fbbf24, #f59e0b);
}

.result-card.red .carbon-bar > span {
    background: linear-gradient(90deg, #f87171, #ef4444);
}

.carbon-bar-caption {
    display: flex;
    justify-content: space-between;
    margin-top: 5px;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 700;
}

/* The recommended option gets a soft ring and a slow shimmer. The
   selector matches the card-wrapper rule that resets box-shadow, so it
   needs the same reach to win. */
div[class*="st-key-transport_card_"] .result-card.is-recommended {
    border-color: rgba(34, 197, 94, 0.55) !important;
    box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.30) !important;
}

.recommended-badge {
    position: relative;
    overflow: hidden;
}

.recommended-badge::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        115deg,
        transparent 32%,
        rgba(255, 255, 255, 0.65) 50%,
        transparent 68%
    );
    transform: translateX(-130%);
    animation: badge-shimmer 3.2s ease-in-out 1s infinite;
}

@keyframes badge-shimmer {
    to {
        transform: translateX(130%);
    }
}

@media (prefers-reduced-motion: reduce) {
    div[class*="st-key-transport_card_"],
    .carbon-bar > span,
    .recommended-badge::after {
        animation: none !important;
    }
}
</style>
""")


def safe_float_ui(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _claim_card_animation(message_index):
    """True the first time this message's cards are drawn this session.

    Streamlit re-runs the whole script on every interaction, so without
    this guard the cards would replay their entrance animation on every
    button click.
    """
    key = f"_animated_transport_{message_index}"

    if st.session_state.get(key):
        return False

    st.session_state[key] = True
    return True


COUNT_UP_SCRIPT = """
<script>
(function () {
    const doc = window.parent.document;

    function countUp(el) {
        const raw = el.textContent.trim();
        const match = raw.match(/^([^\\d]*)([\\d.]+)([\\s\\S]*)$/);

        if (!match) {
            return;
        }

        const prefix = match[1];
        const numberText = match[2];
        const suffix = match[3];
        const target = parseFloat(numberText);

        if (!isFinite(target)) {
            return;
        }

        const decimals = (numberText.split(".")[1] || "").length;
        const duration = 700;
        const started = performance.now();

        function frame(now) {
            const progress = Math.min(1, (now - started) / duration);
            const eased = 1 - Math.pow(1 - progress, 3);

            el.textContent =
                prefix + (target * eased).toFixed(decimals) + suffix;

            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                el.textContent = raw;
            }
        }

        requestAnimationFrame(frame);
    }

    setTimeout(function () {
        doc.querySelectorAll(
            ".result-card .fact-value"
        ).forEach(function (el) {
            if (el.dataset.counted) {
                return;
            }
            el.dataset.counted = "1";
            countUp(el);
        });
    }, 140);
})();
</script>
"""


def _compact_transport_card(
    option,
    message_index,
    option_index,
    recommended=False,
    max_carbon=0,
    animate=False,
):
    label = option["label"]
    mode = option["mode"]

    # Ferry variants arrive as "Train via Barcelona"; the leading word
    # is the real transport mode.
    base_mode, _, via_port = str(mode).partition(" via ")
    base_mode = base_mode.strip()
    via_port = via_port.strip()
    is_car = base_mode.casefold() == "car"

    detail = re.sub(
        r"Estimated transport plus accommodation total:.*$",
        "",
        option["source"],
        flags=re.I,
    ).strip()
    # Train and bus routes to an island also carry a ferry leg, so the
    # ferry naming is not car-only.
    includes_ferry = "ferry required: yes" in detail.casefold()

    mode_display = (
        f"{base_mode} + ferry"
        if includes_ferry
        else base_mode
    )

    # Several ports can serve the same mode, so the buttons name the
    # port as well; otherwise three cards share one label.
    selection_label = (
        f"{base_mode} via {via_port}"
        if via_port
        else mode_display
    )

    if is_car:
        route_match = re.search(
            r"One-way road estimate:\s*"
            r"([\d.,]+\s*km),\s*([^.]+)\.",
            detail,
            re.IGNORECASE,
        )
        road_distance = (
            route_match.group(1).strip()
            if route_match
            else "See details"
        )
        drive_time = (
            route_match.group(2).strip()
            if route_match
            else "See details"
        )

        metrics_html = f"""
<div class="card-metrics car-card-metrics">
    <div class="card-metric">
        <div class="fact-label">Fuel cost</div>
        <div class="fact-value">
            &euro;{html.escape(str(option['price']))}
        </div>
    </div>

    <div class="card-metric">
        <div class="fact-label">Road distance</div>
        <div class="fact-value">{html.escape(road_distance)}</div>
    </div>

    <div class="card-metric">
        <div class="fact-label">Drive time</div>
        <div class="fact-value">{html.escape(drive_time)}</div>
    </div>

    <div class="card-metric"
         title="Estimated carbon dioxide equivalent">
        <div class="fact-label">CO2e</div>
        <div class="fact-value">
            {html.escape(str(option['carbon']))} kg
        </div>
    </div>
</div>
"""
    else:
        metrics_html = f"""
<div class="card-metrics">
    <div class="card-metric">
        <div class="fact-label">Transport price</div>
        <div class="fact-value">
            &euro;{html.escape(str(option['price']))}
        </div>
    </div>

    <div class="card-metric"
         title="Estimated carbon dioxide equivalent">
        <div class="fact-label">CO2e</div>
        <div class="fact-value">
            {html.escape(str(option['carbon']))} kg
        </div>
    </div>

    <div class="card-metric">
        <div class="fact-label">Score</div>
        <div class="fact-value">
            {html.escape(str(option['score']))}
        </div>
    </div>
</div>
"""

    badges = ""

    if recommended:
        badges += (
            "<span class='badge recommended-badge'>"
            "Recommended</span>"
        )

    if via_port:
        badges += (
            "<span class='badge ferry-badge'>"
            f"&#9972; via {html.escape(via_port)}</span>"
        )
    elif includes_ferry:
        badges += (
            "<span class='badge ferry-badge'>"
            "Includes ferry</span>"
        )

    badges += (
        f"<span class='badge {label}-badge'>"
        f"{html.escape(label.title())} emissions</span>"
    )

    selected_mode = _selected_transport_after(message_index)

    can_select = (
        _is_current_action_message(message_index)
        or _transport_reselection_active()
    ) and not selected_mode

    # Relative carbon bar, measured against the worst option shown.
    carbon_bar_html = ""
    carbon_value = safe_float_ui(option.get("carbon"))

    if max_carbon > 0 and carbon_value is not None:
        share = max(3, min(100, round(carbon_value / max_carbon * 100)))
        comparison = (
            "highest of these options"
            if share >= 99
            else f"{share}% of the highest option"
        )

        carbon_bar_html = f"""
        <div class="carbon-bar"
             role="img"
             aria-label="Carbon {comparison}">
            <span style="width: {share}%"></span>
        </div>
        <div class="carbon-bar-caption">
            <span>Carbon vs. worst option</span>
            <span>{share}%</span>
        </div>
        """

    # Per-card entrance delay, so the cards arrive one after another.
    animation_css = ""

    if animate:
        animation_css = f"""
<style>
div.st-key-transport_card_{message_index}_{option_index} {{
    animation: card-rise 460ms cubic-bezier(.22, .9, .3, 1) backwards;
    animation-delay: {option_index * 80}ms;
}}
</style>
"""

    recommended_class = " is-recommended" if recommended else ""

    with st.container(
        key=f"transport_card_{message_index}_{option_index}"
    ):
        st.html(f"""
{animation_css}
<article class="result-card {label}{recommended_class}"
         aria-label="{html.escape(mode_display)} travel option">
    <div class="card-inner">
        <div class="card-head">
            <div class="card-title">
                <span class="mode-icon">{transport_icon(base_mode)}</span>
                <span>{html.escape(mode_display)}</span>
            </div>

            <div class="badges">{badges}</div>
        </div>

        {metrics_html}

        {carbon_bar_html}

        <details class="card-details">
            <summary>Calculation details</summary>
            <div>{html.escape(detail)}</div>
        </details>
    </div>
</article>
""")

        payload_mode = mode.replace("\\", "\\\\").replace('"', '\\"')

        if selected_mode:
            if selected_mode.casefold() == mode.casefold():
                st.button(
                    f"Selected {selection_label}",
                    key=(
                        f"transport_selected_{message_index}_"
                        f"{option_index}_{abs(hash(mode))}"
                    ),
                    use_container_width=True,
                    disabled=True,
                )

        elif can_select:
            if st.button(
                f"Select {selection_label}",
                key=(
                    f"transport_select_{message_index}_"
                    f"{option_index}_{abs(hash(mode))}"
                ),
                use_container_width=True,
                type="primary" if recommended else "secondary",
            ):
                submit_user_message(
                    f'/select_transport_option'
                    f'{{"selected_transport_mode":"{payload_mode}"}}',
                    display_text=f"Selected transport: {mode}",
                )
                st.rerun()


def _hotel_carousel(
    hotels,
    message_index,
):
    selected_hotel_after = _selected_hotel_after(
        message_index
    )

    can_select = _is_current_action_message(
        message_index
    )

    for hotel_index, hotel in enumerate(hotels):
        parts = [
            part.strip()
            for part in hotel.lstrip("- ").split("|")
        ]

        name_and_city = parts[0]

        if " in " in name_and_city:
            hotel_name = name_and_city.rsplit(" in ", 1)[0].strip()
        else:
            hotel_name = name_and_city.strip()

        price = ""
        total = ""
        budget_status = ""
        features = ""
        source = ""

        for part in parts[1:]:
            lower_part = part.lower()

            if "per night" in lower_part:
                price = part
            elif "night total" in lower_part:
                total = part
            elif "budget status" in lower_part:
                budget_status = part.replace("Budget status:", "").strip()
            elif "features:" in lower_part:
                features = part.replace("Features:", "").strip()
            elif "source:" in lower_part:
                source = part.replace("Source:", "").strip()

        hotel_card = st.container(
            key=f"hotel_card_{message_index}_{hotel_index}"
        )

        hotel_card.html(f"""
<article style="
    width:100%;
    border:1px solid rgba(34,197,94,.45);
    border-left:8px solid #22c55e;
    border-radius:14px;
    padding:22px 24px;
    margin:14px 0 10px 0;
    color:#14532d;
    background:
        linear-gradient(135deg, rgba(34,197,94,.14), #f0fdf4 42%, #ffffff 100%);
    box-shadow:0 18px 38px rgba(31, 63, 45, 0.099);
" aria-label="{html.escape(hotel_name)} accommodation option">
    <div style="
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:14px;
        margin-bottom:16px;
    ">
        <div style="
            font-size:1.35rem;
            font-weight:950;
            color:#14532d;
            line-height:1.2;
        ">
            🏨 {html.escape(name_and_city)}
        </div>

        <div style="
            padding:8px 13px;
            border-radius:999px;
            background:#dcfce7;
            color:#166534;
            font-size:.88rem;
            font-weight:950;
            white-space:nowrap;
        ">
            Eco stay
        </div>
    </div>

    <div style="
        display:grid;
        grid-template-columns:repeat(3,minmax(0,1fr));
        gap:0;
        border:1px solid rgba(148,163,184,.24);
        border-radius:10px;
        overflow:hidden;
        margin-bottom:16px;
        background:rgba(21,71,43,.03);
    ">
        <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,.24);">
            <div style="font-size:.9rem;font-weight:900;color:#4b5563;">Nightly price</div>
            <div style="font-size:1.35rem;font-weight:950;color:#111c15;margin-top:6px;">{html.escape(price or "N/A")}</div>
        </div>

        <div style="padding:16px;text-align:center;border-right:1px solid rgba(148,163,184,.24);">
            <div style="font-size:.9rem;font-weight:900;color:#4b5563;">Stay total</div>
            <div style="font-size:1.35rem;font-weight:950;color:#111c15;margin-top:6px;">{html.escape(total or "N/A")}</div>
        </div>

        <div style="padding:16px;text-align:center;">
            <div style="font-size:.9rem;font-weight:900;color:#4b5563;">Budget fit</div>
            <div style="font-size:1rem;font-weight:900;color:#15803d;margin-top:6px;">Within check</div>
        </div>
    </div>

    <div style="font-size:1rem;line-height:1.55;color:#374151;">
        <div><strong>Budget:</strong> {html.escape(budget_status or "Not available")}</div>
        <div><strong>Features:</strong> {html.escape(features or "Not available")}</div>
        <div style="color:#047857;margin-top:4px;"><strong>Source:</strong> {html.escape(source or "Prototype dataset")}</div>
    </div>
</article>
""")

        payload_hotel_name = (
            hotel_name
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

        if (
            selected_hotel_after
            and selected_hotel_after.casefold()
            == hotel_name.casefold()
        ):
            hotel_card.button(
                f"Selected {hotel_name}",
                key=(
                    f"hotel_selected_{message_index}_"
                    f"{hotel_index}_{abs(hash(hotel_name))}"
                ),
                use_container_width=True,
                disabled=True,
            )

        elif can_select:
            if hotel_card.button(
                f"Select {hotel_name}",
                key=(
                    f"hotel_select_{message_index}_"
                    f"{hotel_index}_{abs(hash(hotel_name))}"
                ),
                use_container_width=True,
                type="primary" if hotel_index == 0 else "secondary",
            ):
                submit_user_message(
                    f'/select_hotel_option'
                    f'{{"selected_hotel_name":"{payload_hotel_name}"}}',
                    display_text=f"Selected hotel: {hotel_name}",
                )
                st.rerun()

def render_recommendations(
    text,
    message_index,
):
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    transports = []
    budget_lines = []
    scoring_lines = []

    for line in lines:
        transport = parse_transport_line(line)

        if transport:
            transports.append(transport)
            continue

        lower = line.lower()

        if lower.startswith((
            "budget alert",
            "the lowest current estimate",
            "prices are estimates",
        )):
            budget_lines.append(line)
            continue

        if lower.startswith("scoring method"):
            scoring_lines.append(line)
            continue

    context = _trip_context(lines)

    facts = "".join(
        (
            "<div class='fact'>"
            f"<div class='fact-label'>{label}</div>"
            f"<div class='fact-value'>{html.escape(value)}</div>"
            "</div>"
        )
        for label, value in [
            ("Distance", context["distance"]),
            ("Budget", context["budget"]),
            ("Stay", context["stay"]),
            ("Trip type", context["trip_type"]),
            ("Priority", context["priority"]),
        ]
    )

    alert = ""

    if budget_lines:
        alert = (
            "<div class='budget-alert' role='alert'>"
            "<strong>Budget adjustment needed</strong><br>"
            + html.escape(" ".join(budget_lines))
            + "</div>"
        )

    ranking = ""

    if scoring_lines:
        ranking = (
            "<details class='summary-details'>"
            "<summary>How options are ranked</summary>"
            "<div>"
            + html.escape(" ".join(scoring_lines))
            + "</div></details>"
        )

    st.html(f"""
<section class="result-summary"
         aria-label="Trip recommendation summary">
    <div class="result-head">
        <div class="result-kicker">Trip recommendation</div>
        <div class="result-route">{html.escape(context["route"])}</div>
    </div>

    <div class="fact-grid">{facts}</div>
    {alert}
    {ranking}
</section>
""")

    if transports:
        st.html(
            "<div class='section-title'>Choose Transport First</div>"
        )

        st.html("""
<details class="metric-help">
    <summary>How to read these results</summary>
    <div>
        <strong>CO2e:</strong> estimated greenhouse-gas impact.
        <strong>Colours:</strong> green is lower intensity,
        amber moderate, and red higher.
        <strong>Score:</strong> weighted carbon, cost,
        and preference comparison.
    </div>
</details>
""")

        animate = _claim_card_animation(message_index)
        max_carbon = max(
            (
                safe_float_ui(option.get("carbon")) or 0
                for option in transports
            ),
            default=0,
        )

        for index, option in enumerate(transports):
            _compact_transport_card(
                option,
                message_index,
                index,
                recommended=index == 0,
                max_carbon=max_carbon,
                animate=animate,
            )

        if animate:
            components.html(COUNT_UP_SCRIPT, height=0)

def recommendation_transports_before(message_index):
    for previous_index in range(
        message_index - 1,
        -1,
        -1,
    ):
        message = st.session_state.messages[previous_index]

        if message.get("role") != "assistant":
            continue

        text = str(message.get("content", ""))

        transports = []

        for line in text.splitlines():
            transport = parse_transport_line(line)

            if transport:
                transports.append(transport)

        if transports:
            return transports

    return []

def recommendation_hotels_before(message_index):
    hotel_headers = (
        "eco hotels",
        "eco-certified accommodation options",
        "now choose eco hotel",
    )

    stop_headers = (
        "local experiences",
        "local cultural experiences",
        "environmental note",
        "environmental data and privacy note",
        "transport options",
        "choose transport first",
    )

    for previous_index in range(
        message_index - 1,
        -1,
        -1,
    ):
        message = st.session_state.messages[previous_index]

        if message.get("role") != "assistant":
            continue

        text = str(message.get("content", ""))
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        hotels = []
        section = None

        for line in lines:
            lower = line.lower()

            if lower.startswith(hotel_headers):
                section = "hotels"
                continue

            if lower.startswith(stop_headers):
                if section == "hotels":
                    break
                section = None
                continue

            if section == "hotels":
                if lower == "eco-certified accommodation":
                    continue

                if (
                    "per night" in lower
                    or "features:" in lower
                    or "source:" in lower
                ):
                    if line.startswith("-"):
                        hotels.append(line)
                    else:
                        hotels.append(f"- {line}")

        if hotels:
            return hotels

    return []

def recommendation_activities_before(message_index):
    activity_headers = (
        "local experiences",
        "local cultural experiences",
    )

    stop_headers = (
        "environmental note",
        "environmental data and privacy note",
    )

    for previous_index in range(
        message_index - 1,
        -1,
        -1,
    ):
        message = st.session_state.messages[previous_index]

        if message.get("role") != "assistant":
            continue

        text = str(message.get("content", ""))
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        activities = []
        section = None

        for line in lines:
            lower = line.lower()

            if lower.startswith(activity_headers):
                section = "activities"
                continue

            if lower.startswith(stop_headers):
                break

            if section == "activities":
                if line.startswith("-"):
                    activities.append(line)
                elif not lower.startswith("environmental"):
                    activities.append(f"- {line}")

        if activities:
            return activities

    return []

def render_transport_selection_after_change(message_index):
    transports = recommendation_transports_before(
        message_index
    )

    if not transports:
        st.warning(
            "Transport options could not be reloaded. Please confirm the trip again to regenerate recommendations."
        )
        return

    st.html(
        "<div class='section-title'>Choose New Transport</div>"
    )

    animate = _claim_card_animation(f"reselect_{message_index}")
    max_carbon = max(
        (
            safe_float_ui(option.get("carbon")) or 0
            for option in transports
        ),
        default=0,
    )

    for index, option in enumerate(transports):
        _compact_transport_card(
            option,
            message_index,
            index,
            recommended=index == 0,
            max_carbon=max_carbon,
            animate=animate,
        )

    if animate:
        components.html(COUNT_UP_SCRIPT, height=0)

def render_hotel_selection_after_transport(message_index):
    hotels = recommendation_hotels_before(
        message_index
    )

    activities = recommendation_activities_before(
        message_index
    )

    if hotels:
        st.html(
            "<div class='section-title'>Now Choose Eco Hotel</div>"
        )

        _hotel_carousel(
            hotels,
            message_index,
        )

    if activities:
        st.html(
            "<div class='section-title'>Local Experiences</div>"
        )

        render_activities(activities)

def render_buttons(
    buttons,
    message_index,
):
    current_message = (
        st.session_state.messages[message_index]
        if message_index < len(st.session_state.messages)
        else {}
    )

    current_text = str(
        current_message.get("content", "")
    ).lower()

    choosing_transport = (
        "transport options ranked" in current_text
        or any(
            parse_transport_line(line)
            for line in current_text.splitlines()
        )
    )

    choosing_hotel = (
        "now choose one of the eco hotel cards"
        in current_text
    )

    cleaned_buttons = []

    for button in buttons:
        title = button.get("title", "Option")
        payload = button.get("payload", title)

        if "/select_transport_option" in payload:
            continue

        if "/select_hotel_option" in payload:
            continue

        is_finish_button = (
            title.strip().casefold() == "finish"
            or payload.strip().casefold() in {
                "/goodbye",
                "/finish",
            }
        )

        if (
            choosing_transport
            or choosing_hotel
        ) and is_finish_button:
            continue

        cleaned_buttons.append(button)

    buttons = cleaned_buttons

    if not buttons:
        return

    if len(buttons) <= 4:
        buttons_per_row = len(buttons)
    else:
        buttons_per_row = 3

    row_key_prefix = (
        "quick_reply_options"
        if len(buttons) > 1
        else "quick_reply_row"
    )

    with st.container(
        key=f"{row_key_prefix}_{message_index}"
    ):
        for row_start in range(
            0,
            len(buttons),
            buttons_per_row,
        ):
            row_buttons = buttons[
                row_start:row_start + buttons_per_row
            ]

            columns = st.columns(len(row_buttons))

            for column_index, button in enumerate(row_buttons):
                button_index = row_start + column_index
                title = button.get("title", "Option")
                payload = button.get("payload", title)

                normalized_title = title.strip().casefold()

                button_type = (
                    "primary"
                    if normalized_title in {
                        "plan a trip",
                        "confirm all",
                        "confirm selected plan",
                    }
                    else "secondary"
                )

                button_key = (
                    f"button_{message_index}_{button_index}_"
                    f"{title}_{abs(hash(payload))}"
                )

                with columns[column_index]:
                    st.button(
                        title,
                        key=button_key,
                        type=button_type,
                        use_container_width=True,
                        on_click=submit_user_message,
                        args=(payload, title),
                    )

def parse_plan_review_text(text):
    def find(pattern, default=""):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else default

    route = find(r"Route:\s*(.+?)\s+to\s+(.+)", "")
    route_match = re.search(
        r"Route:\s*(.+?)\s+to\s+(.+)",
        text,
        re.IGNORECASE,
    )
    origin = route_match.group(1).strip() if route_match else ""
    destination = route_match.group(2).strip() if route_match else ""

    total_match = re.search(
        r"Estimated trip total:\s*€([\d.,]+),\s*(within|over) your stated budget",
        text,
        re.IGNORECASE,
    )
    total_amount = total_match.group(1) if total_match else ""
    over_budget = (
        bool(total_match)
        and total_match.group(2).lower() == "over"
    )

    experiences = []
    experiences_match = re.search(
        r"Suggested local experiences:\s*\n(.*?)(?:\n\s*\n|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if experiences_match:
        for line in experiences_match.group(1).splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                experiences.append(line)

    question_match = re.search(
        r"(Would you like[^\n]*\?)",
        text,
        re.IGNORECASE,
    )

    transport = find(r"Transport:\s*(.+)")
    transport_mode_match = re.match(
        r"([^,]+)",
        transport,
    )
    transport_price_match = re.search(
        r"(€\s*\d+(?:[.,]\d+)?)",
        transport,
    )
    carbon_match = re.search(
        r"([\d.,]+\s*kg\s*CO2e)",
        transport,
        re.IGNORECASE,
    )

    hotel = find(r"Hotel:\s*(.+)")
    hotel_parts = re.split(
        r",\s*(?=€)",
        hotel,
        maxsplit=1,
    )
    hotel_name = (
        hotel_parts[0].strip()
        if hotel_parts
        else hotel
    )
    hotel_details = (
        hotel_parts[1].strip()
        if len(hotel_parts) > 1
        else ""
    )

    return {
        "origin": origin,
        "destination": destination,
        "trip_type": find(r"Trip type:\s*(.+)"),
        "dates": find(r"Dates:\s*(.+)"),
        "transport": transport,
        "transport_mode": (
            transport_mode_match.group(1).strip()
            if transport_mode_match
            else transport
        ),
        "transport_price": (
            transport_price_match.group(1).replace(" ", "")
            if transport_price_match
            else "Not available"
        ),
        "carbon": (
            carbon_match.group(1).strip()
            if carbon_match
            else "Not available"
        ),
        "hotel": hotel,
        "hotel_name": hotel_name,
        "hotel_details": hotel_details,
        "road_distance": find(r"Road distance:\s*(.+)"),
        "driving_time": find(
            r"Estimated driving time:\s*(.+)"
        ),
        "fuel": find(r"Estimated fuel:\s*(.+)"),
        "fuel_assumption": find(
            r"Fuel assumption:\s*(.+)"
        ),
        "fuel_cost": find(
            r"Estimated fuel cost:\s*(.+)"
        ),
        "tolls": find(r"Tolls:\s*(.+)"),
        "ferry_required": find(
            r"Ferry required:\s*(.+)"
        ),
        "ferry_route": find(r"Ferry route:\s*(.+)"),
        "ferry_distance": find(
            r"Ferry crossing:\s*(.+)"
        ),
        "ferry_time": find(
            r"Estimated ferry time:\s*(.+)"
        ),
        "total_route_time": find(
            r"Total route time:\s*(.+)"
        ),
        "ferry_fare": find(r"Ferry fare:\s*(.+)"),
        "ferry_emissions": find(
            r"Ferry emissions:\s*(.+)"
        ),
        "road_route_source": find(
            r"Road route source:\s*(.+)"
        ),
        "total_amount": total_amount,
        "over_budget": over_budget,
        "experiences": experiences,
        "question": (
            question_match.group(1)
            if question_match
            else "Would you like to confirm this selected plan?"
        ),
    }


def parse_confirmed_plan_text(text):
    def find(pattern, default=""):
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        return (
            match.group(1).strip()
            if match
            else default
        )

    route_match = re.search(
        r"Route:\s*(.+?)\s+to\s+(.+)",
        text,
        re.IGNORECASE,
    )

    origin = (
        route_match.group(1).strip()
        if route_match
        else ""
    )
    destination = (
        route_match.group(2).strip()
        if route_match
        else ""
    )

    total_match = re.search(
        r"Estimated trip total:\s*€?([\d.,]+),\s*"
        r"(within|over) your stated budget",
        text,
        re.IGNORECASE,
    )

    total_amount = (
        total_match.group(1)
        if total_match
        else ""
    )
    over_budget = (
        bool(total_match)
        and total_match.group(2).lower() == "over"
    )

    experiences = []
    experiences_match = re.search(
        r"Suggested local experiences:\s*\n"
        r"(.*?)(?:\n\s*\n|This selected plan|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if experiences_match:
        for line in experiences_match.group(1).splitlines():
            experience = line.strip().lstrip("-").strip()

            if experience:
                experiences.append(experience)

    dates = find(r"Dates:\s*(.+)")
    dates_match = re.match(
        r"(.+?)\s+(?:to|–|—)\s+(.+)$",
        dates,
        re.IGNORECASE,
    )

    departure_date = (
        dates_match.group(1).strip()
        if dates_match
        else dates
    )
    return_date = (
        dates_match.group(2).strip()
        if dates_match
        else "Not available"
    )

    return {
        "mode": find(r"Selected trip plan:\s*(.+)"),
        "origin": origin,
        "destination": destination,
        "trip_type": find(r"Trip type:\s*(.+)"),
        "dates": dates,
        "departure_date": departure_date,
        "return_date": return_date,
        "transport_price": find(
            r"Transport estimate:\s*(.+)"
        ),
        "carbon": find(
            r"Transport carbon estimate:\s*(.+)"
        ),
        "accommodation": find(
            r"Accommodation:\s*(.+)"
        ),
        "road_distance": find(r"Road distance:\s*(.+)"),
        "driving_time": find(
            r"Estimated driving time:\s*(.+)"
        ),
        "fuel": find(r"Estimated fuel:\s*(.+)"),
        "fuel_assumption": find(
            r"Fuel assumption:\s*(.+)"
        ),
        "fuel_cost": find(
            r"Estimated fuel cost:\s*(.+)"
        ),
        "tolls": find(r"Tolls:\s*(.+)"),
        "ferry_required": find(
            r"Ferry required:\s*(.+)"
        ),
        "ferry_route": find(r"Ferry route:\s*(.+)"),
        "ferry_distance": find(
            r"Ferry crossing:\s*(.+)"
        ),
        "ferry_time": find(
            r"Estimated ferry time:\s*(.+)"
        ),
        "total_route_time": find(
            r"Total route time:\s*(.+)"
        ),
        "ferry_fare": find(r"Ferry fare:\s*(.+)"),
        "ferry_emissions": find(
            r"Ferry emissions:\s*(.+)"
        ),
        "road_route_source": find(
            r"Road route source:\s*(.+)"
        ),
        "total_amount": total_amount,
        "over_budget": over_budget,
        "experiences": experiences,
    }


def city_flag(city):
    city_key = str(city or "").strip().split(",", 1)[0].casefold()

    flags = {
        "istanbul": "🇹🇷",
        "paris": "🇫🇷",
        "berlin": "🇩🇪",
        "amsterdam": "🇳🇱",
        "barcelona": "🇪🇸",
        "madrid": "🇪🇸",
        "rome": "🇮🇹",
        "roma": "🇮🇹",
        "milan": "🇮🇹",
        "copenhagen": "🇩🇰",
        "london": "🇬🇧",
        "lisbon": "🇵🇹",
        "vienna": "🇦🇹",
        "wien": "🇦🇹",
        "prague": "🇨🇿",
        "zurich": "🇨🇭",
        "brussels": "🇧🇪",
        "dublin": "🇮🇪",
        "oslo": "🇳🇴",
        "stockholm": "🇸🇪",
        "athens": "🇬🇷",
        "budapest": "🇭🇺",
        "warsaw": "🇵🇱",
        "mallorca": "🇪🇸",
        "majorca": "🇪🇸",
        "palma": "🇪🇸",
        "palma de mallorca": "🇪🇸",
    }

    return flags.get(city_key, "📍")


def transport_icon(mode):
    mode_key = str(mode or "").strip().casefold()

    icons = {
        "train": "🚆",
        "bus": "🚌",
        "car": "🚗",
        "flight": "✈️",
    }

    return icons.get(mode_key, "🧭")


def google_maps_directions_url(origin, destination):
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(str(origin))}"
        f"&destination={quote_plus(str(destination))}"
        "&travelmode=driving"
    )


def build_car_route_panel(
    plan,
    origin,
    destination,
):
    selected_mode = (
        plan.get("mode")
        or plan.get("transport_mode")
        or ""
    )

    if str(selected_mode).strip().casefold() != "car":
        return ""

    ferry_required = str(
        plan.get("ferry_required") or ""
    ).strip().casefold()
    has_ferry = (
        ferry_required.startswith("yes")
        or bool(plan.get("ferry_route"))
    )

    toll_text = (
        plan.get("tolls")
        or "Check the live route"
    )
    toll_display = toll_text.split(";", 1)[0].strip()

    route_url = google_maps_directions_url(
        origin,
        destination,
    )

    source_text = (
        plan.get("road_route_source")
        or "Road route estimate"
    )

    if has_ferry:
        total_route_time = re.sub(
            r"\s*\(.*$",
            "",
            str(plan.get("total_route_time") or ""),
        ).strip()
        metrics = [
            ("🛣️", "Road distance", plan.get("road_distance")),
            ("⏱️", "Drive time", plan.get("driving_time")),
            ("🧭", "Total route time", total_route_time),
            ("⛽", "Estimated fuel", plan.get("fuel")),
            ("💶", "Fuel cost", plan.get("fuel_cost")),
            ("🌿", "Road CO2e", plan.get("carbon")),
        ]
    else:
        metrics = [
            ("🛣️", "Road distance", plan.get("road_distance")),
            ("⏱️", "Drive time", plan.get("driving_time")),
            ("⛽", "Estimated fuel", plan.get("fuel")),
            ("💶", "Fuel cost", plan.get("fuel_cost")),
            ("🌿", "Carbon estimate", plan.get("carbon")),
            ("🎟️", "Tolls", toll_display),
        ]

    metrics_html = "".join(
        (
            "<div class='car-metric'>"
            "<div class='car-metric-label'>"
            f"{icon} {html.escape(label)}"
            "</div>"
            "<div class='car-metric-value'>"
            f"{html.escape(str(value or 'Not available'))}"
            "</div>"
            "</div>"
        )
        for icon, label, value in metrics
    )

    fuel_assumption = (
        plan.get("fuel_assumption")
        or "Fuel use varies by vehicle and driving conditions."
    )

    ferry_panel_html = ""

    if has_ferry:
        ferry_route = str(
            plan.get("ferry_route") or "Vehicle ferry"
        ).strip()
        ferry_route_match = re.match(
            r"(.+?)\s+to\s+(.+)$",
            ferry_route,
            re.IGNORECASE,
        )
        departure_port = (
            ferry_route_match.group(1).strip()
            if ferry_route_match
            else "Departure port"
        )
        arrival_port = (
            ferry_route_match.group(2).strip()
            if ferry_route_match
            else "Arrival port"
        )
        ferry_fare = (
            plan.get("ferry_fare")
            or "Check a live vehicle fare and schedule"
        )
        ferry_emissions = (
            plan.get("ferry_emissions")
            or "Not included in this prototype estimate"
        )

        ferry_panel_html = f"""
<div class="ferry-route-panel">
    <div class="ferry-route-label">Ferry segment required</div>

    <div class="ferry-route-flow">
        <div class="ferry-port">
            <div class="ferry-port-label">Board with car</div>
            <div class="ferry-port-name">
                {html.escape(departure_port)}
            </div>
        </div>

        <div class="ferry-flow-icon" aria-hidden="true">&#9972;</div>

        <div class="ferry-port">
            <div class="ferry-port-label">Disembark</div>
            <div class="ferry-port-name">
                {html.escape(arrival_port)}
            </div>
        </div>
    </div>

    <div class="ferry-facts">
        <div class="ferry-fact">
            <div class="ferry-fact-label">Crossing</div>
            <div class="ferry-fact-value">
                {html.escape(str(plan.get('ferry_distance') or 'Estimate unavailable'))}
            </div>
        </div>

        <div class="ferry-fact">
            <div class="ferry-fact-label">Ferry time</div>
            <div class="ferry-fact-value">
                {html.escape(str(plan.get('ferry_time') or 'Estimate unavailable'))}
            </div>
        </div>

        <div class="ferry-fact">
            <div class="ferry-fact-label">Vehicle fare</div>
            <div class="ferry-fact-value">Live check required</div>
        </div>
    </div>

    <div class="ferry-disclosure">
        {html.escape(str(ferry_fare))}.
        Ferry check-in and waiting time are excluded.
        Ferry emissions: {html.escape(str(ferry_emissions))}.
    </div>
</div>
"""

    route_kicker = (
        "Driving + ferry route"
        if has_ferry
        else "Driving route"
    )
    route_badge = (
        "Car + ferry"
        if has_ferry
        else "One-way estimate"
    )
    route_link_label = (
        "Open combined route in Google Maps"
        if has_ferry
        else "Open route in Google Maps"
    )

    return f"""
<section class="car-route-panel" aria-label="Driving route estimate">
    <div class="car-route-head">
        <div>
            <div class="car-route-kicker">
                {route_kicker}
            </div>
            <div class="car-route-title">
                {html.escape(str(origin))}
                &rarr;
                {html.escape(str(destination))}
            </div>
        </div>

        <div class="car-route-badge">{route_badge}</div>
    </div>

    <div class="car-metrics-grid">
        {metrics_html}
    </div>

    {ferry_panel_html}

    <div class="car-route-assumption">
        <strong>Prototype assumption:</strong>
        {html.escape(str(fuel_assumption))}.
        Tolls{', ferry fares' if has_ferry else ''} are excluded
        from the estimated trip total.
    </div>

    <div class="car-route-footer">
        <div class="car-route-source">
            Route source: {html.escape(str(source_text))}
        </div>

        <a class="car-route-link"
           href="{html.escape(route_url)}"
           target="_blank"
           rel="noopener noreferrer">
            {route_link_label} &#8599;
        </a>
    </div>
</section>
"""


def render_confirmed_plan(text):
    plan = parse_confirmed_plan_text(text)

    origin = plan["origin"] or "Starting city"
    destination = plan["destination"] or "Destination"
    origin_flag = city_flag(origin)
    destination_flag = city_flag(destination)
    # "Train via Barcelona" still travels by train.
    confirmed_base_mode = str(
        plan["mode"]
    ).partition(" via ")[0].strip()

    is_car = confirmed_base_mode.casefold() == "car"
    has_ferry = (
        str(plan.get("ferry_required") or "")
        .strip()
        .casefold()
        .startswith("yes")
        or bool(plan.get("ferry_route"))
        or " via " in str(plan["mode"])
    )
    mode_icon = (
        f"{transport_icon(confirmed_base_mode)} · &#9972;"
        if has_ferry
        else transport_icon(confirmed_base_mode)
    )

    journey_chain_html = build_journey_chain(
        origin,
        destination,
        plan["mode"],
        plan.get("ferry_route", ""),
    )

    origin_date_html = (
        ""
        if is_car
        else (
            "<span class='confirmed-city-date'>"
            "<span class='confirmed-date-label'>Departure</span>"
            f"{html.escape(pretty_date(plan['departure_date']))}"
            "</span>"
        )
    )
    destination_date_html = (
        ""
        if is_car
        else (
            "<span class='confirmed-city-date'>"
            "<span class='confirmed-date-label'>Return</span>"
            f"{html.escape(pretty_date(plan['return_date']))}"
            "</span>"
        )
    )

    trip_meta_text = (
        f"Trip dates: {plan['dates']} · {plan['trip_type']}"
        if is_car
        else plan["trip_type"]
    )

    car_route_panel_html = build_car_route_panel(
        plan,
        origin,
        destination,
    )

    if is_car:
        confirmed_details_html = f"""
<div class="confirmed-details-grid">
    <div class="confirmed-detail hotel wide">
        <div class="confirmed-detail-label">
            🏨 Accommodation
        </div>
        <div class="confirmed-detail-value">
            {html.escape(plan['accommodation'])}
        </div>
    </div>
</div>
"""
    else:
        confirmed_details_html = f"""
<div class="confirmed-details-grid">
    <div class="confirmed-detail transport">
        <div class="confirmed-detail-label">Transport</div>
        <div class="confirmed-detail-value">
            {mode_icon}
            {html.escape(plan['mode'])}
            &middot;
            {html.escape(plan['transport_price'])}
        </div>
    </div>

    <div class="confirmed-detail carbon">
        <div class="confirmed-detail-label">
            🌿 Carbon estimate
        </div>
        <div class="confirmed-detail-value">
            {html.escape(plan['carbon'])}
        </div>
    </div>

    <div class="confirmed-detail hotel wide">
        <div class="confirmed-detail-label">
            🏨 Accommodation
        </div>
        <div class="confirmed-detail-value">
            {html.escape(plan['accommodation'])}
        </div>
    </div>
</div>
"""

    experience_chips = "".join(
        (
            "<div class='activity-pill'>"
            f"{html.escape(item)}"
            "</div>"
        )
        for item in plan["experiences"]
    ) or (
        "<div class='activity-pill'>"
        "No local experience suggestions are available."
        "</div>"
    )

    total_badge_class = (
        "plan-total-badge over-budget"
        if plan["over_budget"]
        else "plan-total-badge"
    )
    total_row_class = (
        "plan-total-row over-budget"
        if plan["over_budget"]
        else "plan-total-row"
    )
    budget_label = (
        "Over budget"
        if plan["over_budget"]
        else (
            "Before ferry fare"
            if has_ferry
            else "Within budget"
        )
    )
    total_label = (
        "Estimated subtotal"
        if has_ferry
        else "Estimated total"
    )

    st.html(f"""
<section class="summary-box confirmed-plan-card"
         aria-label="Selected trip plan">
    <div class="confirmed-plan-banner">
        <div>
            <div class="confirmed-plan-kicker">
                Confirmed itinerary
            </div>

            <div class="confirmed-plan-title">
                Your trip plan is ready
            </div>
        </div>

        <div class="confirmed-status-badge">
            <span class="confirmed-status-mark">&#10003;</span>
            Confirmed
        </div>
    </div>

    <div class="confirmed-plan-body">
        <div class="confirmed-route-card">
            <div class="confirmed-city">
                <span class="confirmed-flag" aria-hidden="true">
                    {origin_flag}
                </span>
                <span class="confirmed-city-label">From</span>
                <span class="confirmed-city-name">
                    {html.escape(origin)}
                </span>
                {origin_date_html}
            </div>

            <div class="confirmed-route-track" aria-hidden="true">
                <span class="confirmed-route-dot"></span>
                <span class="confirmed-route-line"></span>
                <span class="confirmed-mode-icon">{mode_icon}</span>
                <span class="confirmed-route-line"></span>
                <span class="confirmed-route-dot"></span>
            </div>

            <div class="confirmed-city destination">
                <span class="confirmed-flag" aria-hidden="true">
                    {destination_flag}
                </span>
                <span class="confirmed-city-label">To</span>
                <span class="confirmed-city-name">
                    {html.escape(destination)}
                </span>
                {destination_date_html}
            </div>
        </div>

        {journey_chain_html}

        <div class="confirmed-trip-meta">
            {html.escape(trip_meta_text)}
        </div>

        {car_route_panel_html}

        {confirmed_details_html}

        <div class="{total_row_class}">
            <div class="plan-total-amount">
                {total_label}:
                &euro;{html.escape(plan['total_amount'])}
            </div>

            <div class="{total_badge_class}">
                {budget_label}
            </div>
        </div>

        <div class="plan-section-label">
            Suggested local experiences
        </div>

        <div class="activity-list confirmed-experiences">
            {experience_chips}
        </div>

        <div class="plan-question">
            This plan is ready to be changed, shared with an
            advisor, or finished.
        </div>
    </div>
</section>
""")


def render_trip_details_review(text):
    def find(pattern, default=""):
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        return (
            match.group(1).strip()
            if match
            else default
        )

    was_updated = (
        "change has been saved"
        in text.lower()
    )

    route_match = re.search(
        r"Route:\s*(.+?)\s+to\s+(.+)",
        text,
        re.IGNORECASE,
    )

    origin = (
        route_match.group(1).strip()
        if route_match
        else ""
    )

    destination = (
        route_match.group(2).strip()
        if route_match
        else ""
    )

    # Regex işlemleri f-string dışında hazırlanır.
    trip_type = html.escape(
        find(r"Trip type:\s*(.+)")
    )
    departure = html.escape(
        pretty_date(find(r"Departure:\s*(.+)"))
    )
    return_date = html.escape(
        pretty_date(find(r"Return:\s*(.+)"))
    )

    travel_dates = (
        f"{departure} &rarr; {return_date}"
        if departure and return_date
        else (departure or return_date or "Not set")
    )
    budget = html.escape(
        find(r"Budget:\s*€?([\d.,]+)")
    )
    sustainability = html.escape(
        find(r"Sustainability priority:\s*(.+)").capitalize()
    )

    change_badge = (
        "<div class='plan-total-badge' "
        "style='margin-bottom:12px;'>"
        "Change saved"
        "</div>"
        if was_updated
        else ""
    )

    st.html(f"""
<div class="summary-box">
    {change_badge}

    <div class="summary-title">
        Review your trip details
    </div>

    <div class="plan-route">
        <span>{html.escape(origin)}</span>
        <span class="plan-route-arrow">&#8594;</span>
        <span>{html.escape(destination)}</span>
    </div>

    <div class="plan-subtitle">
        {trip_type}
    </div>

    <div class="plan-facts-grid">
        <div class="plan-fact-card wide">
            <div class="plan-fact-label">Travel dates</div>
            <div class="plan-fact-value">📅 {travel_dates}</div>
        </div>

        <div class="plan-fact-card">
            <div class="plan-fact-label">Budget</div>
            <div class="plan-fact-value">&euro;{budget}</div>
        </div>

        <div class="plan-fact-card">
            <div class="plan-fact-label">
                Sustainability priority
            </div>
            <div class="plan-fact-value">
                🌿 {sustainability}
            </div>
        </div>
    </div>

    <div class="plan-question">
        Are all these details correct?
    </div>
</div>
""")


def render_plan_review(text):
    plan = parse_plan_review_text(text)

    # "Train via Barcelona" still travels by train.
    review_base_mode = str(
        plan["transport_mode"]
    ).partition(" via ")[0].strip()

    mode_icon = transport_icon(review_base_mode)
    is_car = review_base_mode.casefold() == "car"
    has_ferry = (
        str(plan.get("ferry_required") or "")
        .strip()
        .casefold()
        .startswith("yes")
        or bool(plan.get("ferry_route"))
        or " via " in str(plan["transport_mode"])
    )

    journey_chain_html = build_journey_chain(
        plan["origin"],
        plan["destination"],
        plan["transport_mode"],
        plan.get("ferry_route", ""),
    )

    hotel_details_html = (
        "<div class='plan-highlight-subvalue'>"
        f"{html.escape(plan['hotel_details'])}"
        "</div>"
        if plan["hotel_details"]
        else ""
    )

    hotel_card_html = f"""
<div class="plan-highlight-card hotel">
    <div class="plan-highlight-icon" aria-hidden="true">
        🏨
    </div>
    <div class="plan-highlight-copy">
        <div class="plan-highlight-label">Hotel</div>
        <div class="plan-highlight-value">
            {html.escape(plan['hotel_name'])}
        </div>
        {hotel_details_html}
    </div>
</div>
"""

    car_route_panel_html = build_car_route_panel(
        plan,
        plan["origin"],
        plan["destination"],
    )

    if is_car:
        plan_highlights_html = f"""
{car_route_panel_html}
<div class="plan-highlights-grid">
    {hotel_card_html}
</div>
"""
        plan_subtitle_text = (
            f"{plan['trip_type']} · Trip dates: "
            f"{pretty_date_range(plan['dates'])}"
        )
    else:
        plan_highlights_html = f"""
<div class="plan-highlights-grid">
    <div class="plan-highlight-card transport">
        <div class="plan-highlight-icon" aria-hidden="true">
            {mode_icon}
        </div>
        <div class="plan-highlight-copy">
            <div class="plan-highlight-label">Transport</div>
            <div class="plan-highlight-value">
                {html.escape(plan['transport_mode'])}
            </div>
            <div class="plan-highlight-subvalue">
                {html.escape(plan['transport_price'])}
            </div>
        </div>
    </div>

    <div class="plan-highlight-card carbon">
        <div class="plan-highlight-icon" aria-hidden="true">
            🌿
        </div>
        <div class="plan-highlight-copy">
            <div class="plan-highlight-label">Carbon estimate</div>
            <div class="plan-highlight-value">
                {html.escape(plan['carbon'])}
            </div>
            <div class="plan-highlight-subvalue">
                Estimated transport CO2e
            </div>
        </div>
    </div>

    {hotel_card_html}
</div>
"""
        plan_subtitle_text = (
            f"{plan['trip_type']} · "
            f"{pretty_date_range(plan['dates'])}"
        )

    experience_chips = "".join(
        f"<div class='activity-pill'>{html.escape(item)}</div>"
        for item in plan["experiences"]
    ) or (
        "<div class='activity-pill'>"
        "Local low-impact experience suggestions are not "
        "available for this destination yet."
        "</div>"
    )

    total_badge_class = (
        "plan-total-badge over-budget"
        if plan["over_budget"]
        else "plan-total-badge"
    )
    total_row_class = (
        "plan-total-row over-budget"
        if plan["over_budget"]
        else "plan-total-row"
    )
    budget_label = (
        "Over budget"
        if plan["over_budget"]
        else (
            "Before ferry fare"
            if has_ferry
            else "Within budget"
        )
    )
    total_label = (
        "Estimated subtotal"
        if has_ferry
        else "Estimated total"
    )

    st.html(f"""
<div class="summary-box">
    <div class="summary-title">Review your selected trip plan</div>

    {journey_chain_html}
    <div class="plan-subtitle">
        {html.escape(plan_subtitle_text)}
    </div>

    {plan_highlights_html}

    <div class="{total_row_class}">
        <div class="plan-total-amount">
            {total_label}: &euro;{html.escape(plan['total_amount'])}
        </div>
        <div class="{total_badge_class}">{budget_label}</div>
    </div>

    <div class="plan-section-label">Suggested local experiences</div>
    <div class="activity-list" style="margin-left:0;max-width:none;">
        {experience_chips}
    </div>

    <div class="plan-question">{html.escape(plan['question'])}</div>
</div>
""")


def render_handover_message(
    text,
    custom,
):
    context = custom.get("context", {})
    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    if current_user:
        context = {
            "Logged-in user": current_user.get(
                "display_name",
                "User",
            ),
            "User email": current_user.get(
                "email",
                "Not available",
            ),
            **context,
        }
    latest_request = custom.get(
        "latest_user_request",
        "Not available",
    )
    history = custom.get(
        "conversation_history",
        [],
    )
    privacy_note = custom.get(
        "privacy_note",
        "",
    )
    advisor_summary = custom.get(
        "advisor_summary",
        "",
    )

    context_rows = "".join(
        (
            "<div class='context-label'>"
            f"{html.escape(str(label))}"
            "</div>"
            "<div class='context-value'>"
            f"{html.escape(str(value))}"
            "</div>"
        )
        for label, value in context.items()
    )

    st.html(f"""
<div class="handover-box">
    <div class="handover-title">
        Simulated Advisor Handover
    </div>

    <div class="handover-status">
        Simulated handover prepared
    </div>

    <div class="context-grid">
        {context_rows}
        <div class="context-label">Latest request</div>
        <div class="context-value">
            {html.escape(str(latest_request))}
        </div>
    </div>
</div>
""")

    if (
        advisor_summary
        and advisor_summary != "Not available"
    ):
        st.info(
            "Advisor summary:\n\n"
            + str(advisor_summary)
        )

    with st.expander(
        "View full conversation history",
        expanded=False,
    ):
        if not history:
            st.write(
                "No conversational messages were available."
            )

        for item in history:
            speaker = html.escape(
                str(item.get("speaker", "Message"))
            )
            message_text = html.escape(
                str(item.get("message", ""))
            ).replace("\n", "<br>")

            st.html(f"""
<div class="history-item">
    <div class="history-speaker">
        {speaker}
    </div>
    {message_text}
</div>
""")

    if privacy_note:
        st.info(
            f"Privacy: {privacy_note}"
        )

def render_step_message(text):
    lower_text = text.lower()

    if (
        lower_text.startswith("selected transport:")
        and "eco hotel cards" in lower_text
    ):
        first_line = text.splitlines()[0]
        selected_transport = first_line.split(":", 1)[-1].strip()

        st.html(f"""
<section class="step-box" aria-label="Next planning step">
    <div class="step-kicker">Transport selected</div>
    <div class="step-title">
        {html.escape(selected_transport)}
    </div>
    <div class="step-copy">
        Now choose one of the eco hotel cards to build your final trip plan.
    </div>
</section>
""")
        return True

    return False

def render_bot_message(
    message,
    message_index,
):
    text = message["content"]
    lower_text = text.lower()
    custom = message.get("custom") or {}

    if custom.get("type") == "human_handover":
        render_handover_message(
            text,
            custom,
        )

    elif lower_text.startswith("selected trip plan:"):
        render_confirmed_plan(text)

    elif "review your selected trip plan" in lower_text:
        render_plan_review(text)

    elif (
        "please review your trip details" in lower_text
        or "please review your updated trip details" in lower_text
    ):
        render_trip_details_review(text)

    elif (
        "human travel advisor" in lower_text
        or "human advisor handover" in lower_text
        or "context package" in lower_text
        or "trip context for the advisor" in lower_text
    ):
        safe_text = html.escape(text).replace(
            "\n",
            "<br>",
        )

        st.html(f"""
<div class="handover-box">
    <div class="handover-title">
        Simulated Advisor Handover
    </div>

    {safe_text}
</div>
""")

    elif (
        "transport options ranked" in lower_text
        or any(
            parse_transport_line(line)
            for line in text.splitlines()
        )
    ):
        render_recommendations(
            text,
            message_index,
        )

    elif render_step_message(text):
        if "now choose one of the eco hotel cards" in lower_text:
            render_hotel_selection_after_transport(
                message_index
            )
    else:
        safe_text = html.escape(text).replace(
            "\n",
            "<br>",
        )

        st.html(f"""
<article class="chat-row" aria-label="Assistant message">
    <div class="avatar-bot" aria-hidden="true">E</div>

    <div class="message-box bot-message">
        {safe_text}
    </div>
</article>
""")

        if (
            "choose a new transport option"
            in lower_text
        ):
            render_transport_selection_after_change(
                message_index
            )

        if (
            "now choose one of the eco hotel cards"
            in lower_text
            or "choose a new eco hotel"
            in lower_text
            or "choose a new hotel"
            in lower_text
        ):
            render_hotel_selection_after_transport(
                message_index
            )


def render_user_message(message):
    content = str(message["content"])
    safe_text = html.escape(content)

    current_user = st.session_state.get(
        "authenticated_user",
        {},
    ) or {}

    display_name = (
        current_user.get("display_name")
        or current_user.get("email")
        or "User"
    )

    user_initial = str(display_name).strip()[:1].upper() or "U"

    if content.lower().startswith((
        "selected transport:",
        "selected hotel:",
    )):
        st.html(f"""
<div class="selection-chip-row" aria-label="User selection">
    <div class="selection-chip">
        {safe_text}
    </div>
</div>
""")
        return

    st.html(f"""
<article class="chat-row user-row" aria-label="User message">
    <div class="avatar-user" aria-hidden="true">
        {html.escape(user_initial)}
    </div>

    <div class="message-box user-message">
        {safe_text}
    </div>
</article>
""")

def render_trip_progress():
    step = 1
    label = "Trip details"

    if st.session_state.conversation_finished:
        step = 5
        label = "Complete"

    else:
        for message in reversed(
            st.session_state.messages
        ):
            text = str(
                message.get("content", "")
            ).strip().lower()

            if any(
                phrase in text
                for phrase in (
                    "which trip detail would you like to change",
                    "please enter the new",
                    "would you like to keep this change",
                )
            ):
                step = 1
                label = "Trip details"
                break

            if text.startswith(
                "selected trip plan:"
            ):
                step = 5
                label = "Complete"
                break

            if (
                text.startswith(
                    "review your selected trip plan:"
                )
                or text.startswith("selected hotel:")
            ):
                step = 4
                label = "Review"
                break

            if (
                "now choose one of the eco hotel cards"
                in text
                or "choose a new eco hotel" in text
                or "choose a new hotel" in text
                or text.startswith("selected transport:")
            ):
                step = 3
                label = "Hotel"
                break

            if (
                "transport options ranked" in text
                or "choose a new transport option" in text
            ):
                step = 2
                label = "Transport"
                break

    progress_percent = step * 20

    st.html(f"""
    <div class="trip-progress">
        <div class="trip-progress-meta">
            <strong>Step {step} of 5</strong>
            <span>{html.escape(label)}</span>
        </div>

        <div
            class="trip-progress-track"
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow="{progress_percent}"
        >
            <div
                class="trip-progress-fill"
                style="width: {progress_percent}%"
            ></div>
        </div>
    </div>
    """)

def render_trip_summary_rail():
    slots = fetch_trip_slots()

    origin = str(slots.get("origin") or "").strip()
    destination = str(slots.get("destination") or "").strip()
    trip_type = str(slots.get("trip_type") or "").strip()
    depart = format_summary_date(slots.get("departure_date"))
    return_on = format_summary_date(slots.get("return_date"))
    budget_raw = slots.get("budget")
    priority = str(slots.get("sustainability_level") or "").strip()
    transport = str(slots.get("selected_transport_mode") or "").strip()
    hotel = str(slots.get("selected_hotel_name") or "").strip()

    try:
        budget = f"€{float(budget_raw):.0f}" if budget_raw else ""
    except (TypeError, ValueError):
        budget = ""

    def endpoint(label, city):
        pending = not city
        flag = city_flag(city) if city else "○"
        value = html.escape(city) if city else "Not set yet"
        css = "pending" if pending else ""
        return flag, label, value, css

    origin_flag, _, origin_value, origin_css = endpoint("From", origin)
    dest_flag, _, dest_value, dest_css = endpoint("To", destination)

    dates_value = "Not set yet"
    dates_pending = "pending"
    if depart and return_on:
        dates_value = f"{html.escape(depart)} &rarr; {html.escape(return_on)}"
        dates_pending = ""
    elif depart:
        dates_value = html.escape(depart)
        dates_pending = ""

    def fact(icon, label, value):
        pending = not value
        shown = value if value else "Not set yet"
        css = "pending" if pending else ""
        return f"""
        <div class="trip-rail-fact">
            <div class="trip-rail-fact-icon" aria-hidden="true">{icon}</div>
            <div>
                <div class="trip-rail-fact-label">{label}</div>
                <div class="trip-rail-fact-value {css}">{shown}</div>
            </div>
        </div>
        """

    facts = [
        f"""
        <div class="trip-rail-fact">
            <div class="trip-rail-fact-icon" aria-hidden="true">📅</div>
            <div>
                <div class="trip-rail-fact-label">Dates</div>
                <div class="trip-rail-fact-value {dates_pending}">{dates_value}</div>
            </div>
        </div>
        """,
        fact("🧭", "Trip type", html.escape(humanize_slot(trip_type)) if trip_type else ""),
        fact("💰", "Budget", html.escape(budget)),
        fact("🌿", "Sustainability", html.escape(humanize_slot(priority)) if priority else ""),
    ]

    if transport:
        # "Train via Barcelona" keeps its lower-case "via" and the icon
        # comes from the underlying mode.
        transport_base, _, transport_port = transport.partition(" via ")
        transport_label = humanize_slot(transport_base)

        if transport_port:
            transport_label += f" via {transport_port.strip()}"

        facts.append(
            fact(
                transport_icon(transport_base),
                "Transport",
                html.escape(transport_label),
            )
        )

    if hotel:
        facts.append(fact("🏨", "Stay", html.escape(hotel)))

    st.html(f"""
<aside class="trip-rail" aria-label="Trip summary so far">
    <div class="trip-rail-eyebrow">Your trip</div>
    <div class="trip-rail-title">Plan so far</div>

    <div class="trip-rail-route">
        <div class="trip-rail-pin" aria-hidden="true">{origin_flag}</div>
        <div>
            <div class="trip-rail-endpoint-label">From</div>
            <div class="trip-rail-endpoint-value {origin_css}">{origin_value}</div>
        </div>

        <div class="trip-rail-connector" aria-hidden="true"><span></span></div>
        <div></div>

        <div class="trip-rail-pin" aria-hidden="true">{dest_flag}</div>
        <div>
            <div class="trip-rail-endpoint-label">To</div>
            <div class="trip-rail-endpoint-value {dest_css}">{dest_value}</div>
        </div>
    </div>

    <div class="trip-rail-divider"></div>

    <div class="trip-rail-facts">
        {"".join(facts)}
    </div>

    <div class="trip-rail-foot">
        Fills in as you answer. Prices and carbon are estimates.
    </div>
</aside>
""")


with st.sidebar:
    render_user_panel()

    st.html('<div class="sidebar-section-label">Good to know</div>')

    with st.expander(
        "How it works",
        expanded=False,
    ):
        st.markdown("""
1. **Tell me your route and dates** — where you're starting, where you're headed, and when.
2. **I compare your options** — train, bus, car and flight, ranked by price, travel time and carbon footprint.
3. **Pick a plan** — then I suggest eco-friendly stays and things to do at your destination.

Carbon levels are shown as **green**, **amber** or **red** so you can weigh cost against climate impact at a glance.
""")

    with st.expander(
        "Privacy & accessibility",
        expanded=False,
    ):
        st.markdown("""
**Your data**

- Only the trip details needed for planning are ever requested.
- Please don't enter passport, payment, health or other sensitive data.
- "Plan a new trip" clears the current conversation and starts fresh.

**Accessibility**

- Every control works with the keyboard.
- Messages and results carry screen-reader labels.
- Carbon information is shown as text as well as colour, so it never relies on colour alone.
""")

    st.html(
        '<div class="sidebar-footnote">'
        "🌿 Eco-Travel Advisor · lower-impact trips across Europe"
        "</div>"
    )


render_brand_header(
    "Compare lower-impact transport, thoughtful stays, "
    "and local experiences in one guided plan."
)

st.html("""
<div class="privacy-note">
    <strong>Privacy note:</strong>
    Only enter information needed to plan the trip.
    Do not include sensitive personal data.
</div>
""")

render_trip_progress()

render_trip_summary_rail()

for message_index, message in enumerate(
    st.session_state.messages
):
    is_latest_message = (
        message_index == len(st.session_state.messages) - 1
    )

    # Marks where the newest reply begins, so a tall answer such as a
    # list of transport cards is scrolled to its first option instead
    # of its last one.
    if is_latest_message:
        st.html(
            '<div id="latest-response-start" '
            'aria-hidden="true"></div>'
        )

    if message["role"] == "user":
        render_user_message(message)
    else:
        render_bot_message(
            message,
            message_index,
        )

        if is_latest_message:
            render_buttons(
                message.get("buttons", []),
                message_index,
            )

    if is_latest_message:
        st.html(
            '<div id="latest-response-anchor" '
            'aria-hidden="true"></div>'
        )


render_date_picker()


if st.session_state.handover_active:
    st.info(
        "Simulated advisor handover is ready. "
        "Reset the chat to begin a new conversation."
    )

if st.session_state.conversation_finished:
    st.success(
        "Conversation finished. You can start another trip "
        "whenever you are ready."
    )

    if st.button(
        "Plan another trip",
        key="plan_another_trip",
        use_container_width=True,
        type="primary",
    ):
        reset_chat()
        st.rerun()


date_selection_active = (
    latest_requested_date_type() is not None
    and not st.session_state.handover_active
    and not st.session_state.conversation_finished
)

latest_message = (
    st.session_state.messages[-1]
    if st.session_state.messages
    else {}
)

latest_button_titles = {
    button.get("title", "")
    for button in latest_message.get("buttons", [])
}

start_button_active = (
    latest_message.get("role") == "assistant"
    and latest_button_titles == {"Plan a trip"}
)

post_result_action_active = (
    latest_message.get("role") == "assistant"
    and "Finish" in latest_button_titles
)

transport_selection_active = (
    latest_message.get("role") == "assistant"
    and (
        "choose a new transport option"
        in str(latest_message.get("content", "")).lower()
        or "transport options ranked"
        in str(latest_message.get("content", "")).lower()
    )
)

hotel_selection_active = (
    latest_message.get("role") == "assistant"
    and (
        "now choose one of the eco hotel cards"
        in str(latest_message.get("content", "")).lower()
        or "choose a new eco hotel"
        in str(latest_message.get("content", "")).lower()
        or "choose a new hotel"
        in str(latest_message.get("content", "")).lower()
    )
)

detail_selection_active = (
    latest_message.get("role") == "assistant"
    and "which trip detail would you like to change"
    in str(latest_message.get("content", "")).lower()
)

review_confirmation_active = (
    latest_message.get("role") == "assistant"
    and "are all these details correct"
    in str(latest_message.get("content", "")).lower()
)

selected_plan_review_active = (
    latest_message.get("role") == "assistant"
    and (
        "review your selected trip plan"
        in str(
            latest_message.get("content", "")
        ).lower()
        or "Confirm selected plan"
        in latest_button_titles
    )
)

change_confirmation_active = (
    latest_message.get("role") == "assistant"
    and "would you like to keep this change"
    in str(latest_message.get("content", "")).lower()
)

trip_type_selection_active = (
    latest_message.get("role") == "assistant"
    and "what kind of trip are you planning"
    in str(latest_message.get("content", "")).lower()
)


input_hidden = (
    st.session_state.handover_active
    or st.session_state.conversation_finished
    or date_selection_active
    or start_button_active
    or post_result_action_active
    or hotel_selection_active
    or detail_selection_active
    or trip_type_selection_active
    or review_confirmation_active
    or change_confirmation_active
    or transport_selection_active
    or selected_plan_review_active
)

if input_hidden:
    st.html("""
<style>
[data-testid="stMainBlockContainer"],
.block-container {
    padding-bottom: 1.5rem !important;
}
</style>
""")

components.html(
    """
<script>
(function () {
    const parentDocument = window.parent.document;

    function mainScrollContainer() {
        const candidates = [
            'section[data-testid="stAppScrollToBottomContainer"]',
            'section.stMain',
            'section[data-testid="stMain"]',
            '[data-testid="stAppViewContainer"] section.main',
            'section.main',
        ];

        for (const selector of candidates) {
            const el = parentDocument.querySelector(selector);
            if (el && el.scrollHeight > el.clientHeight + 4) {
                return el;
            }
        }

        return parentDocument.scrollingElement
            || parentDocument.documentElement;
    }

    // Bring the start of the newest reply to the top of the view.
    // Short replies get clamped to the bottom by the browser, so they
    // still behave the way a chat is expected to, while a tall reply
    // such as a list of transport cards opens on its first option.
    // Instant (not smooth) keeps the view steady as late content
    // reflows in, instead of firing competing animations that bounce.
    function pinToBottom() {
        const container = mainScrollContainer();

        if (!container) {
            return;
        }

        const anchor = parentDocument.getElementById(
            "latest-response-start"
        );

        if (!anchor) {
            container.scrollTop = container.scrollHeight;
            return;
        }

        const anchorTop = anchor.getBoundingClientRect().top;
        const containerTop = container.getBoundingClientRect().top;

        container.scrollTop += (anchorTop - containerTop) - 12;
    }

    // A few instant re-pins cover late-rendering buttons, transport
    // cards and the date picker without any visible jitter.
    window.requestAnimationFrame(function () {
        pinToBottom();
        [150, 400, 800].forEach(function (delay) {
            setTimeout(pinToBottom, delay);
        });
    });
})();
</script>
""",
    height=0,
)


if not input_hidden:
    st.chat_input(
        "Type your travel request here...",
        key="main_chat_input",
        on_submit=submit_chat_input,
    )
