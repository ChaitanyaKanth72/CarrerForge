"""Shows every salary in Indian rupees. Live rates from Frankfurter (ECB data, no key), cached; fallback rates if offline."""
import logging
import threading
import time

import requests

import config

RATES_URL = "https://api.frankfurter.dev/v1/latest"
CACHE_SECONDS = 12 * 3600

_lock = threading.Lock()
_rates = {"at": 0.0, "inr_per": {}}


def _fallback():
    return {"INR": 1.0, "USD": config.USD_INR, "EUR": config.USD_INR * 1.12, "GBP": config.USD_INR * 1.34,
            "CAD": config.USD_INR * 0.72, "AUD": config.USD_INR * 0.65, "SGD": config.USD_INR * 0.77}


def inr_per():
    """{currency: rupees per 1 unit}. Refreshed at most every 12 hours."""
    with _lock:
        if time.time() - _rates["at"] < CACHE_SECONDS and _rates["inr_per"]:
            return _rates["inr_per"]
        try:
            res = requests.get(RATES_URL, params={"base": "INR"}, timeout=8)
            res.raise_for_status()
            per_inr = res.json()["rates"]
            rates = {cur: 1 / v for cur, v in per_inr.items() if v} | {"INR": 1.0}
            _rates.update(at=time.time(), inr_per=rates)
        except (requests.RequestException, KeyError, ValueError, TypeError):
            logging.warning("Exchange rates unavailable; using fallback rates.")
            _rates.update(at=time.time() - CACHE_SECONDS + 600, inr_per=_fallback())  # retry in 10 minutes
        return _rates["inr_per"]


def group(n):
    """Indian digit grouping: 1234567 -> 12,34,567."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + parts + [tail])


def _num(v):
    try:
        v = float(v)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def salary(min_, max_, currency="INR", period="annual", estimated=False):
    """Returns (label, note, yearly rupees for sorting), e.g. ("₹6 – 9 LPA", "", 600000); ("", "", 0) if unknown."""
    lo, hi = _num(min_), _num(max_)
    if not lo and not hi:
        return "", "", 0
    lo, hi = lo or hi, hi or lo
    if lo > hi:
        lo, hi = hi, lo
    currency = (currency or "INR").upper()
    rate = inr_per().get(currency)
    if rate is None:
        return "", "", 0
    period = (period or "annual").lower()
    a, b = lo * rate, hi * rate
    if currency != "INR":  # a converted figure is approximate; don't show false precision
        nice = lambda x: round(x, -3) if x >= 10000 else round(x, -1)
        a, b = nice(a), nice(b)
    if period in ("annual", "yearly", "year") and a >= 100000:
        lakh = lambda x: f"{x / 100000:.1f}".rstrip("0").rstrip(".")
        label = f"₹{lakh(a)} LPA" if lakh(a) == lakh(b) else f"₹{lakh(a)} – {lakh(b)} LPA"
    else:
        unit = {"monthly": "/month", "month": "/month", "hourly": "/hour", "hour": "/hour", "weekly": "/week",
                "daily": "/day"}.get(period, "/year")
        label = f"₹{group(a)}{unit}" if round(a) == round(b) else f"₹{group(a)} – {group(b)}{unit}"
    notes = []
    if currency != "INR":
        orig = f"{currency} {group(lo)}" + (f"–{group(hi)}" if round(lo) != round(hi) else "")
        notes.append(f"Converted from {orig} {period} at ₹{rate:.2f}/{currency}")
    if estimated:
        notes.append("Estimated by the job site")
    per_year = {"monthly": 12, "month": 12, "hourly": 2000, "hour": 2000, "weekly": 52, "daily": 250}.get(period, 1)
    return label, ". ".join(notes), int(a * per_year)
