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
    try:
        result = service.users().labels().list(userId='me').execute()
        return sorted(
            [l for l in result.get('labels', []) if l['type'] == 'user'],
            key=lambda l: l['name'].lower(),
        )
    except Exception as e:
        return None, str(e)


def get_children(labels, parent_name):
    return [l for l in labels if l['name'].startswith(parent_name + '/')]


def api_rename(service, labels, old_name, new_name):
    try:
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
    except Exception as e:
        return False, f"API error: {e}"


def api_delete(service, labels, label_name, cascade=False):
    try:
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
    except Exception as e:
        return False, f"API error: {e}"


def api_create(service, name):
    try:
        service.users().labels().create(userId='me', body={'name': name}).execute()
        return True, f"Created '{name}'"
    except Exception as e:
        return False, f"API error: {e}"


# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700&display=swap');

/* ── Design tokens ── */
:root {
    --c-bg:        #f8fafc;
    --c-surface:   #ffffff;
    --c-border:    #e2e8f0;
    --c-text:      #0f172a;
    --c-muted:     #64748b;
    --c-subtle:    #94a3b8;
    --c-accent:    #6366f1;
    --c-success:   #22c55e;
    --c-danger:    #ef4444;
    --c-warning:   #f59e0b;
    --c-sidebar:   #0f172a;
    --c-sidebar-2: #1e293b;
    --c-move:      #10b981;

    --text-xs:   0.75rem;
    --text-sm:   0.875rem;
    --text-base: 1rem;
    --text-lg:   1.125rem;
    --text-xl:   1.5rem;
}

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 1100px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--c-sidebar) 0%, var(--c-sidebar-2) 100%) !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* Scope color overrides to text nodes, not Streamlit internals */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div:not([class]) {
    color: #cbd5e1 !important;
}

[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #f1f5f9 !important;
    border-radius: 8px !important;
    font-size: var(--text-sm) !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: rgba(255,255,255,0.3) !important;
}
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
    font-size: var(--text-xs) !important;
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
    border-left: 3px solid var(--c-accent) !important;
    color: #fff !important;
    font-weight: 600 !important;
}

/* ── Page header ── */
.page-title {
    font-size: var(--text-xl);
    font-weight: 700;
    color: var(--c-text);
    margin: 0;
}
.stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--c-bg);
    border: 1px solid var(--c-border);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: var(--text-xs);
    color: var(--c-muted);
    margin-right: 6px;
}
.stat-pill b { color: var(--c-text); }
.divider { border: none; border-top: 1px solid var(--c-border); margin: 12px 0 20px; }

