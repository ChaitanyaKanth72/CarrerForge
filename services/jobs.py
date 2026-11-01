"""Live job APIs (Adzuna, Jobvetta, Himalayas) with a short cache to protect free-tier quotas."""
import hashlib
import html
import json
import logging
import re
import time
from datetime import datetime

import requests

import config
from services import currency, db

TIMEOUT = 15
_memory = {}  # query_key -> (fetched_at, jobs); used when MySQL is not available


def providers():
    return {"adzuna": bool(config.ADZUNA_APP_ID and config.ADZUNA_APP_KEY), "jobvetta": bool(config.JOBVETTA_API_KEY),
            "himalayas": config.HIMALAYAS_ENABLED}


def _plain(text, limit=3000):
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"</(p|li|div|br|h\d)>|<br\s*/?>", "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()[:limit]


def _safe_url(url):
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else ""


def _experience(text):
    m = re.search(r"(\d{1,2})\s*(?:\+|-\s*\d{1,2})?\s*(?:years?|yrs?)", text or "", re.I)
    if m:
        return f"{m.group(1)}+ years"
    if re.search(r"\b(fresher|entry[- ]level|graduate|intern(ship)?|junior)\b", text or "", re.I):
        return "Entry level"
    return ""


def _posted(value):
    """Unix seconds from an epoch number or an ISO date string; 0 if unknown."""
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    if isinstance(value, str) and value:
        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    return 0


def _job(provider, title, company, location, description, url, job_type="", remote=False, experience="",
         salary=("", "", 0), posted=0):
    description = _plain(description)
    return {"provider": provider, "title": _plain(title, 200), "company": _plain(company, 150), "location": _plain(location, 150),
            "description": description, "url": _safe_url(url), "type": job_type, "remote": bool(remote),
            "experience": experience or _experience(f"{title} {description}"),
            "salary": salary[0], "salary_note": salary[1], "salary_value": salary[2], "posted": _posted(posted)}


# ---- providers ----
ADZUNA_CURRENCY = {"in": "INR", "gb": "GBP", "us": "USD", "ca": "CAD", "au": "AUD", "sg": "SGD", "nz": "NZD", "za": "ZAR",
                   "de": "EUR", "fr": "EUR", "nl": "EUR", "it": "EUR", "es": "EUR", "at": "EUR", "be": "EUR", "pl": "PLN",
                   "br": "BRL", "mx": "MXN", "ch": "CHF"}


def _adzuna(q, location, job_type, days):
    params = {"app_id": config.ADZUNA_APP_ID, "app_key": config.ADZUNA_APP_KEY, "results_per_page": 15,
              "what": q, "where": location, "content-type": "application/json"}
    params.update({"full_time": 1} if job_type == "full-time" else {"part_time": 1} if job_type == "part-time"
                  else {"contract": 1} if job_type == "contract" else {})
    if days:
        params["max_days_old"] = days
    res = requests.get(f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1",
                       params={k: v for k, v in params.items() if v != ""}, timeout=TIMEOUT)
    res.raise_for_status()
    cur = ADZUNA_CURRENCY.get(config.ADZUNA_COUNTRY.lower(), "INR")
    return [_job("Adzuna", j.get("title"), (j.get("company") or {}).get("display_name"), (j.get("location") or {}).get("display_name"),
                 j.get("description"), j.get("redirect_url"), (j.get("contract_time") or "").replace("_", "-"),
                 salary=currency.salary(j.get("salary_min"), j.get("salary_max"), cur, "annual",
                                        str(j.get("salary_is_predicted")) == "1"),
                 posted=j.get("created"))
            for j in res.json().get("results", [])]


def _jobvetta(q, location, job_type, days):
    params = {"q": q, "location": location, "limit": 10, "days": days}
    res = requests.get("https://api.jobvetta.com/v1/jobs", params={k: v for k, v in params.items() if v}, timeout=TIMEOUT,
                       headers={"Authorization": f"Bearer {config.JOBVETTA_API_KEY}"})
    res.raise_for_status()
    out = []
    # The search response has no description (fetching each job would use the 50/day quota), so matching uses the title.
    for j in res.json().get("jobs", []):
        pay = j.get("salary") if isinstance(j.get("salary"), dict) else {}
        sal = currency.salary(pay.get("min", j.get("salary_min")), pay.get("max", j.get("salary_max")),
                              pay.get("currency") or j.get("salary_currency") or "INR", pay.get("period") or "annual")
        out.append(_job("Jobvetta", j.get("title"), j.get("company"), j.get("location"), "", j.get("url"),
                        (j.get("employment_type") or "").lower(), (j.get("work_model") or "").lower() == "remote",
                        salary=sal, posted=j.get("created_at")))
    return out


