"""Resume clean-up and the optional MySQL copy."""
import uuid

from errors import AppError
from services import db

LIST_FIELDS = {
    "education": {"college": 200, "degree": 100, "branch": 100, "grad_year": 10, "cgpa": 10},
    "projects": {"title": 200, "description": 2000, "tech": 255, "link": 500},
    "experience": {"company": 200, "role": 150, "duration": 100, "details": 2000},
    "certifications": {"name": 200, "organisation": 200, "completed": 20},
}
TOP_FIELDS = {"name": 120, "email": 160, "phone": 40, "location": 120, "linkedin": 255, "github": 255, "summary": 2000}
MAX_ITEMS = 20
MAX_SKILLS = 60


def _text(value, limit):
    return str(value if value is not None else "").strip()[:limit]


def normalize(raw):
    """Returns a clean resume dict with every field present, whatever the client sent."""
    raw = raw if isinstance(raw, dict) else {}
    r = {k: _text(raw.get(k), n) for k, n in TOP_FIELDS.items()}
    skills = raw.get("skills") or []
    if isinstance(skills, str):
        skills = skills.split(",")
    seen, clean = set(), []
    for s in skills if isinstance(skills, list) else []:
        s = _text(s, 80)
        if s and s.lower() not in seen:
            seen.add(s.lower())
            clean.append(s)
    r["skills"] = clean[:MAX_SKILLS]
    for key, fields in LIST_FIELDS.items():
        items = raw.get(key) if isinstance(raw.get(key), list) else []
        rows = [{f: _text(item.get(f), n) for f, n in fields.items()} for item in items[:MAX_ITEMS] if isinstance(item, dict)]
        r[key] = [row for row in rows if any(row.values())]
    return r


def is_empty(r):
    return not (any(r[k] for k in TOP_FIELDS) or r["skills"] or any(r[k] for k in LIST_FIELDS))


def save(raw, template, token=None):
    """Stores a copy. Creates a row (returns a new token) or updates one (returns None if it does not exist)."""
    r = normalize(raw)
    if is_empty(r):
        raise AppError("Add some details to your resume first.")
    template = _text(template, 20) or "modern"
    with db.transaction() as cur:
        fields = [r[k] for k in TOP_FIELDS]
        if token is None:
            token = uuid.uuid4().hex
            cur.execute("INSERT INTO resumes (token, name, email, phone, location, linkedin, github, summary, template)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", [token, *fields, template])
            resume_id = cur.lastrowid
        else:
            cur.execute("SELECT id FROM resumes WHERE token=%s", [token])
            row = cur.fetchone()
            if not row:
                return None
            resume_id = row["id"]
            cur.execute("UPDATE resumes SET name=%s, email=%s, phone=%s, location=%s, linkedin=%s, github=%s,"
                        " summary=%s, template=%s WHERE id=%s", [*fields, template, resume_id])
            for table in ("education", "skills", "projects", "experience", "certifications"):
                cur.execute(f"DELETE FROM {table} WHERE resume_id=%s", [resume_id])
        for skill in r["skills"]:
            cur.execute("INSERT INTO skills (resume_id, skill) VALUES (%s,%s)", [resume_id, skill])
        for table, fields_ in LIST_FIELDS.items():
            cols = list(fields_)
            for row in r[table]:
                cur.execute(f"INSERT INTO {table} (resume_id, {', '.join(cols)}) VALUES (%s, {', '.join(['%s'] * len(cols))})",
                            [resume_id, *[row[c] for c in cols]])
    return token
