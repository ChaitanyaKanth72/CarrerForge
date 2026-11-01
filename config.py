import os
from dotenv import load_dotenv

load_dotenv()
env = os.environ.get

GEMINI_API_KEY = env("GEMINI_API_KEY", "")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-flash-latest")
ADZUNA_APP_ID = env("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = env("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = env("ADZUNA_COUNTRY", "in")
JOBVETTA_API_KEY = env("JOBVETTA_API_KEY", "")
HIMALAYAS_ENABLED = env("HIMALAYAS_ENABLED", "true").lower() == "true"

MYSQL = dict(host=env("MYSQL_HOST", "localhost"), port=int(env("MYSQL_PORT", "3306")),
             user=env("MYSQL_USER", ""), password=env("MYSQL_PASSWORD", ""), database=env("MYSQL_DB", "careerforge"))

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
CACHE_SECONDS = 600
