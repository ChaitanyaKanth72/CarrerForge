# CareerForge

An AI-powered resume builder and job finder for students and early-career job seekers. Python Flask backend, plain HTML/CSS/JS frontend, Google Gemini for the AI features. No login.

| Tab | What it does | Needs a key? |
|---|---|---|
| **01 Build** | Resume form with a live preview, three templates (Modern, Classic, Minimal), PDF download, a completeness score, and **Import PDF** to fill the form from an existing resume | Import needs Gemini; everything else works without keys |
| **02 Analyze** | Estimated ATS score, missing sections and a numbered list of fixes, for the builder resume or an uploaded PDF | Gemini |
| **03 Assistant** | Chat that reads your resume and rewrites summaries, bullet points and projects | Gemini |
| **04 Careers** | Ranks roles by how much of each role's core skill set your resume shows, and what to learn next | No |
| **05 Jobs** | Live listings from Adzuna, Jobvetta and Himalayas, ranked by fit, with salaries shown in **rupees** | Himalayas needs no key; Adzuna and Jobvetta are optional |

---

## Quick start

You need **Python 3.10 or newer** ([python.org/downloads](https://www.python.org/downloads/)). Check with `python3 --version` (on Windows: `python --version`).

### 1. Get the code and install

macOS / Linux:

```bash
git clone https://github.com/ChaitanyaKanth72/CarrerForge.git
cd CarrerForge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):

```powershell
git clone https://github.com/ChaitanyaKanth72/CarrerForge.git
cd CarrerForge
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

If PowerShell refuses to run the activate script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

### 2. Add your Gemini API key

The Analyzer, Assistant and Import PDF use Google Gemini. A key is free to create.

1. Go to **[aistudio.google.com/apikey](https://aistudio.google.com/apikey)** and sign in with a Google account.
2. Click **Create API key**. If asked, pick or create a Google Cloud project — the default is fine.
3. Copy the key.
4. Open the `.env` file in the project folder (it was created in step 1) and paste the key after `GEMINI_API_KEY=`, with no spaces or quotes:

   ```ini
   GEMINI_API_KEY=paste-your-key-here
   GEMINI_MODEL=gemini-flash-lite-latest
   ```

5. Save the file.

The key stays on the server: it is read from `.env` by Flask and never sent to the browser. `.env` is listed in `.gitignore`, so it is never committed. **Never put the key in `.env.example`, in the code, or in a screenshot.** If a key leaks, delete it in AI Studio and create a new one.

### 3. Start the app

```bash
python app.py
```

Open **http://127.0.0.1:5000**.

> **On a Mac**, port 5000 is taken by AirPlay Receiver and the page shows "403 Forbidden". Set `PORT=5001` in `.env`, run `python app.py` again and open **http://127.0.0.1:5001**.

### 4. Check it's working

- The header's top-right shows **● AI · ● Jobs · ● Sync**. A green dot means that service is on. **AI** should be green once your key is set. (Sync is the optional MySQL copy — grey is normal.)
- On **01 Build**, click **Load sample** to fill in an example resume, then try **02 Analyze → Analyze my resume**. An answer takes 20–40 seconds.
- You can also open http://127.0.0.1:5000/api/status — `"ai": true` means the key was picked up.

Whenever you change `.env`, stop the server (Ctrl + C) and start it again.

---

## Optional: more job sources

Remote jobs from **Himalayas** work with no key and, by default, only show jobs open to candidates in India. Add these for more listings — each is free. A source without a key is skipped, and the Jobs tab says so.

| Source | What you get | How to get the key | `.env` lines |
|---|---|---|---|
| **Adzuna** | On-site and remote jobs in India (or another country) with salary data | Sign up at [developer.adzuna.com](https://developer.adzuna.com) → *Dashboard* → copy the **Application ID** and **Application Key** | `ADZUNA_APP_ID=…`<br>`ADZUNA_APP_KEY=…`<br>`ADZUNA_COUNTRY=in` |
| **Jobvetta** | Vetted jobs in India from employer sites. 50 requests a day, 10 jobs per search | Sign in at [jobvetta.com/dashboard](https://www.jobvetta.com/dashboard) → *API* page → copy the key | `JOBVETTA_API_KEY=…` |

Job results are cached for 10 minutes so repeat searches don't use up these free quotas.

## Salaries in rupees

Every salary is shown in Indian rupees: **₹ LPA** for yearly pay, **₹/month** or **₹/hour** otherwise, with Indian digit grouping (₹2,85,000). Salaries listed in dollars, euros or pounds are converted at today's rate from [frankfurter.dev](https://frankfurter.dev) (free, no key) and marked *approx., converted*; hover to see the original. If the rate service can't be reached, `USD_INR` in `.env` is used instead.

## Choosing the Gemini model

| `GEMINI_MODEL` | Notes |
|---|---|
| `gemini-flash-lite-latest` (default) | Answers in about 20–40 seconds. Recommended. |
| `gemini-flash-latest` | Stronger answers but often much slower, sometimes over a minute. The app turns off its "thinking" mode (`GEMINI_THINKING_BUDGET=0`) to speed it up. |

If Google retires a model name, pick a current one from [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models).

## Optional: MySQL

Without MySQL, each person's resume is saved in their own browser (LocalStorage) and everything works. With MySQL, the server also keeps a copy of each resume and caches job results.

```sql
CREATE DATABASE careerforge CHARACTER SET utf8mb4;
```

Then set `MYSQL_USER` and `MYSQL_PASSWORD` (and `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_DB` if they differ) in `.env`. The tables are created from `schema.sql` when the app starts. There is no login — each stored resume is keyed by a random token kept in the browser — so don't treat stored data as private.

---

## Troubleshooting

| You see | Fix |
|---|---|
| **403 Forbidden** at `localhost:5000` (Mac) | AirPlay Receiver owns port 5000. Set `PORT=5001` in `.env`, restart, open http://127.0.0.1:5001. |
| "AI features are not configured" | `GEMINI_API_KEY` is empty or the server wasn't restarted. Check `.env`, then stop and restart `python app.py`. |
| "The AI service rejected the request" | The key is wrong or disabled, or the model name is retired. Re-copy the key from AI Studio and check `GEMINI_MODEL`. |
| "The AI service took too long to answer" | Gemini is busy. Try again, and use `GEMINI_MODEL=gemini-flash-lite-latest`. |
| "The AI service is busy or its quota is used up" | The free tier has per-minute and per-day limits. Wait a minute (or until tomorrow). |
| "No readable text found" when uploading a PDF | The PDF is a scanned image. Upload a PDF exported from Word / Google Docs, or use the builder. |
| "Live job search is currently unavailable" | Every job source is switched off. Keep `HIMALAYAS_ENABLED=true`, or add an Adzuna / Jobvetta key. |
| `ModuleNotFoundError` | The virtual environment isn't active. Run `source .venv/bin/activate` (Windows: `.venv\Scripts\Activate.ps1`) and `pip install -r requirements.txt`. |
| Changes to the page don't show | Hard-refresh the browser (Cmd/Ctrl + Shift + R). |

## All settings (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Turns on Analyze, Assistant and Import PDF |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | Which Gemini model to call |
| `GEMINI_THINKING_BUDGET` | `0` | Thinking tokens for Flash models; leave blank for the model's default (slow) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | — | Adzuna jobs |
| `ADZUNA_COUNTRY` | `in` | Adzuna country code (`in`, `gb`, `us`, …) |
| `JOBVETTA_API_KEY` | — | Jobvetta jobs (India) |
| `HIMALAYAS_ENABLED` | `true` | Remote jobs from Himalayas |
| `HIMALAYAS_COUNTRY` | `India` | Only show remote jobs open to this country; blank for worldwide |
| `USD_INR` | `95` | Fallback exchange rate if live rates can't be fetched |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` | `localhost`, `3306`, —, —, `careerforge` | Optional MySQL storage |
| `PORT` | `5000` | Port for `python app.py` (use 5001 on a Mac) |

## How it fits together

| Path | Role |
|---|---|
| `app.py` | Flask routes, input validation, JSON errors |
| `services/ai.py` | Gemini calls and prompts |
| `services/pdf.py` | Resume PDF (ReportLab), three templates |
| `services/matching.py` | Career recommendations and resume-to-job fit (no AI) |
| `services/jobs.py` | Adzuna, Jobvetta and Himalayas clients, filters and cache |
| `services/currency.py` | Rupee conversion and salary formatting |
| `services/resumes.py`, `services/db.py` | Resume clean-up and optional MySQL storage |
| `static/` | The single-page frontend (`index.html`, `styles.css`, `app.js`) |

| Route | Purpose |
|---|---|
| `GET /api/status` | Which services are configured |
| `POST /api/resume/pdf` | Generate the resume PDF |
| `POST /api/resume/import` | Read an uploaded PDF into the builder's fields (Gemini) |
| `POST /api/resume/extract` | Validate an uploaded PDF and return its text |
| `POST /api/resume`, `PUT /api/resume/<token>` | Create / update the MySQL copy |
| `POST /api/analyze`, `POST /api/analyze/pdf` | ATS analysis of the builder resume / an uploaded PDF |
| `POST /api/chat` | Assistant |
| `POST /api/recommendations` | Career roles with fit scores |
| `POST /api/jobs/search`, `POST /api/jobs/match` | Live jobs with fit scores / fit for one job |

## Before putting it online

`python app.py` is a development server. Anyone who can reach the site can spend your Gemini quota, so before hosting it publicly add rate limiting (for example Flask-Limiter) and run it behind a production server such as gunicorn (`pip install gunicorn`, then `gunicorn -w 2 -b 0.0.0.0:8000 app:app`). Set the same variables from `.env` in your host's environment settings — never upload the `.env` file itself.
