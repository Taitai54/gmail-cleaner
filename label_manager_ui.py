#!/usr/bin/env python3
"""Gmail Label Manager — Streamlit UI"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gmail Label Manager",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES = ['https://www.googleapis.com/auth/gmail.labels']
CREDS_DIR = Path(__file__).parent
CREDS_FILE = CREDS_DIR / 'credentials.json'
TOKEN_FILE = CREDS_DIR / 'token_labels.json'

# ── Auth ──────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


# ── Data helpers ──────────────────────────────────────────────────────────────
def load_labels(service):
    result = service.users().labels().list(userId='me').execute()
    return sorted(
        [l for l in result.get('labels', []) if l['type'] == 'user'],
        key=lambda l: l['name'].lower(),
    )


def get_children(labels, parent_name):
    return [l for l in labels if l['name'].startswith(parent_name + '/')]


def api_rename(service, labels, old_name, new_name):
    target = next((l for l in labels if l['name'] == old_name), None)
    if not target:
        return False, f"Label not found: '{old_name}'"
    service.users().labels().update(
        userId='me', id=target['id'], body={**target, 'name': new_name}
    ).execute()
    for child in get_children(labels, old_name):
        new_child = new_name + child['name'][len(old_name):]
        service.users().labels().update(
            userId='me', id=child['id'], body={**child, 'name': new_child}
        ).execute()
    return True, f"Renamed to '{new_name}'"


def api_delete(service, labels, label_name, cascade=False):
    target = next((l for l in labels if l['name'] == label_name), None)
    if not target:
        return False, f"Label not found: '{label_name}'"
    children = get_children(labels, label_name)
    if children and not cascade:
        return False, f"Has {len(children)} child label(s) — enable cascade to delete all."
    for child in children:
        service.users().labels().delete(userId='me', id=child['id']).execute()
    service.users().labels().delete(userId='me', id=target['id']).execute()
    suffix = f" + {len(children)} children" if children else ""
    return True, f"Deleted '{label_name}'{suffix}"


def api_create(service, name):
    service.users().labels().create(userId='me', body={'name': name}).execute()
    return True, f"Created '{name}'"


# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1100px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder { color: rgba(255,255,255,0.3) !important; }
[data-testid="stSidebar"] .stTextInput input:focus {
    border-color: rgba(99,102,241,0.6) !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.15) !important;
}

/* Tree buttons */
[data-testid="stSidebar"] .stButton button {
    background: transparent !important;
    border: none !important;
    border-radius: 6px !important;
    text-align: left !important;
    padding: 5px 10px !important;
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    font-family: 'Inter', monospace !important;
    transition: all 0.12s !important;
    margin-bottom: 1px !important;
    white-space: pre !important;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,0.08) !important;
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: rgba(99,102,241,0.25) !important;
    border-left: 3px solid #6366f1 !important;
    color: #fff !important;
    font-weight: 600 !important;
}

/* Refresh button */
[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] .stButton button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #94a3b8 !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    padding: 4px 10px !important;
    text-align: center !important;
}

/* ── Main area ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4px;
}
.page-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}
.page-sub { font-size: 0.82rem; color: #64748b; margin-bottom: 20px; }

.stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78rem;
    color: #64748b;
    margin-right: 6px;
}
.stat-pill b { color: #0f172a; }

.divider { border: none; border-top: 1px solid #e2e8f0; margin: 12px 0 20px; }

/* ── Selection header ── */
.sel-header {
    background: linear-gradient(135deg, #f0f4ff 0%, #fafafa 100%);
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.sel-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e1b4b;
}
.sel-path {
    font-size: 0.8rem;
    color: #6366f1;
    margin-top: 2px;
}
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 8px;
}
.badge-children { background: #fef3c7; color: #92400e; }
.badge-root     { background: #dbeafe; color: #1e40af; }

/* ── Action cards ── */
.card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 20px 16px;
    margin-bottom: 14px;
    transition: box-shadow 0.15s;
}
.card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.card-title {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
}
.card-rename { border-top: 3px solid #6366f1; }
.card-rename .card-title { color: #6366f1; }
.card-move   { border-top: 3px solid #10b981; }
.card-move .card-title   { color: #10b981; }
.card-danger { border-top: 3px solid #ef4444; }
.card-danger .card-title { color: #ef4444; }
.card-create { border-top: 3px solid #3b82f6; }
.card-create .card-title { color: #3b82f6; }

.card-note {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 6px;
}
.danger-note {
    background: #fef2f2;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.8rem;
    color: #b91c1c;
    margin-bottom: 10px;
}
.confirm-bar {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 0.84rem;
    color: #9a3412;
    font-weight: 500;
}

/* ── Flash messages ── */
.flash-ok  { background:#f0fdf4; color:#166534; border-left:4px solid #22c55e;
             border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85rem; }
.flash-err { background:#fef2f2; color:#991b1b; border-left:4px solid #ef4444;
             border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:0.85rem; }

/* ── Welcome ── */
.welcome {
    text-align: center;
    padding: 64px 32px;
    color: #94a3b8;
}
.welcome-icon { font-size: 3.5rem; margin-bottom: 16px; }
.welcome h2 { color: #1e293b; font-size: 1.25rem; margin-bottom: 8px; }
.welcome p  { font-size: 0.88rem; max-width: 360px; margin: 0 auto; }

/* Fix selectbox & input in main area */
.stSelectbox > div > div { border-radius: 8px !important; }
.stTextInput input { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    'selected': None,
    'confirm_delete': False,
    'cascade': False,
    'labels': None,
    'flash': None,
    'flash_type': 'ok',
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def flash(msg, kind='ok'):
    st.session_state.flash = msg
    st.session_state.flash_type = kind


def refresh():
    st.session_state.labels = load_labels(service)


# ── Bootstrap ─────────────────────────────────────────────────────────────────
service = get_service()

if st.session_state.labels is None:
    refresh()

labels = st.session_state.labels

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 4px 14px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:14px">
        <div style="font-size:1.15rem;font-weight:700;color:#f1f5f9;letter-spacing:-0.02em">
            📧 Label Manager
        </div>
        <div style="font-size:0.7rem;color:rgba(255,255,255,0.3);margin-top:2px;letter-spacing:0.05em;text-transform:uppercase">
            Gmail
        </div>
    </div>
    """, unsafe_allow_html=True)

    search = st.text_input("search", placeholder="🔍  Search labels…", label_visibility="collapsed", key="search_box")

    if st.button("↻  Refresh labels", use_container_width=True, key="btn_refresh"):
        refresh()
        st.session_state.selected = None
        st.session_state.confirm_delete = False
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    filtered = [l for l in labels if search.lower() in l['name'].lower()] if search else labels

    if not filtered:
        st.markdown("<div style='color:rgba(255,255,255,0.3);font-size:0.78rem;padding:6px 4px'>No labels match</div>", unsafe_allow_html=True)
    else:
        for label in filtered:
            parts = label['name'].split('/')
            depth = len(parts) - 1
            indent = '  ' * depth
            prefix = '└ ' if depth > 0 else '▸ '
            display = f"{indent}{prefix}{parts[-1]}"
            kind = "primary" if st.session_state.selected == label['name'] else "secondary"
            if st.button(display, key=f"lbl_{label['id']}", use_container_width=True, type=kind):
                st.session_state.selected = label['name']
                st.session_state.confirm_delete = False
                st.session_state.cascade = False
                st.session_state.flash = None
                st.rerun()

    # ── Create label ──
    st.markdown("""
    <div style="margin-top:24px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08)">
        <div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;
                    color:rgba(255,255,255,0.3);margin-bottom:8px">New Label</div>
    </div>
    """, unsafe_allow_html=True)

    new_name = st.text_input("new_label", placeholder="e.g. Work/Projects/Q3", label_visibility="collapsed", key="new_label_name")
    if st.button("＋  Create label", use_container_width=True, key="btn_create"):
        if new_name.strip():
            ok, msg = api_create(service, new_name.strip())
            refresh()
            flash(msg, 'ok' if ok else 'err')
            st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
