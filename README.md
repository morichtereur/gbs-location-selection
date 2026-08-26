# GBS Location Selection

**Where should a shared-services or capability centre go — and how much of that answer is evidence rather than opinion?**

A location study arrives as three cities and a weighted scorecard. The weights were agreed in a workshop, and the weights are what chose the three cities. This scores 11 cities on seven pillars from public data, then re-scores them 10,000 times across every weighting somebody could have defended, and reports what survives.

**[Interactive tool](dashboard.html)** · `make dashboard`

---

## What it finds

**1. A transactional hub is a cost ranking wearing six other pillars.**
Removing each pillar in turn, only cost changes the shortlist. Talent, governance, capability, overlap, durability and employer depth can each be deleted without moving it. For a judgment centre, five of seven move it.

**2. Cities the evidence cannot separate are not ranked.**
Seven of the 55 city pairs finish closer than 65/35. Those cities share a band rather than being given invented positions. For a transactional hub that is one band holding all five Indian cities.

**3. The cheapest markets are a currency bet.**
India and Brazil look like the most durable cost positions in the panel. Local wages are rising 5–7% a year in both; a weakening currency has been hiding it from a dollar buyer. Poland's 8.5% is real wage growth with no currency help.

**4. Filtering the sample changes which city leads.**
Warsaw dominates Poland on a broad finance sample because it is the largest finance job market. On GBS and GCC work alone, **Kraków** leads — because it is the largest shared-services one.

**5. The shift to value work is not visible in hiring yet.**
Across 378 classified GBS and GCC postings: **62% transactional, 37% judgment,
and essentially no AI-adjacent roles at all.** Only Mexico shows any, and that is
one posting. The practitioner argument that GBS is moving from labour arbitrage
to value creation is a claim about direction; on the hiring side the base is
still overwhelmingly processing work. A point-in-time sample cannot show a
trend, so this does not contradict the direction — it establishes where the
starting point actually is.

The tool is built around the same distinction. Its two centre types *are*
arbitrage and value work, and the pillar test above says something sharp about
them: a transactional hub is decided by cost alone, while a judgment centre
needs five of seven pillars. Cheap labour is sufficient to site arbitrage work
and nowhere near sufficient to site value work.

![What the filter changed](data/chart_filter.png)

---

## The cities

Evidenced from job postings, not asserted: a location qualifies only where GBS or GCC roles are advertised by four or more employers.

| market | cities |
|---|---|
| Poland | Kraków, Wrocław, Warsaw, Poznań |
| India | Bangalore, Pune, Hyderabad, Mumbai, Chennai |
| Brazil | São Paulo |
| South Africa | Johannesburg |

Four have city-level labour cost, from Eurostat's regional accounts. The rest carry their country's, so cities within them differ on capability alone.

---

## The pillars

| pillar | source |
|---|---|
| Cost | ILOSTAT earnings by occupation — ISCO-08 2/3/4, USD, aged to a common year |
| Talent | ILOSTAT employment by occupation — same three groups |
| Governance | World Bank Worldwide Governance Indicators — five dimensions with their 90% intervals |
| Capability | Adzuna postings, classified as GBS/GCC work |
| Overlap | Computed — working hours shared with a declared headquarters |
| Durability | ILOSTAT, derived — wage drift, split from currency movement |
| Employer depth | Adzuna, derived — distinct employers hiring |

**What the move is worth** is the question that follows the ranking, so the
dashboard answers it: the annual wage gap between a baseline market and each
city, for a headcount you set. Zurich to Kraków is about USD 54k per role per
year; to any of the Indian cities about USD 95k. Sixteen markets can be the origin (`make baselines`). Ten of them are priced
by ILOSTAT but never scored — the study needs seven pillars per candidate and
these carry one — because "we are moving work out of France" was a question the
tool had been refusing for no better reason than that France is not a
candidate. ILOSTAT has no earnings in this dataflow for Canada, Australia or
Japan.

**The wage is not the cost, so the exhibit now loads it.** Three multipliers sit
between a gross ILOSTAT wage and what a role costs, and all three are on the
exhibit as controls: employer social charges, an attrition/backfill uplift, and
a horizon. Base and loaded run side by side, so Zurich to Kraków is USD 54k per
role on the wage line and about **USD 59k loaded** at the declared defaults; to
the Indian cities, 95k becomes about **118k**. Two of the three are assumptions
the reader sets and the page says so where they are set — no free source gives
comparable employer-charge schedules for all eleven markets, so the factor is
**uniform, which scales every gap and cannot reorder them**, while real charges
differ sharply by country and pricing that difference is exactly what this
cannot do. The attrition uplift applies to the destination only, since the
origin is not being stood up, and it *can* reorder, because it scales with a
city's own wage. The third is not an assumption at all: the horizon carries each
market forward at its own **measured** drift, which is what makes the durability
finding concrete — over five years the Kraków gap closes from USD 5.4m to 4.0m
for 100 roles, because Poland's 8.5% outruns Switzerland's 2.2%. South Africa
has too short a series to measure a drift, so Johannesburg reports as **not
projectable** rather than being carried at the panel median.

