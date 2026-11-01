"""Optional MySQL connection. Everything works without it."""
import logging
import pathlib
from contextlib import contextmanager

import pymysql

import config

_ready = False
MIGRATIONS = ["salary VARCHAR(80)", "salary_note VARCHAR(200)", "salary_value BIGINT", "posted BIGINT"]


def _connect():
    return pymysql.connect(**config.MYSQL, charset="utf8mb4", autocommit=False,
                           cursorclass=pymysql.cursors.DictCursor, connect_timeout=5)


def init():
    """Creates tables from schema.sql. Raises if MySQL is not configured or unreachable."""
    global _ready
    if not config.MYSQL["user"]:
        return
    schema = (pathlib.Path(__file__).resolve().parent.parent / "schema.sql").read_text(encoding="utf-8")
    statements = [s.strip() for s in schema.split(";") if s.strip()]
    with transaction() as cur:
        for stmt in statements:
            cur.execute(stmt)
        for col in MIGRATIONS:  # columns added after the first release; existing tables get them here
            try:
                cur.execute(f"ALTER TABLE job_listings ADD COLUMN {col}")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060:  # 1060 = duplicate column, already migrated
                    raise
    _ready = True
    logging.info("MySQL storage ready.")


def available():
    return _ready


@contextmanager
def transaction():
    conn = _connect()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
