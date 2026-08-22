"""Who already runs a centre in each city.

The question a room always asks — "who is there already?" — and the postings
answer it without another source: 85% of them carry the operator's own name.

Two things have to be cleaned first, and both are visible lists rather than a
model, so a reader can disagree with a specific entry.

*Recruiters are not operators.* Michael Page advertising a Kraków role says
nothing about who runs a centre there. They are 15% of named postings and are
excluded, and the count of what was excluded is reported rather than hidden.

*One company appears under several names.* "Heineken Kraków", "Heineken Sp. z
o.o." and "HEINEKEN Global Shared Services" are one operator. Names are
normalised by stripping legal forms and site suffixes, which merges the obvious
cases and will still miss some.
"""

from __future__ import annotations

import collections
import re

from src.population import load

# Staffing and search firms. They advertise the work; they do not run the centre.
AGENCY = re.compile(
    r"michael page|hays\b|robert half|robert walters|adecco|randstad|manpower|"
    r"experis|antal|\blhh\b|recruit|staffing|talent solutions|persol|hudson|"
    r"grafton|\bcpl\b|morgan mckinley|brunel|gi group|sthree|nigel frank|"
    r"page personnel|link group|praca|peoplefinder|resume|vanrath|job-room|"
    r"\bsearch\b|selection|headhunt|personalberatung|personalmanagement|"
    r"consultancy|consulting group|\bwe search\b|jobskey|nlwerkt|werkt\b",
    re.I,
)

# Legal forms and site suffixes that split one operator into several names.
# Applied after punctuation is stripped, so "Sp. z o.o." arrives as "sp z o o".
NOISE = re.compile(
    r"\b(sp z o o|s a|gmbh|ag|ltd|limited|llc|inc|plc|bv|nv|sarl|srl|pvt|"
    r"private|corporation|corp|company|co|group|holding|holdings|"
    r"international|global|europe|emea|services|service center|service centre|"
    r"shared services|business services|gbs|ssc|solutions)\b",
    re.I,
)
CITY_SUFFIX = re.compile(
    r"\b(krak[oó]w|wroc[łl]aw|warsaw|warszawa|pozna[nń]|gda[nń]sk|[łl][oó]d[źz]|"
    r"pune|mumbai|bangalore|bengaluru|hyderabad|chennai|deutschland|polska|"
    r"india|polska)\b",
    re.I,
)


def canonical(name: str) -> str:
    """Collapse a company's several spellings to one."""
    n = (name or "").lower()
    n = re.sub(r"[.,()\"'/]", " ", n)
    # Collapse before matching: stripping "Sp. z o.o." leaves double spaces and
    # the pattern expects single ones, which is why legal forms survived a
    # first pass and split one operator into several.
    n = re.sub(r"\s+", " ", n).strip()
    n = CITY_SUFFIX.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    n = NOISE.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip(" -&")
    return n


def title(name: str) -> str:
    """Presentable form, preserving well-known capitalisations."""
    keep = {"ups": "UPS", "abb": "ABB", "sap": "SAP", "ibm": "IBM", "bp": "BP",
            "gia": "GIA", "dnv": "DNV", "exl": "EXL", "arko": "ARKO",
            "ppg": "PPG", "iff": "IFF", "dsv": "DSV", "nec": "NEC"}
    return " ".join(keep.get(w, w.capitalize()) for w in name.split())


def by_city(cities_only: bool = True) -> dict[tuple[str, str], list[tuple[str, int]]]:
    """Operators per (market, city), most postings first.

    Restricted by default to the cities the study actually ranks; the sample
    names employers in dozens of places that never clear the centre thresholds,
    and listing them implies a centre where there is one office.
    """
    keep = None
    if cities_only:
        from src.centres import survey

        kept, _ = survey()
        keep = {(c.market, c.name) for c in kept}
    counts: dict[tuple[str, str], collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for posting in load():
        if not (posting.city and posting.company):
            continue
        if keep is not None and (posting.country, posting.city) not in keep:
            continue
        if AGENCY.search(posting.company):
            continue
        key = canonical(posting.company)
        if len(key) < 2:
            continue
        counts[(posting.country, posting.city)][key] += 1
    return {k: v.most_common() for k, v in counts.items()}


def agency_share() -> tuple[int, int]:
    """(postings from agencies, postings carrying any employer name)."""
    named = [p for p in load() if p.company]
    return sum(1 for p in named if AGENCY.search(p.company)), len(named)


def main() -> None:
    agencies, named = agency_share()
    print(f"{named} postings name an employer; {agencies} "
          f"({agencies / named:.0%}) are recruiters and are excluded.\n")
    from src import config as C

    for (market, city), ops in sorted(by_city().items(), key=lambda kv: -len(kv[1])):
        names = ", ".join(title(n) for n, _ in ops[:6])
        print(f"  {C.MARKETS[market]['name']:13} {city:13} {len(ops):3} named — {names}")


if __name__ == "__main__":
    main()
