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
JOOBLE_API = "https://jooble.org/api/{key}"
RESULTS_PER_PAGE = 50
# Deep enough that every market exhausts. Probed per market: Switzerland and
# the Netherlands run dry after one page, Spain and Singapore around eight,
# Germany around twenty, and the United Kingdom and India were still returning
# full pages at forty. A cap that binds on the largest markets and not the
# smallest silently understates the employer-depth pillar for the biggest ones.
MAX_PAGES = int(os.getenv("GBSLOC_MAX_PAGES", "42"))
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
    "br": ["serviços compartilhados", "centro de serviços compartilhados"],
}

DB_PATH = C.DATA / "gbs_postings.duckdb"


def _load_env() -> None:
    """Pull credentials from the sibling repo's .env if they are not exported."""
    env = C.POSTINGS_DB.parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _env() -> tuple[str, str]:
    """Credentials come from the sibling repo's .env or the environment."""
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if app_id and app_key:
        return app_id, app_key
    _load_env()
    env = C.POSTINGS_DB.parent.parent / ".env"
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


def _jooble_page(key: str, country: str, term: str, page: int) -> list[dict]:
    """One page from Jooble, which serves the markets Adzuna does not.

    Jooble returns no structured location field, so postings from it cannot be
    resolved to a city — those markets will appear in the country panel and not
    in the city ranking. That is a real limitation of the source and is better
    than leaving six GBS markets out of the study entirely.
    """
    response = requests.post(
        JOOBLE_API.format(key=key),
        json={"keywords": term, "location": country.upper(), "page": str(page)},
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "User-Agent": "gbs-location-selection/1.0"},
        timeout=45,
    )
    if response.status_code != 200:
        # Distinguish the two failures, because they need opposite responses and
        # look identical in a status code. Cloudflare serves an HTML error page
        # when it blocks a client at the edge — that is bot protection refusing
        # automated access, and the request never reaches Jooble, so no key will
        # fix it. A JSON body is Jooble itself answering, and there a 403 really
        # does mean the credential.
        body = response.text[:200].lstrip("\ufeff")
        edge_block = body.lstrip().startswith("<") or "cloudflare" in (
            response.headers.get("server", "").lower()
        )
        if edge_block:
            raise RuntimeError(
                f"Jooble is refusing automated requests at the edge "
                f"(HTTP {response.status_code}, Cloudflare) for {country}. This "
                "is not a key problem and cannot be worked around — the block is "
                "the site declining programmatic access. Leave these markets out "
                "or use a source that permits it."
            )
        raise RuntimeError(
            f"Jooble returned HTTP {response.status_code} for {country}: "
            f"{body}. Check JOOBLE_API_KEY; register free at "
            "https://jooble.org/api/about."
        )
    payload = response.json()
    return payload.get("jobs", payload.get("results", []))


