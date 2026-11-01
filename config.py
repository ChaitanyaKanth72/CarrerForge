import os
from dotenv import load_dotenv

load_dotenv()
env = os.environ.get

GEMINI_API_KEY = env("GEMINI_API_KEY", "")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_THINKING_BUDGET = env("GEMINI_THINKING_BUDGET", "0")  # "" = the model's default (slow on Flash)
ADZUNA_APP_ID = env("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = env("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = env("ADZUNA_COUNTRY", "in")
JOBVETTA_API_KEY = env("JOBVETTA_API_KEY", "")
PORT = int(env("PORT", "5000"))  # macOS AirPlay Receiver uses 5000; set PORT=5001 in .env there
HIMALAYAS_ENABLED = env("HIMALAYAS_ENABLED", "true").lower() == "true"
HIMALAYAS_COUNTRY = env("HIMALAYAS_COUNTRY", "India")  # only remote jobs open to this country (blank = worldwide)
USD_INR = float(env("USD_INR", "95"))  # used only if live exchange rates cannot be fetched

MYSQL = dict(host=env("MYSQL_HOST", "localhost"), port=int(env("MYSQL_PORT", "3306")),
             user=env("MYSQL_USER", ""), password=env("MYSQL_PASSWORD", ""), database=env("MYSQL_DB", "careerforge"))

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
CACHE_SECONDS = 600