nested_count = sum(1 for l in labels if '/' in l['name'])

st.markdown(f"""
<div class="page-header">
    <span style="font-size:2rem">📧</span>
    <div>
        <div class="page-title">Gmail Label Manager</div>
    </div>
</div>
<div class="page-sub">
    <span class="stat-pill"><b>{len(labels)}</b> total labels</span>
    <span class="stat-pill"><b>{nested_count}</b> nested</span>
    <span class="stat-pill"><b>{len(labels) - nested_count}</b> root</span>
</div>
<hr class="divider">
""", unsafe_allow_html=True)

# Flash message
if st.session_state.flash:
    css = 'flash-ok' if st.session_state.flash_type == 'ok' else 'flash-err'
    icon = '✓' if st.session_state.flash_type == 'ok' else '✗'
    st.markdown(f'<div class="{css}">{icon}  {st.session_state.flash}</div>', unsafe_allow_html=True)
    st.session_state.flash = None

selected = st.session_state.selected

if not selected:
    st.markdown("""
    <div class="welcome">
        <div class="welcome-icon">📂</div>
        <h2>Select a label from the sidebar</h2>
        <p>Click any label on the left to rename, move, or delete it.
           Use the search box to filter, or create a new label at the bottom of the sidebar.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    target = next((l for l in labels if l['name'] == selected), None)

    if not target:
        st.warning("This label no longer exists. Click Refresh in the sidebar.")
    else:
        children = get_children(labels, selected)
        parts = selected.split('/')
        leaf = parts[-1]
        parent_path = ' › '.join(parts[:-1]) if len(parts) > 1 else None

        # ── Selection header ──
        location = f"📁 {parent_path}" if parent_path else "📁 Root level"
        children_badge = f'<span class="badge badge-children">⚠ {len(children)} children</span>' if children else '<span class="badge badge-root">Root</span>' if not parent_path else ''
        st.markdown(f"""
        <div class="sel-header">
            <div style="display:flex;align-items:center;gap:6px">
                <span class="sel-name">🏷 {leaf}</span>
                {children_badge}
            </div>
            <div class="sel-path">{location}</div>
            <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;font-family:monospace">{selected}</div>
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns(2, gap="medium")

        # ── Rename ────────────────────────────────────────────────────────────
        with col_left:
            st.markdown('<div class="card card-rename"><div class="card-title">✏️ Rename</div>', unsafe_allow_html=True)
            new_full_name = st.text_input(
                "Full label name",
                value=selected,
                key="rename_val",
                help="Use / for nesting. e.g. Work/Projects/Active",
            )
            if children:
                st.markdown(f'<div class="card-note">Will also rename {len(children)} child label(s)</div>', unsafe_allow_html=True)
            if st.button("Rename →", key="do_rename", type="primary", use_container_width=True):
                val = new_full_name.strip()
                if val and val != selected:
                    ok, msg = api_rename(service, labels, selected, val)
                    refresh()
                    if ok:
                        st.session_state.selected = val
                    flash(msg, 'ok' if ok else 'err')
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Move ──────────────────────────────────────────────────────────────
        with col_right:
            st.markdown('<div class="card card-move"><div class="card-title">📦 Move</div>', unsafe_allow_html=True)

            parent_options = ['(Root — no parent)'] + [
                l['name'] for l in labels
                if l['name'] != selected and not l['name'].startswith(selected + '/')
            ]

            current_parent = '/'.join(parts[:-1]) if len(parts) > 1 else None
            default_idx = 0
            if current_parent and current_parent in parent_options:
                default_idx = parent_options.index(current_parent)

            chosen = st.selectbox("Move under", parent_options, index=default_idx, key="move_target")
            if children:
                st.markdown(f'<div class="card-note">Will also move {len(children)} child label(s)</div>', unsafe_allow_html=True)
            if st.button("Move →", key="do_move", type="primary", use_container_width=True):
                parent_val = '' if chosen == '(Root — no parent)' else chosen
                new_name = f"{parent_val}/{leaf}" if parent_val else leaf
                if new_name != selected:
                    ok, msg = api_rename(service, labels, selected, new_name)
                    refresh()
                    if ok:
                        st.session_state.selected = new_name
                    flash(msg, 'ok' if ok else 'err')
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Delete ────────────────────────────────────────────────────────────
        st.markdown('<div class="card card-danger"><div class="card-title">🗑️ Delete</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="danger-note">
            Deleting a label does <strong>not</strong> delete your emails — messages simply lose this label.
        </div>
        """, unsafe_allow_html=True)

        dcol1, dcol2 = st.columns([3, 1])
        with dcol1:
            if children:
                cascade = st.checkbox(
                    f"Also delete {len(children)} child label(s): "
                    + ", ".join(c['name'].split('/')[-1] for c in children[:4])
                    + ("…" if len(children) > 4 else ""),
                    key="cascade_check",
                )
                st.session_state.cascade = cascade

            if not st.session_state.confirm_delete:
                if st.button(f"Delete '{leaf}'", key="pre_delete"):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.markdown('<div class="confirm-bar">⚠ This cannot be undone. Confirm?</div>', unsafe_allow_html=True)
                y, n = st.columns(2)
                with y:
                    if st.button("✓ Yes, delete it", key="yes_delete", type="primary"):
                        ok, msg = api_delete(service, labels, selected, cascade=st.session_state.cascade)
                        refresh()
                        if ok:
                            st.session_state.selected = None
                        st.session_state.confirm_delete = False
                        flash(msg, 'ok' if ok else 'err')
                        st.rerun()
                with n:
                    if st.button("✗ Cancel", key="no_delete"):
                        st.session_state.confirm_delete = False
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