def fetch_jooble(only: tuple[str, ...] | None = None) -> int:
    """Top the sample up with the markets Adzuna cannot serve.

    Skipped silently when no key is set, so `make fetch` keeps working for
    anyone without one; the markets simply stay out of the panel, which is what
    the study already reports.
    """
    key = os.getenv("JOOBLE_API_KEY") or ""
    if not key:
        _load_env()
        key = os.getenv("JOOBLE_API_KEY") or ""
    if not key:
        print("no JOOBLE_API_KEY set — skipping "
              f"{', '.join(C.UNREACHABLE.values())}")
        return 0

    con = duckdb.connect(str(DB_PATH))
    _init(con)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    today = time.strftime("%Y-%m-%d")
    added = 0
    for country in C.JOOBLE_MARKETS:
        if only and country not in only:
            continue
        for term in SEARCH_TERMS + LOCAL_TERMS.get(country, []):
            for page in range(1, MAX_PAGES + 1):
                try:
                    results = _jooble_page(key, country, term, page)
                except RuntimeError as error:
                    print(f"  {error}")
                    con.close()
                    return added
                if not results:
                    break
                for r in results:
                    ident = "jooble_" + hashlib.sha256(
                        str(r.get("id") or r.get("link") or r.get("title", "")).encode()
                    ).hexdigest()[:24]
                    con.execute(
                        "INSERT OR IGNORE INTO postings VALUES (?,?,?,?,?,?,?,?,?,?)",
                        [
                            ident, country, term, r.get("title") or "",
                            r.get("company") or "", r.get("snippet") or "",
                            # Jooble's location is a free-text string rather than
                            # a structured field, and often just the country.
                            r.get("location") or "",
                            r.get("updated") or "", r.get("link") or "", stamp,
                        ],
                    )
                    con.execute(
                        "INSERT OR IGNORE INTO observations VALUES (?,?,?)",
                        [ident, today, country],
                    )
                    added += 1
                time.sleep(REQUEST_INTERVAL)
        held = con.execute(
            "SELECT count(*) FROM main.postings WHERE country = ?", [country]
        ).fetchone()[0]
        print(f"  {country}: {held} unique postings held")
    con.close()
    print(f"{added} results seen from Jooble")
    return added


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
    # `postings` keeps one row per advertisement, first seen wins. That cannot
    # answer whether a market is growing, because a posting found in March and
    # again in June looks identical to one found only in March. Presence is
    # therefore recorded per run, so each snapshot can be counted on its own.
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS observations (
            id VARCHAR, snapshot DATE, country VARCHAR,
            PRIMARY KEY (id, snapshot)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot DATE PRIMARY KEY, markets VARCHAR, max_pages INTEGER,
            terms INTEGER, note VARCHAR
        )
        """
    )


def backfill(con: duckdb.DuckDBPyConnection) -> int:
    """Record the existing postings as one snapshot, dated when they were seen.

    Snapshot tracking arrived after the first fetches. Without this the sample
    already on disk would have no observation rows and would vanish from any
    trend — throwing away real data to tidy a schema.
    """
    already = con.execute("SELECT count(*) FROM main.observations").fetchone()[0]
    if already:
        return 0
    con.execute(
        """
        INSERT OR IGNORE INTO main.observations
        SELECT id, CAST(substr(fetched_at, 1, 10) AS DATE), country FROM main.postings
        WHERE fetched_at IS NOT NULL AND length(fetched_at) >= 10
        """
    )
    con.execute(
        """
        INSERT OR IGNORE INTO main.snapshots
        SELECT DISTINCT snapshot, 'backfilled', NULL, NULL,
               'reconstructed from posting fetch dates'
        FROM main.observations
        """
    )
    return con.execute("SELECT count(*) FROM main.observations").fetchone()[0]


def fetch(only: tuple[str, ...] | None = None) -> int:
    """Fetch the sample. `only` limits to named markets, for topping up one
    market without re-querying the rest."""
    app_id, app_key = _env()
    C.DATA.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    _init(con)
    restored = backfill(con)
    if restored:
        print(f"backfilled {restored} observations from earlier fetches")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    today = time.strftime("%Y-%m-%d")
    seen = 0

    for country in C.MARKETS:
        if only and country not in only:
            continue
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
                    con.execute(
                        "INSERT OR IGNORE INTO observations VALUES (?,?,?)",
                        [ident, today, country],
                    )
                    seen += 1
                time.sleep(REQUEST_INTERVAL)
        total = con.execute(
            "SELECT count(*) FROM postings WHERE country = ?", [country]
        ).fetchone()[0]
        print(f"  {country}: {total} unique postings held")

    fetched = sorted(only) if only else sorted(C.MARKETS)
    con.execute(
        "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)",
        [today, ",".join(fetched), MAX_PAGES, len(SEARCH_TERMS), ""],
    )
    total = con.execute("SELECT count(*) FROM postings").fetchone()[0]
    snaps = con.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    con.close()
    print(f"{seen} results seen, {total} unique postings in {DB_PATH.name}")
    print(f"snapshot {today} recorded ({snaps} snapshot(s) held)")
    return total


if __name__ == "__main__":
    import sys

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    markets = tuple(args) or None
    if "--jooble" not in flags:
        fetch(markets)
    # Jooble serves the six markets Adzuna has no endpoint for. It is attempted
    # on every run and skips itself with a message when no key is set, so the
    # study works with or without one.
    if "--adzuna" not in flags:
        fetch_jooble(markets)
