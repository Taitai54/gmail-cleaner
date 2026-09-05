import io
import json
import re
import zipfile
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Tuple


def format_export(threads_data: list, format_type: str) -> Tuple[Any, str, str]:
    """
    Formats the list of thread data into the desired format.
    Returns: (content, media_type, file_extension)
    threads_data: list of dicts with 'id', 'messages' list of dicts with 'from', 'date', 'subject', 'body', etc.
    """
    fmt = (format_type or "text").lower()
    if fmt in ("markdown", "md"):
        return _format_markdown(threads_data)
    elif fmt == "pdf":
        return _format_pdf(threads_data)
    elif fmt == "json":
        return _format_json(threads_data)
    elif fmt == "html":
        return _format_html(threads_data)
    elif fmt in ("eml", "zip"):
        return _format_eml_zip(threads_data)
    else:
        return _format_text(threads_data)


def _format_text(threads_data: list) -> Tuple[str, str, str]:
    lines = []
    lines.append("Gmail Thread Export")
    lines.append(f"Total Threads: {len(threads_data)}")
    lines.append(f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"{'=' * 80}\n")

    for idx, thread in enumerate(threads_data, 1):
        lines.append(f"\n{'=' * 80}")
        lines.append(f"THREAD {idx} of {len(threads_data)} (ID: {thread.get('id', '')})")
        msgs = thread.get("messages", [])
        lines.append(f"Messages in thread: {len(msgs)}")
        lines.append(f"{'=' * 80}\n")

        for m_idx, msg in enumerate(msgs, 1):
            lines.append(f"--- Message {m_idx} of {len(msgs)} ---")
            lines.append(f"From: {msg.get('from', '')}")
            if msg.get("to"):
                lines.append(f"To: {msg.get('to', '')}")
            lines.append(f"Date: {msg.get('date', '')}")
            lines.append(f"Subject: {msg.get('subject', '')}")
            lines.append(f"\n{msg.get('body', '')}\n")
            lines.append("---\n")

    return ("\n".join(lines), "text/plain", "txt")


