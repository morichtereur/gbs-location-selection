"""Fetch a sample that is actually about GBS and GCC work.

The earlier study searched "finance operations", "record to report" and
similar, which returns finance roles at any employer. Measured against the
result, only 13% of those 2,159 postings carried an explicit shared-services or
capability-centre signal, and just 8 mentioned a GCC at all. A study about GBS
and GCC locations cannot rest on a sample that is seven-eighths retained
finance, so this fetches its own.

Two changes beyond the search terms:

*Adzuna for every market.* The earlier snapshot used Jooble for the United
Kingdom and South Africa, and Jooble returns no location string — which is why
neither market could be resolved to a city. Adzuna covers all ten and carries
location, so both become resolvable.

*A wider net than the classifier.* The queries are deliberately loose, because
recall matters more than precision at fetch time; `src/delivery.py` decides what
is genuinely in scope afterwards, where the decision is visible and testable.
"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import duckdb
import requests

from src import config as C

API = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
RESULTS_PER_PAGE = 50
MAX_PAGES = int(os.getenv("GBSLOC_MAX_PAGES", "5"))
REQUEST_INTERVAL = 0.4

# Terms aimed at the delivery model rather than the process. "Finance
# operations" is deliberately absent: it was the main source of retained-finance
# noise in the earlier sample.
# Adzuna ANDs every word in a query, so long phrases silently return nothing:
# "shared services centre finance" found zero postings in Germany, a market
# with 1,019 for "shared services" alone. Terms are kept short deliberately.
SEARCH_TERMS = [
    "global capability centre",
    "global capability center",
    "global business services",
    "shared services",
    "shared service center",
]

# Shared-services roles in Poland, Spain and Mexico are often advertised in the
# local language, and an English-only query misses them. German and Dutch ads
# mostly use the English terms above, which the probe above confirmed.
LOCAL_TERMS = {
    "pl": ["centrum usług wspólnych", "SSC finance"],
    "es": ["servicios compartidos"],
    "mx": ["servicios compartidos", "centro de servicios compartidos"],
}

DB_PATH = C.DATA / "gbs_postings.duckdb"


def _env() -> tuple[str, str]:
    """Credentials come from the sibling repo's .env or the environment."""
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if app_id and app_key:
        return app_id, app_key
    env = C.POSTINGS_DB.parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        raise RuntimeError(
            "ADZUNA_APP_ID and ADZUNA_APP_KEY are required. Register a free key "
            "at https://developer.adzuna.com/ and export both, or place them in "
            f"{env}."
        )
    return app_id, app_key


def _page(country: str, term: str, page: int, app_id: str, app_key: str) -> list[dict]:
    response = requests.get(
        API.format(country=country, page=page),
        params={
            "app_id": app_id, "app_key": app_key, "what": term,
            "results_per_page": RESULTS_PER_PAGE, "content-type": "application/json",
        },
        timeout=45,
    )
    if response.status_code != 200:
        return []
    return response.json().get("results", [])


def _init(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS postings (
            id VARCHAR PRIMARY KEY, country VARCHAR, term VARCHAR, title VARCHAR,
            company VARCHAR, description VARCHAR, location VARCHAR,
            created VARCHAR, redirect_url VARCHAR, fetched_at VARCHAR
        )
        """
    )


def fetch() -> int:
    app_id, app_key = _env()
    C.DATA.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    _init(con)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    seen = 0

    for country in C.MARKETS:
        for term in SEARCH_TERMS + LOCAL_TERMS.get(country, []):
            for page in range(1, MAX_PAGES + 1):
                results = _page(country, term, page, app_id, app_key)
                if not results:
                    break
                for r in results:
                    ident = str(r.get("id") or hashlib.sha256(
                        f"{r.get('title')}{r.get('redirect_url')}".encode()
                    ).hexdigest()[:24])
                    con.execute(
                        "INSERT OR IGNORE INTO postings VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [
                            ident, country, term, r.get("title") or "",
                            (r.get("company") or {}).get("display_name") or "",
                            r.get("description") or "",
                            (r.get("location") or {}).get("display_name") or "",
                            r.get("created") or "", r.get("redirect_url") or "", stamp,
                        ],
                    )
                    seen += 1
                time.sleep(REQUEST_INTERVAL)
        total = con.execute(
            "SELECT count(*) FROM postings WHERE country = ?", [country]
        ).fetchone()[0]
        print(f"  {country}: {total} unique postings held")

    total = con.execute("SELECT count(*) FROM postings").fetchone()[0]
    con.close()
    print(f"{seen} results seen, {total} unique postings in {DB_PATH.name}")
    return total


if __name__ == "__main__":
    fetch()