/* ── Selection header ── */
.sel-header {
    background: linear-gradient(135deg, #f0f4ff 0%, #fafafa 100%);
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.sel-name {
    font-size: var(--text-lg);
    font-weight: 700;
    color: #1e1b4b;
}
.sel-path {
    font-size: var(--text-xs);
    color: var(--c-muted);
    margin-top: 4px;
}
.sel-full {
    font-size: var(--text-xs);
    color: var(--c-subtle);
    margin-top: 4px;
    font-family: monospace;
}
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: var(--text-xs);
    font-weight: 600;
    margin-left: 8px;
}
.badge-children { background: #fef3c7; color: #92400e; }

/* ── Section titles (replace broken card wrappers) ── */
.section-title {
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding-bottom: 8px;
    margin-bottom: 12px;
    border-bottom: 2px solid;
}
.section-rename { color: var(--c-accent); border-color: var(--c-accent); }
.section-move   { color: var(--c-move);   border-color: var(--c-move); }
.section-danger { color: var(--c-danger); border-color: var(--c-danger); }

/* ── Notes & warnings ── */
.card-note {
    font-size: var(--text-xs);
    color: var(--c-subtle);
    margin-top: 6px;
}
.danger-note {
    background: #fef2f2;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: var(--text-sm);
    color: #b91c1c;
    margin-bottom: 12px;
}
.confirm-bar {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 8px;
    margin-bottom: 8px;
    font-size: var(--text-sm);
    color: #9a3412;
    font-weight: 500;
}

/* ── Flash messages ── */
.flash-ok  { background:#f0fdf4; color:#166534; border-left:4px solid var(--c-success);
             border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:var(--text-sm); }
.flash-err { background:#fef2f2; color:#991b1b; border-left:4px solid var(--c-danger);
             border-radius:8px; padding:10px 14px; margin-bottom:14px; font-size:var(--text-sm); }

/* ── Welcome ── */
.welcome {
    text-align: center;
    padding: 64px 32px;
    color: var(--c-subtle);
}
.welcome h2 { color: #1e293b; font-size: var(--text-lg); margin-bottom: 8px; }
.welcome p  { font-size: var(--text-sm); max-width: 360px; margin: 0 auto; }
.welcome-icon { font-size: 3.5rem; margin-bottom: 16px; }

/* Fix inputs & selects in main area */
.stSelectbox > div > div { border-radius: 8px !important; }
.stTextInput input { border-radius: 8px !important; font-size: var(--text-sm) !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    'selected': None,
    'confirm_delete': False,
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
    result = load_labels(service)
    if isinstance(result, tuple):  # error tuple
        flash(f"Could not load labels: {result[1]}", 'err')
    else:
        st.session_state.labels = result


# ── Bootstrap ─────────────────────────────────────────────────────────────────
try:
    service = get_service()
except Exception as e:
    st.error(f"Could not connect to Gmail: {e}")
    st.stop()

if st.session_state.labels is None:
    refresh()

labels = st.session_state.labels or []


# ── Tree icon helper ──────────────────────────────────────────────────────────
def tree_icon(label_name, all_labels):
    """Returns ▸/├/└ depending on depth and sibling position."""
    parts = label_name.split('/')
    depth = len(parts) - 1
    if depth == 0:
        return '▸ '
    parent_prefix = '/'.join(parts[:-1]) + '/'
    siblings = [
        l['name'] for l in all_labels
        if l['name'].startswith(parent_prefix)
        and '/' not in l['name'][len(parent_prefix):]
    ]
    return '└ ' if (not siblings or label_name == siblings[-1]) else '├ '


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 4px 14px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:14px">
        <div style="font-size:var(--text-lg);font-weight:700;color:#f1f5f9;letter-spacing:-0.02em">
            📧 Label Manager
        </div>
        <div style="font-size:var(--text-xs);color:rgba(255,255,255,0.3);margin-top:2px;
                    letter-spacing:0.05em;text-transform:uppercase">Gmail</div>
    </div>
    """, unsafe_allow_html=True)

    search = st.text_input(
        "search", placeholder="🔍  Search labels…",
        label_visibility="collapsed", key="search_box",
    )

    if st.button("↻ Refresh labels", use_container_width=True, key="btn_refresh"):
        refresh()
        st.session_state.selected = None
        st.session_state.confirm_delete = False
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    filtered = [l for l in labels if search.lower() in l['name'].lower()] if search else labels

    if not filtered:
        no_match = f"No labels match '{search}'" if search else "No labels found"
        st.markdown(
            f"<div style='color:rgba(255,255,255,0.3);font-size:var(--text-xs);padding:6px 4px'>"
            f"{no_match}</div>",
            unsafe_allow_html=True,
        )
    else:
        for label in filtered:
            parts = label['name'].split('/')
            depth = len(parts) - 1
            indent = '  ' * depth
            icon = tree_icon(label['name'], labels)
            display = f"{indent}{icon}{parts[-1]}"
            kind = "primary" if st.session_state.selected == label['name'] else "secondary"
            if st.button(display, key=f"lbl_{label['id']}", use_container_width=True, type=kind):
                st.session_state.selected = label['name']
                st.session_state.confirm_delete = False
                st.session_state.flash = None
                st.rerun()

    # ── Create label ──
    st.markdown("""
    <div style="margin-top:24px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.08)">
        <div style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;
                    letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">
            New Label
        </div>
    </div>
    """, unsafe_allow_html=True)

    new_name_input = st.text_input(
        "new_label", placeholder="e.g. Work/Projects/Q3",
        label_visibility="collapsed", key="new_label_name",
    )
    if st.button("+ Create label", use_container_width=True, key="btn_create"):
        val = new_name_input.strip()
        if val:
            ok, msg = api_create(service, val)
            refresh()
            flash(msg, 'ok' if ok else 'err')
            st.rerun()
        else:
            flash("Enter a label name first", 'err')
            st.rerun()

# ── Main area: header ─────────────────────────────────────────────────────────
nested_count = sum(1 for l in labels if '/' in l['name'])
root_count = len(labels) - nested_count

st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
    <span style="font-size:2rem">📧</span>
    <div class="page-title">Gmail Label Manager</div>
</div>
<div style="margin-bottom:20px">
    <span class="stat-pill"><b>{len(labels)}</b> total</span>
    <span class="stat-pill"><b>{root_count}</b> root</span>
    <span class="stat-pill"><b>{nested_count}</b> nested</span>
</div>
<hr class="divider">
""", unsafe_allow_html=True)

# Flash message
if st.session_state.flash:
    css = 'flash-ok' if st.session_state.flash_type == 'ok' else 'flash-err'
    icon = '✓' if st.session_state.flash_type == 'ok' else '✗'
    st.markdown(
        f'<div class="{css}">{icon}  {st.session_state.flash}</div>',
        unsafe_allow_html=True,
    )
    st.session_state.flash = None

selected = st.session_state.selected

# ── Main area: content ────────────────────────────────────────────────────────
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
        location = f"📁 {parent_path}" if parent_path else "📁 Root level"
        children_badge = (
            f'<span class="badge badge-children">⚠ {len(children)} children</span>'
            if children else ''
        )

        # Selection header
        st.markdown(f"""
        <div class="sel-header">
            <div style="display:flex;align-items:center;gap:6px">
                <span class="sel-name">🏷 {leaf}</span>
                {children_badge}
            </div>
            <div class="sel-path">{location}</div>
            <div class="sel-full">{selected}</div>
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns(2, gap="medium")

        # ── Rename ────────────────────────────────────────────────────────────
        with col_left:
            with st.container(border=True):
                st.markdown(
                    '<div class="section-title section-rename">✏️ Rename</div>',
                    unsafe_allow_html=True,
                )
                new_full_name = st.text_input(
                    "Full label name", value=selected, key="rename_val",
                    help="Use / for nesting — e.g. Work/Projects/Active",
                )
                if children:
                    preview = ", ".join(c['name'].split('/')[-1] for c in children[:3])
                    suffix = "…" if len(children) > 3 else ""
                    st.markdown(
                        f'<div class="card-note">Also renames: {preview}{suffix}</div>',
                        unsafe_allow_html=True,
                    )
                if st.button("Rename →", key="do_rename", type="primary", use_container_width=True):
                    val = new_full_name.strip()
                    if val and val != selected:
                        ok, msg = api_rename(service, labels, selected, val)
                        refresh()
                        if ok:
                            st.session_state.selected = val
                        flash(msg, 'ok' if ok else 'err')
                    else:
                        flash("Name is unchanged", 'err')
                    st.rerun()

        # ── Move ──────────────────────────────────────────────────────────────
        with col_right:
            with st.container(border=True):
                st.markdown(
                    '<div class="section-title section-move">📦 Move</div>',
                    unsafe_allow_html=True,
                )
                parent_options = ['(Root — no parent)'] + [
                    l['name'] for l in labels
                    if l['name'] != selected and not l['name'].startswith(selected + '/')
                ]
                current_parent = '/'.join(parts[:-1]) if len(parts) > 1 else None
                default_idx = 0
                if current_parent and current_parent in parent_options:
                    default_idx = parent_options.index(current_parent)

                chosen = st.selectbox(
                    "Move under", parent_options, index=default_idx, key="move_target",
                )
                if children:
                    preview = ", ".join(c['name'].split('/')[-1] for c in children[:3])
                    suffix = "…" if len(children) > 3 else ""
                    st.markdown(
                        f'<div class="card-note">Also moves: {preview}{suffix}</div>',
                        unsafe_allow_html=True,
                    )
                if st.button("Move →", key="do_move", type="primary", use_container_width=True):
                    parent_val = '' if chosen == '(Root — no parent)' else chosen
                    new_name = f"{parent_val}/{leaf}" if parent_val else leaf
                    if new_name != selected:
                        ok, msg = api_rename(service, labels, selected, new_name)
                        refresh()
                        if ok:
                            st.session_state.selected = new_name
                        flash(msg, 'ok' if ok else 'err')
                    else:
                        flash("Already in that location", 'err')
                    st.rerun()

        # ── Delete ────────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                '<div class="section-title section-danger">🗑️ Delete</div>',
                unsafe_allow_html=True,
            )
            st.markdown("""
            <div class="danger-note">
                Deleting a label does <strong>not</strong> delete your emails —
                messages simply lose this label. This cannot be undone.
            </div>
            """, unsafe_allow_html=True)

            if children:
                child_names = ", ".join(c['name'].split('/')[-1] for c in children[:4])
                suffix = "…" if len(children) > 4 else ""
                st.checkbox(
                    f"Also delete {len(children)} child label(s): {child_names}{suffix}",
                    key="cascade_check",
                )

            if not st.session_state.confirm_delete:
                if st.button(f"Delete '{leaf}'", key="pre_delete"):
                    st.session_state.confirm_delete = True
                    st.rerun()
            else:
                st.markdown(
                    '<div class="confirm-bar">⚠ This cannot be undone. Are you sure?</div>',
                    unsafe_allow_html=True,
                )
                y, n = st.columns(2)
                with y:
                    if st.button("✓ Yes, delete it", key="yes_delete", type="primary"):
                        cascade = st.session_state.get('cascade_check', False)
                        ok, msg = api_delete(service, labels, selected, cascade=cascade)
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
