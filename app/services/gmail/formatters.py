import io
from typing import Any, Tuple

def format_export(threads_data: list, format_type: str) -> Tuple[Any, str, str]:
    """
    Formats the list of thread data into the desired format.
    Returns: (content, media_type, file_extension)
    threads_data: list of dicts with 'id', 'messages' list of dicts with 'from', 'date', 'subject', 'body'
    """
    if format_type == "markdown":
        return _format_markdown(threads_data)
    elif format_type == "pdf":
        return _format_pdf(threads_data)
    else:
        return _format_text(threads_data)

def _format_text(threads_data: list) -> Tuple[str, str, str]:
    lines = []
    lines.append("Gmail Thread Export")
    lines.append(f"Total Threads: {len(threads_data)}")
    lines.append(f"{'=' * 80}\n")
    
    for idx, thread in enumerate(threads_data, 1):
        lines.append(f"\n{'=' * 80}")
        lines.append(f"THREAD {idx} of {len(threads_data)} (ID: {thread['id']})")
        lines.append(f"Messages in thread: {len(thread['messages'])}")
        lines.append(f"{'=' * 80}\n")
        
        for m_idx, msg in enumerate(thread['messages'], 1):
            lines.append(f"--- Message {m_idx} of {len(thread['messages'])} ---")
            lines.append(f"From: {msg['from']}")
            lines.append(f"Date: {msg['date']}")
            lines.append(f"Subject: {msg['subject']}")
            lines.append(f"\n{msg['body']}\n")
            lines.append("---\n")
            
    return ("\n".join(lines), "text/plain", "txt")

def _format_markdown(threads_data: list) -> Tuple[str, str, str]:
    lines = []
    lines.append("# Gmail Thread Export\n")
    lines.append(f"**Total Threads:** {len(threads_data)}\n")
    lines.append("---\n")
    
    for idx, thread in enumerate(threads_data, 1):
        lines.append(f"## THREAD {idx} of {len(threads_data)}")
        lines.append(f"**ID:** `{thread['id']}`  ")
        lines.append(f"**Messages:** {len(thread['messages'])}\n")
        
        for m_idx, msg in enumerate(thread['messages'], 1):
            lines.append(f"### Message {m_idx} of {len(thread['messages'])}")
            lines.append(f"- **From:** {msg['from']}")
            lines.append(f"- **Date:** {msg['date']}")
            lines.append(f"- **Subject:** {msg['subject']}\n")
            
            # Indent body as blockquote or code
            body = msg['body'].strip()
            if body:
                lines.append("```text")
                lines.append(body)
                lines.append("```\n")
                
        lines.append("---\n")
            
    return ("\n".join(lines), "text/markdown", "md")

def _format_pdf(threads_data: list) -> Tuple[bytes, str, str]:
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    def safe_text(text):
        if not text: return ""
        # fpdf2 with helvetica handles latin-1, replace unsupported chars
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "Gmail Thread Export", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Total Threads: {len(threads_data)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    for idx, thread in enumerate(threads_data, 1):
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 10, f"THREAD {idx} of {len(threads_data)} (ID: {thread['id']})", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)
        
        for m_idx, msg in enumerate(thread['messages'], 1):
            pdf.ln(2)
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(0, 8, f"--- Message {m_idx} of {len(thread['messages'])} ---", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=10)
            
            pdf.cell(0, 6, safe_text(f"From: {msg['from']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, safe_text(f"Date: {msg['date']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, safe_text(f"Subject: {msg['subject']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
            # body
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, safe_text(msg['body']))
            pdf.ln(5)
            
    # Output to bytes
    pdf_bytes = pdf.output()
    return (bytes(pdf_bytes), "application/pdf", "pdf")