One asymmetry decides how far that comparison can be pushed: the baseline is
always a national figure, while the Polish cities carry a regional index
against their own country mean (Warsaw 1.81, Kraków 1.46). Against a UK
baseline Warsaw therefore reads as *dearer* than the UK, which is a capital
region measured against a national average rather than a wage fact. This is the wage line only —
it excludes facilities, technology, management overhead, transition and
severance, and holds headcount one-for-one, which for a ramping centre is
optimistic. It is an upper bound on one component, not a saving.

**The unreachable locations are priced, not omitted** (`make beyond`). Manila is
the first name a GBS room says, and the study could not put a number on it at
all. That was a gap in the tool rather than a fact about Manila: wages,
employed stock, governance and overlap come from sources that cover every
country alike, and only the two pillars built from job postings stop at
Adzuna's country list. So Manila, Kuala Lumpur, Lisbon, Bucharest, Prague and
Budapest are reported on those five — Manila at USD 505 a month against
India's 342, with the largest relevant workforce in the comparison at 9.2m —
and are **never scored or ranked**, because a score over five of seven pillars
would render beside the ranked cities' scores and would not mean the same
thing.

Eleven locations are reported that way, from Prague at USD 3,128 a month down
to Ho Chi Minh City at 478. Three other kinds of absence are named rather than
left blank: **seen but too thin** (105 locations appear in the sample and clear
neither threshold — Gdańsk and Katowice at 7 postings from 3 employers come
closest, and the employer count is usually what stops them); **not priceable at
all** (ILOSTAT publishes no earnings by occupation for China or Morocco, so
Wuxi and Casablanca have no cost figure on the basis every other market uses);
and **incoherent** (Egypt reports professionals at 1.06× clerical pay against
1.3–2.9× everywhere else, which is a broken series rather than a cheap country,
and `MIN_PROFESSIONAL_PREMIUM` excludes it by a test rather than a judgement).

A second job board does not fix this. Employer depth counts distinct
employers *within one feed*; another feed's count is not comparable, so
splicing one in would move Manila into the ranking on evidence unlike the
rest. The Muse API was tested and rejected for a different reason: its
location filter is inert, and "Atlantis, Nowhere" returns the same 110 jobs
as Manila.

**The finding is stated before anything is asked of the reader.** The page opens
with the top band named and called indistinguishable, at the weighting the study
declares — and says whose weighting it is reporting, so it cannot read as the
study's conclusion once a reader has moved a slider. One control stays in the
open, the centre type, because it is the choice the whole argument turns on.
Weights, headquarters and the cost inputs sit behind an *adjust assumptions*
disclosure: an exhibit that has to be configured before it says anything is a
tool, not an exhibit.

**The boundary is stated on the exhibit, not in a footnote.** What public
evidence settles here and what it cannot are set side by side beneath the
ranking, both built from the run on screen so they move when the weighting
does. The tool covers eleven cities and one function on public data alone;
saying where that stops is the finding, not a disclaimer.

**The document says what the page says, before any script runs.** Every figure
on the exhibit is written by JavaScript, which used to leave the shipped file as
empty tags and half-finished sentences — that is what a crawler indexes and
what reader mode extracts. The declared scenario is now rendered in Python
(`src/fallback.py`) and baked into the document at build time; the script
overwrites it on load with the same content, and a test runs the page's own
JavaScript under a DOM shim and requires the two renderings to agree word for
word on every claim, and city for city on the ranking. The page also carries a
meta description stating the finding rather than the subject, and a link-preview
card (`make og`, `data/og.png`) drawing Exhibit 1 at the declared weights — both
built from the run, not written down.

**A workbook** (`make excel`) carries the same study for readers who will not
open a browser: what it does and does not claim, the seven criteria with their
sources and both starting weightings, the ranking with band and stability, and
the wage gap priced against all sixteen origins so the comparison can be
re-based in the sheet, and the locations it cannot rank with the three
reasons they are absent. The dashboard cannot hand a file over — its published
form runs under a policy that blocks downloads a page starts itself — so the
workbook is built here instead.

