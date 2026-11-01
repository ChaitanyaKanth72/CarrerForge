"""CareerForge - Flask backend. Run with: python app.py"""
import io
import logging

import pymupdf as fitz  # PyMuPDF
from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

import config
from errors import AppError
from services import ai, db, jobs, matching, resumes
from services.pdf import build_pdf

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = config.MAX_PDF_BYTES + 100_000


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise AppError("The request body must be JSON.")
    return data


def extract_pdf_text(file):
    """Validates an uploaded PDF and returns its text (PyMuPDF)."""
    raw = file.read() if file else b""
    name = (file.filename or "").lower() if file else ""
    if not raw or not name.endswith(".pdf") or not raw.startswith(b"%PDF-"):
        raise AppError("Please upload a valid PDF file.")
    if len(raw) > config.MAX_PDF_BYTES:
        raise AppError("The PDF must be under 5 MB.", 413)
    try:
        with fitz.open(stream=raw, filetype="pdf") as doc:
            if doc.needs_pass:
                raise AppError("This PDF is password protected.")
            if doc.page_count > config.MAX_PDF_PAGES:
                raise AppError("Please upload a resume of 10 pages or fewer.")
            text = "\n".join(page.get_text() for page in doc).strip()
    except AppError:
        raise
    except Exception:
        raise AppError("This PDF could not be read. It may be damaged.")
    if len(text) < 50:
        raise AppError("No readable text found. Scanned PDFs are not supported.")
    return text


@app.get("/")
def home():
    return app.send_static_file("index.html")


@app.get("/api/status")
def status():
    return jsonify(ai=ai.configured(), database=db.available(), jobs=jobs.providers())


# ---- resume storage (optional MySQL copy) ----
@app.post("/api/resume")
def create_resume():
    if not db.available():
        raise AppError("Server storage is not configured.", 503)
    data = body()
    return jsonify(token=resumes.save(data.get("resume"), data.get("template", "modern"))), 201


@app.put("/api/resume/<token>")
def update_resume(token):
    if not db.available():
        raise AppError("Server storage is not configured.", 503)
    data = body()
    if resumes.save(data.get("resume"), data.get("template", "modern"), token) is None:
        raise AppError("Resume not found.", 404)
    return jsonify(token=token)


@app.post("/api/resume/pdf")
def resume_pdf():
    data = body()
    r = resumes.normalize(data.get("resume"))
    if resumes.is_empty(r):
        raise AppError("Add some details to your resume first.")
    return send_file(io.BytesIO(build_pdf(r, data.get("template", "modern"))), mimetype="application/pdf",
                     as_attachment=True, download_name="resume.pdf")


@app.post("/api/resume/extract")
def resume_extract():
    return jsonify(text=extract_pdf_text(request.files.get("file")))


@app.post("/api/resume/import")
def resume_import():
    """Reads an uploaded PDF resume into builder fields (needs Gemini)."""
    text = extract_pdf_text(request.files.get("file"))[:12000]
    r = resumes.normalize(ai.ask_json(ai.IMPORT_PROMPT, "Resume text:\n" + text))
    if resumes.is_empty(r):
        raise AppError("Nothing could be read from this resume. Try filling the form instead.")
    return jsonify(resume=r)


# ---- AI ----
@app.post("/api/analyze")
def analyze():
    r = resumes.normalize(body().get("resume"))
    if resumes.is_empty(r):
        raise AppError("Add some details to your resume first.")
    import json
    return jsonify(ai.ask_json(ai.ANALYZE_PROMPT, "Resume (JSON):\n" + json.dumps(r, indent=1)))


@app.post("/api/analyze/pdf")
def analyze_pdf():
    text = extract_pdf_text(request.files.get("file"))[:12000]
    return jsonify(ai.ask_json(ai.ANALYZE_PROMPT, "Resume (plain text from PDF):\n" + text))


@app.post("/api/chat")
def chat():
    data = body()
    message = str(data.get("message", "")).strip()[:2000]
    if not message:
        raise AppError("Type a message first.")
    import json
    r = resumes.normalize(data.get("resume"))
    lines = [f"{str(m.get('role', ''))[:10]}: {str(m.get('text', ''))[:1500]}" for m in (data.get("history") or [])[-8:] if isinstance(m, dict)]
    prompt = "Resume (JSON):\n" + json.dumps(r, indent=1) + "\n\nConversation so far:\n" + "\n".join(lines) + "\n\nUser: " + message
    return jsonify(ai.ask_json(ai.CHAT_PROMPT, prompt))


# ---- recommendations and jobs ----
@app.post("/api/recommendations")
def recommendations():
    return jsonify(roles=matching.recommend(resumes.normalize(body().get("resume"))))


@app.post("/api/jobs/match")
def job_match():
    data = body()
    job = data.get("job") or {}
    return jsonify(matching.job_match(resumes.normalize(data.get("resume")),
                                      {"title": str(job.get("title", "")), "description": str(job.get("description", ""))}))


@app.post("/api/jobs/search")
def search_jobs():
    d = body()
    r = resumes.normalize(d.get("resume") or {})
    days = d.get("days") if d.get("days") in (1, 3, 7, 14, 30) else 0
    found, status_, configured = jobs.search(str(d.get("q", "")).strip()[:100], str(d.get("location", "")).strip()[:100],
                                             str(d.get("type", "all")), str(d.get("experience", "any")), str(d.get("source", "all")),
                                             days)
    return jsonify(jobs=[{**j, **matching.job_match(r, j)} for j in found], sources=status_, configured=configured)


# ---- errors: always JSON, never a stack trace ----
@app.errorhandler(AppError)
def app_error(e):
    return jsonify(error=e.message), e.status


@app.errorhandler(HTTPException)
def http_error(e):
    msg = "The PDF must be under 5 MB." if e.code == 413 else "The request could not be processed."
    return jsonify(error=msg), e.code


@app.errorhandler(Exception)
def unexpected(e):
    logging.exception("Unhandled error")
    return jsonify(error="Something went wrong on the server."), 500


# Runs on import too, so MySQL is set up under gunicorn as well as with `python app.py`.
try:
    db.init()
except Exception:
    logging.warning("MySQL tables could not be created; continuing without server storage.")

if __name__ == "__main__":
    app.run(debug=False, port=config.PORT)