def _himalayas(q, location, job_type, days):
    params = {"q": q or "developer"}
    if config.HIMALAYAS_COUNTRY:
        params["country"] = config.HIMALAYAS_COUNTRY
    res = requests.get("https://himalayas.app/jobs/api/search", params=params, timeout=TIMEOUT)
    res.raise_for_status()
    out = []
    for j in res.json().get("jobs", [])[:20]:
        regions = j.get("locationRestrictions") or []
        if config.HIMALAYAS_COUNTRY and regions and config.HIMALAYAS_COUNTRY not in regions:
            continue
        if config.HIMALAYAS_COUNTRY in regions:  # show the user's country first
            regions = [config.HIMALAYAS_COUNTRY] + [r for r in regions if r != config.HIMALAYAS_COUNTRY]
        more = f" + {len(regions) - 2} more" if len(regions) > 2 else ""
        where = "Remote (worldwide)" if not regions else "Remote (" + ", ".join(regions[:2]) + more + ")"
        out.append(_job("Himalayas", j.get("title"), j.get("companyName"), where,
                        j.get("description") or j.get("excerpt"), j.get("applicationLink") or j.get("guid"),
                        (j.get("employmentType") or "").lower().replace(" ", "-"), True, ", ".join(j.get("seniority") or []),
                        salary=currency.salary(j.get("minSalary"), j.get("maxSalary"), j.get("currency") or "USD",
                                               j.get("salaryPeriod") or "annual"),
                        posted=j.get("pubDate")))
    return out


SOURCES = {"adzuna": _adzuna, "jobvetta": _jobvetta, "himalayas": _himalayas}


# ---- cache ----
def _cache_get(key):
    cutoff = time.time() - config.CACHE_SECONDS
    if db.available():
        try:
            with db.transaction() as cur:
                cur.execute("DELETE FROM job_listings WHERE fetched_at < NOW() - INTERVAL %s SECOND", [config.CACHE_SECONDS])
                cur.execute("SELECT * FROM job_listings WHERE query_key=%s", [key])
                rows = cur.fetchall()
            if rows:
                return [{"provider": r["provider"], "title": r["title"], "company": r["company"], "location": r["location"],
                         "description": r["description"], "url": r["url"], "type": r["job_type"], "remote": bool(r["remote"]),
                         "experience": r["experience"], "salary": r.get("salary") or "", "salary_note": r.get("salary_note") or "",
                         "salary_value": int(r.get("salary_value") or 0), "posted": int(r.get("posted") or 0)} for r in rows]
        except Exception:
            logging.warning("Job cache read failed; fetching live.")
        return None
    hit = _memory.get(key)
    return hit[1] if hit and hit[0] > cutoff else None


def _cache_put(key, jobs):
    if not jobs:
        return
    if db.available():
        try:
            with db.transaction() as cur:
                for j in jobs:
                    cur.execute("INSERT INTO job_listings (query_key, provider, title, company, location, description, experience,"
                                " job_type, remote, url, salary, salary_note, salary_value, posted) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                [key, j["provider"], j["title"][:300], j["company"][:200], j["location"][:200], j["description"],
                                 j["experience"][:100], j["type"][:60], int(j["remote"]), j["url"][:1000],
                                 j["salary"][:80], j["salary_note"][:200], j["salary_value"], j["posted"]])
        except Exception:
            logging.warning("Job cache write failed.")
        return
    if len(_memory) > 200:
        _memory.clear()
    _memory[key] = (time.time(), jobs)


# ---- search ----
def search(q, location, job_type="all", experience="any", source="all", days=0):
    """Returns (jobs, per-source status, configured). Never invents jobs: only what the providers returned."""
    available = providers()
    chosen = [s for s in SOURCES if source in ("all", s)]
    status, jobs = {}, []
    for name in chosen:
        if not available[name]:
            status[name] = "not configured"
            continue
        key = hashlib.sha1(json.dumps([name, q.lower(), location.lower(), job_type, days], ensure_ascii=False).encode()).hexdigest()
        found = _cache_get(key)
        if found is None:
            try:
                try:
                    found = SOURCES[name](q, location, job_type, days)
                except (requests.ConnectionError, requests.Timeout):  # one retry for a flaky network
                    found = SOURCES[name](q, location, job_type, days)
                _cache_put(key, found)
            except requests.RequestException as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                logging.warning("%s search failed (%s)", name, code or type(e).__name__)
                status[name] = "daily limit reached" if code == 429 else "temporarily unavailable"
                continue
        status[name] = 0
        jobs += found
    jobs = [j for j in jobs if j["url"] and j["title"]]
    if days:
        jobs = [j for j in jobs if not j["posted"] or j["posted"] >= time.time() - days * 86400]
    if job_type != "all":
        jobs = [j for j in jobs if not j["type"] or job_type in j["type"]]
    if experience == "fresher":
        jobs = [j for j in jobs if j["experience"] in ("", "Entry level") or re.match(r"[01]\+", j["experience"])]
    elif experience == "experienced":
        jobs = [j for j in jobs if j["experience"] not in ("Entry level",)]
    seen, unique = set(), []
    for j in jobs:
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k)
            unique.append(j)
    for j in unique:  # count what is actually shown, after filters
        status[j["provider"].lower()] += 1
    status = {k: (f"{v} jobs" if isinstance(v, int) else v) for k, v in status.items()}
    configured = any(available[s] for s in chosen)
    return unique, status, configured