**Who is already there** is reported per city — Heineken, Huntsman, Euroclear and
six others in Kraków; Cisco, Booking and ABB among fourteen in Bangalore. The
postings carry the operator's own name in 85% of cases, so the question a room
always asks needs no further source. Staffing firms are removed (16% of named
postings) and one company's several spellings are merged, both by visible lists
in [`src/operators.py`](src/operators.py). `make operators` prints the full list.

Two further facts are **reported per city and deliberately not scored**:
**languages** the city's postings ask for (Wrocław 50%, Warsaw 41%, Indian cities
0–5% — more languages is a strength only if you need them), and cost in **PPP**
alongside USD (an Indian wage of $336 buys $1,478 locally). PPP answers what a
wage is worth to the person earning it rather than what it costs you, and it does
not reorder anything, because the cheapest market is cheapest on both bases.

Every declared judgement — weights, archetypes, thresholds, the staffing blend — sits in [`src/config.py`](src/config.py), so a reader can disagree with a number rather than with the conclusion.

---

**The page closes on what would change it** — the three checks a phase-2
shortlist validation would actually run, each replacing an input this analysis
cannot source from public data: live wage and employer-charge quotes for the
top band (its cost is mostly national and the loading factor is a uniform
assumption), site visits against the advertised capability (a pillar resting on
as few as four postings per city), and attrition and ramp data from the
employers already operating there (the backfill uplift is the one Exhibit 3
input that can reorder cities, and today it is a slider). Written from the run
on screen, so the band, the counts and the rates are always the current ones.

## What it cannot tell you

- **Tax and incentives are absent, and attrition is an assumption rather than a measurement.** Exhibit 3 carries an attrition/backfill uplift the reader sets, which is not the same as knowing what attrition costs in Pune against Kraków — no free public source gives comparable rates, and that difference is probably the most important thing still missing.
- **The Philippines, Romania, Czechia, Hungary, Portugal and Malaysia are missing.** Five of seven pillars are ready for all six; no permitted postings feed exists. Adzuna has no endpoint, EURES forbids automated extraction, Jooble blocks it at the edge.
- **India has no city-level cost** in any reachable source, so its five cities separate on capability alone.
- **The capability classifier is imperfect** — two clear failures in the last audited twenty, across five audits and a hundred postings. That error is modelled in the resampling, not just noted; doing so reversed which market is robust as a judgment location.
- **No infrastructure or flight connectivity.** Flight data is reachable —
  OpenFlights covers 9 of the 11 cities — but its routes file has not been
  updated since 2017, which is staler than anything else in the panel. Left out
  rather than caveated harder than the six-year-old wage figures.
- **The seven pillars are not independent, and that weakens the reweighting claim.** The
  average pair of pillars correlates at 0.58, nine of the twenty-one pairs sit at 0.7 or
  above, and the panel carries about **two independent directions, not seven**
  (`make correlation`). Five of the seven pillars — talent, governance, overlap,
  durability and employer depth — are national series that take one value per country
  across these cities, so they cannot separate two cities in the same country however
  they are weighted, and the four countries then line up on close to a single axis:
  the cheaper markets sit further from a European working day, score lower on
  governance, and have had flatter dollar wage drift. The 2,000 reweightings therefore
  explore substantially less of the decision space than the count suggests. This is
  measured and reported on the exhibit rather than caveated; it is also the mechanism
  behind finding 1 above.
- **One snapshot, 22 August 2026.** `make trend` compares snapshots and says so until a
  second exists. The date, the board, the five search terms, the page depth and the
  markets covered are read back out of the fetch's own record and shown on the page
  (`make provenance`) rather than typed into it, so a refetch moves the provenance line
  instead of leaving it confidently stale.

---

## Run it

```
make install
make fetch      # dated posting snapshot (free Adzuna credentials)
make run        # analysis, charts, RESULTS.md
make dashboard  # the interactive tool
make test
```

`make refresh` does the whole cycle. Monthly is the right cadence — the postings feed turns over faster than that, the statistical series update annually.

Also available: `make validate` (is the measured subset representative?), `make leverage` (which pillars decide the answer?), `make correlation` (how independent are the pillars, and what does that do to the reweighting claim?), `make provenance` (what was scraped, when, and how old is each series?), `make centres` (what qualifies as a city, and what the thresholds exclude), `make shot` (render the tool to PNG).

Full numbers in [RESULTS.md](RESULTS.md). Classifier audits in [eval/precision_audit.md](eval/precision_audit.md).