def _format_markdown(threads_data: list) -> Tuple[str, str, str]:
    lines = []
    lines.append("# Gmail Thread Export\n")
    lines.append(f"**Total Threads:** {len(threads_data)}  ")
    lines.append(f"**Exported:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    lines.append("---\n")

    for idx, thread in enumerate(threads_data, 1):
        msgs = thread.get("messages", [])
        lines.append(f"## THREAD {idx} of {len(threads_data)}")
        lines.append(f"**ID:** `{thread.get('id', '')}`  ")
        lines.append(f"**Messages:** {len(msgs)}\n")

        for m_idx, msg in enumerate(msgs, 1):
            lines.append(f"### Message {m_idx} of {len(msgs)}")
            lines.append(f"- **From:** {msg.get('from', '')}")
            if msg.get("to"):
                lines.append(f"- **To:** {msg.get('to', '')}")
            lines.append(f"- **Date:** {msg.get('date', '')}")
            lines.append(f"- **Subject:** {msg.get('subject', '')}\n")

            body = (msg.get("body") or "").strip()
            if body:
                lines.append("```text")
                lines.append(body)
                lines.append("```\n")

        lines.append("---\n")

    return ("\n".join(lines), "text/markdown", "md")


def _format_json(threads_data: list) -> Tuple[str, str, str]:
    """Formats thread data as structured JSON for easy parsing, retrieval, and AI processing."""
    export_obj = {
        "metadata": {
            "source": "Gmail Cleaner & Archive",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_threads": len(threads_data),
            "total_messages": sum(len(t.get("messages", [])) for t in threads_data),
        },
        "threads": threads_data,
    }
    return (json.dumps(export_obj, indent=2, ensure_ascii=False), "application/json", "json")


def _format_html(threads_data: list) -> Tuple[str, str, str]:
    """Generates an interactive, standalone HTML email archive with instant search and viewer."""
    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_threads = len(threads_data)
    total_messages = sum(len(t.get("messages", [])) for t in threads_data)

    threads_json = json.dumps(threads_data, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gmail Archive - {total_threads} Thread(s)</title>
    <style>
        :root {{
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --bg-sidebar: #f1f5f9;
            --border-color: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --primary: #4f46e5;
            --primary-hover: #4338ca;
            --badge-bg: #e0e7ff;
            --badge-text: #3730a3;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-page: #0f172a;
                --bg-card: #1e293b;
                --bg-sidebar: #131d2e;
                --border-color: #334155;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --badge-bg: #312e81;
                --badge-text: #e0e7ff;
            }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-page);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        header {{
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-shrink: 0;
        }}
        .header-title {{
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .header-meta {{
            font-size: 13px;
            color: var(--text-muted);
        }}
        .search-box {{
            flex: 1;
            max-width: 400px;
            position: relative;
        }}
        .search-input {{
            width: 100%;
            padding: 8px 14px;
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background: var(--bg-page);
            color: var(--text-main);
            outline: none;
        }}
        .search-input:focus {{
            border-color: var(--primary);
        }}
        .layout {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}
        .sidebar {{
            width: 380px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border-color);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}
        .thread-item {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: background 0.15s;
        }}
        .thread-item:hover {{
            background: rgba(99, 102, 241, 0.08);
        }}
        .thread-item.active {{
            background: var(--bg-card);
            border-left: 4px solid var(--primary);
        }}
        .thread-item-sender {{
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 3px;
            display: flex;
            justify-content: space-between;
        }}
        .thread-item-date {{
            font-size: 11px;
            font-weight: normal;
            color: var(--text-muted);
        }}
        .thread-item-subject {{
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .thread-item-snippet {{
            font-size: 12px;
            color: var(--text-muted);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .thread-badge {{
            display: inline-block;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 999px;
            background: var(--badge-bg);
            color: var(--badge-text);
            font-weight: 600;
            margin-top: 4px;
        }}
        .viewer {{
            flex: 1;
            background: var(--bg-card);
            overflow-y: auto;
            padding: 32px 40px;
        }}
        .thread-header {{
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
        }}
        .thread-subject-title {{
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .thread-id-pill {{
            font-size: 12px;
            font-family: monospace;
            color: var(--text-muted);
        }}
        .message-card {{
            background: var(--bg-page);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .message-card-header {{
            padding: 14px 18px;
            background: rgba(0,0,0,0.02);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .message-meta-row {{
            margin-bottom: 3px;
            font-size: 13px;
        }}
        .meta-label {{
            font-weight: 600;
            color: var(--text-muted);
            margin-right: 6px;
        }}
        .message-body {{
            padding: 20px;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: inherit;
        }}
        .empty-viewer {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-muted);
            font-size: 15px;
        }}
        @media print {{
            body {{ height: auto; overflow: visible; background: white; color: black; }}
            header, .sidebar, .search-box {{ display: none; }}
            .viewer {{ padding: 0; overflow: visible; }}
            .message-card {{ border: 1px solid #ccc; page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#EA4335">
                <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
            </svg>
            Gmail Archive
        </div>
        <div class="search-box">
            <input type="text" id="archive-search" class="search-input" placeholder="Filter archived threads..." oninput="filterThreads()">
        </div>
        <div class="header-meta">
            <span>{total_threads} threads ({total_messages} msgs)</span> &bull; <span>{timestamp_str}</span>
        </div>
    </header>

    <div class="layout">
        <div class="sidebar" id="thread-list"></div>
        <div class="viewer" id="thread-viewer">
            <div class="empty-viewer">Select a thread from the left to view messages</div>
        </div>
    </div>

    <script>
        const threadsData = {threads_json};
        let activeIndex = 0;

        function renderSidebar(filteredList) {{
            const listEl = document.getElementById('thread-list');
            listEl.innerHTML = '';
            
            if (filteredList.length === 0) {{
                listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No matching threads</div>';
                return;
            }}

            filteredList.forEach((thread, displayIdx) => {{
                const item = document.createElement('div');
                item.className = 'thread-item' + (thread._origIdx === activeIndex ? ' active' : '');
                
                const msgs = thread.messages || [];
                const lastMsg = msgs[msgs.length - 1] || {{}};
                const firstMsg = msgs[0] || {{}};
                const sender = lastMsg.from || firstMsg.from || 'Unknown';
                const subject = lastMsg.subject || firstMsg.subject || '(No Subject)';
                const date = lastMsg.date || firstMsg.date || '';
                const snippet = (msgs[0]?.body || '').slice(0, 80);

                item.innerHTML = `
                    <div class="thread-item-sender">
                        <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:220px;">${{escapeHtml(sender)}}</span>
                        <span class="thread-item-date">${{escapeHtml(date.split(' ').slice(0, 4).join(' '))}}</span>
                    </div>
                    <div class="thread-item-subject">${{escapeHtml(subject)}}</div>
                    <div class="thread-item-snippet">${{escapeHtml(snippet)}}</div>
                    <span class="thread-badge">${{msgs.length}} msg${{msgs.length > 1 ? 's' : ''}}</span>
                `;

                item.onclick = () => {{
                    activeIndex = thread._origIdx;
                    document.querySelectorAll('.thread-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    renderViewer(threadsData[activeIndex]);
                }};

                listEl.appendChild(item);
            }});
        }}

        function renderViewer(thread) {{
            const viewerEl = document.getElementById('thread-viewer');
            if (!thread) {{
                viewerEl.innerHTML = '<div class="empty-viewer">Select a thread to view</div>';
                return;
            }}

            const msgs = thread.messages || [];
            const subject = msgs[0]?.subject || '(No Subject)';

            let msgsHtml = '';
            msgs.forEach((m, idx) => {{
                msgsHtml += `
                    <div class="message-card">
                        <div class="message-card-header">
                            <div>
                                <div class="message-meta-row"><span class="meta-label">From:</span>${{escapeHtml(m.from || '')}}</div>
                                ${{m.to ? `<div class="message-meta-row"><span class="meta-label">To:</span>${{escapeHtml(m.to)}}</div>` : ''}}
                                <div class="message-meta-row"><span class="meta-label">Subject:</span>${{escapeHtml(m.subject || '')}}</div>
                            </div>
                            <div style="font-size:12px; color:var(--text-muted);">${{escapeHtml(m.date || '')}}</div>
                        </div>
                        <div class="message-body">${{escapeHtml(m.body || '(Empty body)')}}</div>
                    </div>
                `;
            }});

            viewerEl.innerHTML = `
                <div class="thread-header">
                    <div class="thread-subject-title">${{escapeHtml(subject)}}</div>
                    <div class="thread-id-pill">Thread ID: ${{escapeHtml(thread.id || '')}} &bull; ${{msgs.length}} message(s)</div>
                </div>
                ${{msgsHtml}}
            `;
        }}

        function filterThreads() {{
            const query = (document.getElementById('archive-search').value || '').toLowerCase().trim();
            const indexed = threadsData.map((t, idx) => ({{ ...t, _origIdx: idx }}));
            
            if (!query) {{
                renderSidebar(indexed);
                return;
            }}

            const filtered = indexed.filter(t => {{
                return (t.messages || []).some(m => 
                    (m.from || '').toLowerCase().includes(query) ||
                    (m.subject || '').toLowerCase().includes(query) ||
                    (m.body || '').toLowerCase().includes(query) ||
                    (m.to || '').toLowerCase().includes(query) ||
                    (m.date || '').toLowerCase().includes(query)
                );
            }});

            renderSidebar(filtered);
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }}

        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {{
            threadsData.forEach((t, i) => {{ t._origIdx = i; }});
            renderSidebar(threadsData);
            if (threadsData.length > 0) {{
                renderViewer(threadsData[0]);
            }}
        }});
    </script>
</body>
</html>
"""
    return (html_content, "text/html", "html")


def _format_eml_zip(threads_data: list) -> Tuple[bytes, str, str]:
    """Exports thread messages as standard RFC 822 .eml files compressed in a ZIP archive."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for t_idx, thread in enumerate(threads_data, 1):
            thread_id = thread.get("id", f"thread_{t_idx}")
            msgs = thread.get("messages", [])

            for m_idx, msg in enumerate(msgs, 1):
                msg_id = msg.get("id", f"{thread_id}_{m_idx}")
                eml = EmailMessage()
                eml["Subject"] = msg.get("subject", "(No Subject)")
                eml["From"] = msg.get("from", "unknown@domain.com")
                if msg.get("to"):
                    eml["To"] = msg.get("to")
                if msg.get("date"):
                    eml["Date"] = msg.get("date")
                eml["Message-ID"] = f"<{msg_id}@gmail.cleaner.archive>"
                eml.set_content(msg.get("body", ""))

                safe_subject = re.sub(r'[\\/*?:"<>|]', "_", msg.get("subject", "message"))[:40]
                filename = f"threads/thread_{t_idx:03d}_{thread_id}/msg_{m_idx:02d}_{safe_subject}.eml"
                zf.writestr(filename, eml.as_bytes())

    zip_bytes = zip_buffer.getvalue()
    return (zip_bytes, "application/zip", "zip")


def _format_pdf(threads_data: list) -> Tuple[bytes, str, str]:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    def safe_text(text):
        if not text:
            return ""
        return str(text).encode("latin-1", "replace").decode("latin-1")

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "Gmail Thread Export", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Total Threads: {len(threads_data)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    for idx, thread in enumerate(threads_data, 1):
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 10, f"THREAD {idx} of {len(threads_data)} (ID: {thread.get('id', '')})", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)

        msgs = thread.get("messages", [])
        for m_idx, msg in enumerate(msgs, 1):
            pdf.ln(2)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, f"--- Message {m_idx} of {len(msgs)} ---", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=10)

            pdf.cell(0, 6, safe_text(f"From: {msg.get('from', '')}"), new_x="LMARGIN", new_y="NEXT")
            if msg.get("to"):
                pdf.cell(0, 6, safe_text(f"To: {msg.get('to', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, safe_text(f"Date: {msg.get('date', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, safe_text(f"Subject: {msg.get('subject', '')}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, safe_text(msg.get("body", "")))
            pdf.ln(5)

    pdf_bytes = pdf.output()
    return (bytes(pdf_bytes), "application/pdf", "pdf")

