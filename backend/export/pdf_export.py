from __future__ import annotations

from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover - optional dependency at runtime
    A4 = None
    colors = None
    canvas = None


def build_pdf_report(payload: dict) -> bytes:
    if canvas is None or A4 is None:
        return _build_minimal_pdf(payload)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 40
    content_width = width - (margin * 2)
    page_no = 1
    y = height - margin

    anomalies = payload.get("anomalies", [])
    top = anomalies[0] if anomalies else {}
    breakdown = payload.get("detection_breakdown", {})

    def draw_header() -> None:
        nonlocal y
        header_h = 56
        pdf.setFillColor(colors.HexColor("#F2F6FB"))
        pdf.setStrokeColor(colors.HexColor("#D4DFEA"))
        pdf.roundRect(margin, height - margin - header_h, content_width, header_h, 8, stroke=1, fill=1)
        pdf.setFillColor(colors.HexColor("#173754"))
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin + 14, height - margin - 22, "LOG SENTINEL - Security Scan Report")
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.HexColor("#4B667E"))
        pdf.drawRightString(width - margin - 14, height - margin - 22, _safe_text(f"Scan ID: {payload.get('scan_id', 'n/a')}"))
        pdf.drawRightString(
            width - margin - 14,
            height - margin - 36,
            _safe_text(f"Generated: {payload.get('scan_timestamp', 'n/a')}"),
        )
        y = height - margin - header_h - 16

    def draw_footer() -> None:
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#73879B"))
        pdf.drawString(margin, margin - 10, "Confidential incident triage output")
        pdf.drawRightString(width - margin, margin - 10, f"Page {page_no}")

    def next_page() -> None:
        nonlocal page_no
        draw_footer()
        pdf.showPage()
        page_no += 1
        draw_header()

    def ensure_space(required_height: float) -> None:
        if y - required_height < margin + 20:
            next_page()

    def draw_panel(y_top: float, panel_height: float, fill_color: str, stroke_color: str = "#DCE4EE") -> None:
        pdf.setFillColor(colors.HexColor(fill_color))
        pdf.setStrokeColor(colors.HexColor(stroke_color))
        pdf.roundRect(margin, y_top - panel_height, content_width, panel_height, 8, stroke=1, fill=1)

    def write_wrapped(x: float, y_start: float, text: str, width_chars: int, line_gap: int = 11, max_lines: int = 4) -> int:
        lines = _wrap_text(_safe_text(text), width_chars)[:max_lines]
        yy = y_start
        for line in lines:
            pdf.drawString(x, yy, line)
            yy -= line_gap
        return len(lines)

    def fit_text(text: str, font_name: str, font_size: int, max_width: float) -> str:
        safe = _safe_text(text)
        if pdf.stringWidth(safe, font_name, font_size) <= max_width:
            return safe
        ellipsis = "..."
        trimmed = safe
        while trimmed and pdf.stringWidth(trimmed + ellipsis, font_name, font_size) > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis

    pdf.setTitle("Security Scan Report")
    draw_header()

    # Report metadata panel
    ensure_space(64)
    draw_panel(y, 64, "#FFFFFF")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#3D566E"))
    pdf.drawString(margin + 14, y - 20, _safe_text(f"File: {payload.get('filename', 'n/a')}"))
    pdf.drawString(margin + 14, y - 36, _safe_text(f"Detected Format: {payload.get('detected_format', 'n/a')}"))
    pdf.drawString(
        margin + 280,
        y - 20,
        _safe_text(f"Processing Time: {payload.get('processing_time_seconds', 0)} s"),
    )
    pdf.drawString(margin + 280, y - 36, _safe_text(f"Persisted Anomalies: {len(anomalies)}"))
    y -= 76

    # KPI cards
    ensure_space(72)
    cards = [
        ("Events", str(payload.get("total_events", 0))),
        ("Unique IPs", str(payload.get("unique_ips", 0))),
        ("Top Severity", str(top.get("severity_label", "LOW"))),
        ("Top Score", f"{top.get('composite_score', 0)} / 100"),
    ]
    card_width = (content_width - 18) / 4
    card_y = y - 58
    for idx, (label, value) in enumerate(cards):
        x = margin + idx * (card_width + 6)
        pdf.setFillColor(colors.HexColor("#F8FBFF"))
        pdf.setStrokeColor(colors.HexColor("#D8E2EE"))
        pdf.roundRect(x, card_y, card_width, 52, 6, stroke=1, fill=1)
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#5A6B7A"))
        pdf.drawString(x + 8, card_y + 34, label)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColor(colors.HexColor("#13293D"))
        pdf.drawString(x + 8, card_y + 17, _safe_text(value))
    y = card_y - 16

    # Summary and model split
    ensure_space(96)
    draw_panel(y, 92, "#F8FBFF")
    pdf.setFillColor(colors.HexColor("#173754"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin + 14, y - 20, "Executive Summary")
    pdf.drawString(margin + 300, y - 20, "Detection Engine Split")

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#324F67"))
    pdf.drawString(margin + 14, y - 36, _safe_text(f"Highest risk source: {top.get('source_ip', 'n/a')}"))
    pdf.drawString(margin + 14, y - 48, _safe_text(f"Triggered rule: {top.get('rule_triggered') or 'none'}"))
    pdf.drawString(margin + 14, y - 60, _safe_text("Risk trend: prioritize immediate containment and credential reset"))
    pdf.drawString(margin + 300, y - 36, _safe_text(f"Rules: {breakdown.get('rule_count', 0)}"))
    pdf.drawString(margin + 300, y - 48, _safe_text(f"Isolation Forest (ML): {breakdown.get('ml_count', 0)}"))
    pdf.drawString(margin + 300, y - 60, _safe_text(f"Spike Detector: {breakdown.get('spike_count', 0)}"))
    y -= 106

    # Recommended actions
    ensure_space(78)
    draw_panel(y, 74, "#FFF9F2", "#E9D2BA")
    pdf.setFillColor(colors.HexColor("#744513"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin + 14, y - 18, "Recommended Immediate Actions")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#6F4A18"))
    pdf.drawString(margin + 14, y - 34, "1. Block highest-risk source IPs at perimeter firewall.")
    pdf.drawString(margin + 14, y - 46, "2. Reset credentials for affected privileged accounts.")
    pdf.drawString(margin + 14, y - 58, "3. Preserve this report as incident response evidence.")
    y -= 90

    ensure_space(24)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(colors.HexColor("#173754"))
    pdf.drawString(margin, y, _safe_text(f"Top anomalies ({len(anomalies)})"))
    y -= 16

    if not anomalies:
        ensure_space(28)
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#445E75"))
        pdf.drawString(margin, y, "No ranked anomalies were available in this report.")
        y -= 20
    else:
        for anomaly in anomalies:
            severity = str(anomaly.get("severity_label", "LOW"))
            severity_color = {
                "CRITICAL": colors.HexColor("#C73A2F"),
                "WARNING": colors.HexColor("#C97B1A"),
            }.get(severity, colors.HexColor("#2E6DE0"))

            panel_fill = {
                "CRITICAL": "#FFF8F7",
                "WARNING": "#FFF9F2",
            }.get(severity, "#FFFFFF")
            panel_stroke = {
                "CRITICAL": "#E8D6D3",
                "WARNING": "#E9DCC8",
            }.get(severity, "#DCE4EE")

            briefing_lines = _wrap_text(_safe_text(anomaly.get("briefing", "")), 104)[:5]
            panel_height = 120 + (len(briefing_lines) * 11)
            ensure_space(panel_height + 10)

            draw_panel(y, panel_height, panel_fill, panel_stroke)

            score = float(anomaly.get("composite_score", 0.0))
            severity_text = _safe_text(severity.upper())

            # Severity badge (dynamic width + centered text)
            badge_h = 18
            badge_y = y - 30
            badge_x = margin + 12
            badge_w = max(78, int(pdf.stringWidth(severity_text, "Helvetica-Bold", 8) + 22))

            pdf.setFillColor(colors.HexColor("#FFF3F2") if severity == "CRITICAL" else colors.HexColor("#FFF7ED"))
            pdf.setStrokeColor(severity_color)
            pdf.roundRect(badge_x, badge_y, badge_w, badge_h, 4, stroke=1, fill=1)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.setFillColor(severity_color)
            pdf.drawCentredString(badge_x + (badge_w / 2), badge_y + 5, severity_text)

            # Score pill on the right
            score_text = _safe_text(f"{score:.1f}/100")
            score_w = max(64, int(pdf.stringWidth(score_text, "Helvetica-Bold", 9) + 18))
            score_x = width - margin - 14 - score_w
            pdf.setFillColor(colors.HexColor("#EEF3FA"))
            pdf.setStrokeColor(colors.HexColor("#D8E1EE"))
            pdf.roundRect(score_x, badge_y, score_w, badge_h, 4, stroke=1, fill=1)
            pdf.setFillColor(colors.HexColor("#1D2B3A"))
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawCentredString(score_x + (score_w / 2), badge_y + 6, score_text)

            pdf.setFillColor(colors.HexColor("#1D2B3A"))
            pdf.setFont("Helvetica-Bold", 11)
            title_x = badge_x + badge_w + 10
            title_max_w = max(60, score_x - title_x - 8)
            title_text = fit_text(
                f"#{anomaly.get('rank', '?')}  {anomaly.get('source_ip', 'n/a')}",
                "Helvetica-Bold",
                11,
                title_max_w,
            )
            pdf.drawString(title_x, y - 17, title_text)

            pdf.setFont("Helvetica", 8)
            pdf.setFillColor(colors.HexColor("#4F6070"))
            pdf.drawString(
                badge_x + badge_w + 10,
                y - 30,
                _safe_text(f"Rule: {anomaly.get('rule_triggered') or 'none'}"),
            )
            pdf.drawString(
                badge_x + badge_w + 10,
                y - 42,
                _safe_text(f"Window: {anomaly.get('window_start', 'n/a')} to {anomaly.get('window_end', 'n/a')}"),
            )

            bar_x = margin + 104
            bar_y = y - 54
            bar_w = content_width - 118
            bar_h = 7
            score_w = max(0.0, min(1.0, score / 100.0)) * bar_w
            pdf.setFillColor(colors.HexColor("#E7EEF5"))
            pdf.roundRect(bar_x, bar_y, bar_w, bar_h, 3, stroke=0, fill=1)
            pdf.setFillColor(severity_color)
            pdf.roundRect(bar_x, bar_y, score_w, bar_h, 3, stroke=0, fill=1)

            pdf.setFillColor(colors.HexColor("#1D2B3A"))
            pdf.setFont("Helvetica", 8)
            stats_text = (
                f"Failed {anomaly.get('login_failure_count', 0)}   "
                f"Success {anomaly.get('login_success_count', 0)}   "
                f"RPM {anomaly.get('requests_per_minute', 0)}   "
                f"Endpoints {anomaly.get('unique_endpoints', 0)}"
            )
            pdf.drawString(margin + 14, y - 70, _safe_text(stats_text))

            pdf.setFillColor(colors.HexColor("#203243"))
            pdf.setFont("Helvetica", 8)
            pdf.drawString(margin + 14, y - 84, "Briefing:")
            text_y = y - 96
            for line in briefing_lines:
                pdf.drawString(margin + 14, text_y, line)
                text_y -= 11

            y -= panel_height + 10

    draw_footer()
    pdf.save()
    return buffer.getvalue()


def _safe_text(text: str) -> str:
    return str(text).encode("ascii", errors="replace").decode("ascii")


def _wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _build_minimal_pdf(payload: dict) -> bytes:
    anomalies = payload.get("anomalies", [])
    lines = [
        "Security Scan Report",
        f"Scan ID: {payload.get('scan_id', 'n/a')}",
        f"Filename: {payload.get('filename', 'n/a')}",
        f"Detected format: {payload.get('detected_format', 'n/a')}",
        f"Total events: {payload.get('total_events', 0)}",
        f"Unique IPs: {payload.get('unique_ips', 0)}",
        f"Anomalies: {len(anomalies)}",
    ]
    for anomaly in anomalies:
        lines.append(
            f"#{anomaly.get('rank', '?')} {anomaly.get('severity_label', 'LOW')} "
            f"{anomaly.get('source_ip', 'n/a')} score {anomaly.get('composite_score', 0)}"
        )
        lines.extend(_wrap_text(anomaly.get("briefing", ""), 80))

    content_lines = ["BT", "/F1 12 Tf", "50 790 Td"]
    first = True
    for line in lines:
        safe_line = _escape_pdf_text(_safe_text(line))
        if first:
            content_lines.append(f"({safe_line}) Tj")
            first = False
        else:
            content_lines.append("T*")
            content_lines.append(f"({safe_line}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("ascii")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(pdf.tell())
        pdf.write(obj)

    xref_pos = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(
        (
            "trailer << /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".format(
                size=len(objects) + 1,
                xref=xref_pos,
            )
        ).encode("ascii")
    )
    return pdf.getvalue()


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
