"""Resume PDF generation (ReportLab). Three templates: modern, classic, minimal."""
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

THEMES = {
    "modern": dict(font="Helvetica", bold="Helvetica-Bold", accent=colors.HexColor("#c2410c"), align=TA_LEFT, rule=True, caps=True),
    "classic": dict(font="Times-Roman", bold="Times-Bold", accent=colors.black, align=TA_CENTER, rule=True, caps=True),
    "minimal": dict(font="Helvetica", bold="Helvetica-Bold", accent=colors.HexColor("#444444"), align=TA_LEFT, rule=False, caps=False),
}


def _p(text):
    return escape(text or "").replace("\n", "<br/>")


def build_pdf(r, template="modern"):
    t = THEMES.get(template, THEMES["modern"])
    styles = {
        "name": ParagraphStyle("name", fontName=t["bold"], fontSize=22, leading=26, textColor=t["accent"], alignment=t["align"]),
        "contact": ParagraphStyle("contact", fontName=t["font"], fontSize=9.5, leading=13, textColor=colors.HexColor("#444444"), alignment=t["align"]),
        "h": ParagraphStyle("h", fontName=t["bold"], fontSize=11, leading=14, textColor=t["accent"], spaceBefore=10, spaceAfter=2),
        "title": ParagraphStyle("title", fontName=t["bold"], fontSize=10.5, leading=13.5),
        "body": ParagraphStyle("body", fontName=t["font"], fontSize=10, leading=13.5),
        "sub": ParagraphStyle("sub", fontName=t["font"], fontSize=9.5, leading=12.5, textColor=colors.HexColor("#555555")),
        "bullet": ParagraphStyle("bullet", fontName=t["font"], fontSize=10, leading=13.5, leftIndent=11, bulletIndent=1),
    }
    story = []

    def section(title):
        story.append(Paragraph(title.upper() if t["caps"] else title, styles["h"]))
        if t["rule"]:
            story.append(HRFlowable(width="100%", thickness=0.7, color=t["accent"], spaceAfter=4))

    def entry(title, sub, body):
        if title:
            story.append(Paragraph(_p(title), styles["title"]))
        if sub:
            story.append(Paragraph(_p(sub), styles["sub"]))
        lines = [re.sub(r"^\s*[-•*]\s*", "", ln).strip() for ln in (body or "").split("\n")]
        lines = [ln for ln in lines if ln]
        if len(lines) == 1:
            story.append(Paragraph(_p(lines[0]), styles["body"]))
        for ln in lines if len(lines) > 1 else []:  # several lines read as bullet points
            story.append(Paragraph(_p(ln), styles["bullet"], bulletText="•"))
        story.append(Spacer(1, 4))

    story.append(Paragraph(_p(r["name"] or "Your Name"), styles["name"]))
    contact = [r[k] for k in ("email", "phone", "location", "linkedin", "github") if r[k]]
    if contact:
        story.append(Paragraph(_p("  |  ".join(contact)), styles["contact"]))
    if r["summary"]:
        section("Summary")
        story.append(Paragraph(_p(r["summary"]), styles["body"]))
    if r["education"]:
        section("Education")
        for e in r["education"]:
            degree = ", ".join(x for x in (e["degree"], e["branch"]) if x)
            sub = "  |  ".join(x for x in (e["college"], e["grad_year"], f"CGPA {e['cgpa']}" if e["cgpa"] else "") if x)
            entry(degree or e["college"], sub if degree else "", "")
    if r["experience"]:
        section("Experience")
        for e in r["experience"]:
            entry(e["role"] or e["company"], "  |  ".join(x for x in (e["company"] if e["role"] else "", e["duration"]) if x), e["details"])
    if r["projects"]:
        section("Projects")
        for p in r["projects"]:
            entry(p["title"], "  |  ".join(x for x in (p["tech"], p["link"]) if x), p["description"])
    if r["skills"]:
        section("Skills")
        story.append(Paragraph(_p(", ".join(r["skills"])), styles["body"]))
    if r["certifications"]:
        section("Certifications")
        for c in r["certifications"]:
            entry(c["name"], "  |  ".join(x for x in (c["organisation"], c["completed"]) if x), "")

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                      title=f"{r['name'] or 'Resume'} - Resume", author=r["name"] or "").build(story)
    return buf.getvalue()
