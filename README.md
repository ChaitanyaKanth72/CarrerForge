# CareerForge (Flask)

AI resume builder, analyzer, assistant, career recommendations and live job finder. No login.
Frontend: HTML/CSS/JS in `static/`. Backend: Python Flask in `app.py` and `services/`.

## Run

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then fill in your keys
python app.py                                          # http://localhost:5000
```

The builder, templates, PDF download and career recommendations work with no keys.

## Configuration (`.env`, never sent to the browser)

| Variable | Needed for | Where to get it |
|---|---|---|
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Analyzer, assistant | https://aistudio.google.com/apikey (change the model if it is retired) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY` | Adzuna jobs | https://developer.adzuna.com (free) |
| `JOBVETTA_API_KEY` | Jobvetta jobs | https://www.jobvetta.com/dashboard (free, India only, 50 requests/day, 10 jobs per search) |
| `HIMALAYAS_ENABLED` | Remote jobs | No key. Credit and link back to Himalayas (the app does). |
| `MYSQL_*` | Optional storage | See below |

A source without a key is skipped and the Job Finder says so. If none is available it shows "Live job search is currently unavailable".
Apply Now opens the provider's own link in a new tab (for Himalayas, its job page, which links on to the employer).

## MySQL (optional)

```sql
CREATE DATABASE careerforge CHARACTER SET utf8mb4;
```
Set `MYSQL_USER` and `MYSQL_PASSWORD` in `.env`; tables are created from `schema.sql` on startup.
It stores a server-side copy of your resume (browser LocalStorage stays the main store) and caches job results for 10 minutes to protect free-tier quotas.
Without MySQL everything else works.
There is no login, so each resume is keyed by a random token kept in the browser. Do not treat stored data as private.

## Routes

| Route | Purpose |
|---|---|
| `POST /api/resume`, `PUT /api/resume/<token>` | Create / update the MySQL copy |
| `POST /api/resume/pdf` | Generate the PDF (ReportLab) |
| `POST /api/resume/extract` | Validate an uploaded PDF and return its text (PyMuPDF) |
| `POST /api/analyze`, `POST /api/analyze/pdf` | AI analysis of the builder resume / an uploaded PDF |
| `POST /api/chat` | Assistant |
| `POST /api/recommendations` | Career roles with compatibility |
| `POST /api/jobs/search`, `POST /api/jobs/match` | Live jobs with compatibility / compatibility for one job |
| `GET /api/status` | Which services are configured |

## Files

`app.py` routes and validation · `services/ai.py` Gemini · `services/pdf.py` PDF · `services/matching.py` roles and job match · `services/jobs.py` job APIs and cache · `services/resumes.py` clean-up and MySQL · `services/db.py` connection

## Before going public

AI calls cost money and anyone can use the site. Add rate limiting (for example Flask-Limiter) and run behind gunicorn, not `python app.py`.
