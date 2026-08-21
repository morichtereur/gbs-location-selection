# gbs-location-selection

**A shared-services location shortlist, and a measurement of how much of it was ever really in play.**

A location study arrives as three cities and a weighted scorecard. The weights
were set in a workshop, and the weights are what chose the three cities. The
study is then presented as measurement.

This scores ten markets on six pillars from public data, and then does the
part that is usually skipped: re-scores them ten thousand times under every
weighting somebody in that room could have defended, and reports how often each
market survives.

![Rank stability](data/chart_stability.png)

There is also an **[interactive dashboard](dashboard.html)** — move the weights,
watch the ranking reorder, and watch a live stability meter say how much of your
new answer would survive somebody else's equally defensible opinion. Build it
with `make dashboard`.

## Key finding

**The same panel answers one archetype's question and barely answers the other's.**

| | transactional hub | judgment centre of excellence |
|---|---|---|
| robust in the top 3 (≥90% of weightings) | **1** — India 100.0% | **1** — Germany 99.8% |
| never shortlisted (<10%) | 5 | 4 |
| baseline top three | India, United Kingdom, South Africa | Germany, Switzerland, Netherlands |

Exactly one market in each archetype survives a change of mind. Everything
below it is contingent on a weighting somebody chose, and should be presented
that way rather than as a ranking.

## What actually moves the ranking

Each row varies one thing and holds everything else fixed, reporting the largest
change it causes in any market's odds of making the shortlist.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| **All published measurement error, combined** | 2.5pp | 12.0pp |
| Vintage — age-adjusted or as-observed | 11.9pp | 3.2pp |
| Normalisation — log or linear | 11.0pp | **57.4pp** |
| Talent pillar — employed stock or education pipeline | **34.4pp** | 22.9pp |

Every modelling choice in this table outweighs all of the measurement error
underneath it. Two of them change *who is on the list*, not merely how sure we
are:

- **Transactional hub** — employed-stock talent gives India, Mexico, **United
  Kingdom**; education-pipeline talent gives India, Mexico, **South Africa**.
- **Judgment centre** — employed-stock talent gives Germany, Switzerland,
  **Singapore**; education-pipeline talent gives Germany, Switzerland, **India**.

Neither construction is wrong. One counts people already doing the work, the
other counts the pipeline that might one day do it, and they disagree about the
third name on the shortlist. That decision gets made in a single line of code,
usually without discussion, and it matters more than every confidence interval
in the panel put together.

The governance result is worth stating on its own. Six of the nine adjacent
pairs in the governance ranking are separated by 0.7 to 3.4 points, while the
World Bank publishes standard errors of roughly 3.2 to 3.9 points on the
underlying dimensions. Singapore, Switzerland, the Netherlands and Germany are
not distinguishable from each other on governance at all, and the publisher says
so in the same file that carries the scores. Ranking them 1-2-3-4 on a scorecard
invents a precision the source explicitly disclaims.

## Poland: the fix that did not fix it

An earlier version of this study had four pillars, found that Poland — the
canonical European GBS location — was never shortlisted, and concluded that the
panel was blind to what Poland is actually bought for: overlapping working hours
with European headquarters.

So overlap was added as a pillar, and Poland scores the maximum on it.

Poland is still never shortlisted: 0.6% of transactional weightings, 4.9% of
judgment ones.

The reason is visible once the pillar exists. Poland ties four other markets on
that maximum overlap score, so the advantage separates it from nobody. And it
holds the worst durability score in the panel — measured wage drift of 8.5% a
year against India's 1.7% — so the cost gap it is chosen for is closing faster
than anyone else's. Poland is never best at anything.

That is a better answer than the first one, and it only appeared because the
missing pillar was added rather than written up as a caveat. The original
conclusion, that the model could not see Poland, was wrong.

## The four pillars

| pillar | source | what it is |
|---|---|---|
| Cost | [ILOSTAT](https://ilostat.ilo.org/topics/wages/) `DF_EAR_EMTA_SEX_OCU_CUR_NB` | Blended monthly wage basket across ISCO-08 major groups 2, 3 and 4, USD, carried forward to a common year at each market's own measured wage drift. |
| Talent | ILOSTAT `DF_EMP_2EMP_SEX_OCU_NB` | Employed stock in the same three ISCO groups, blended with the same staffing weights, so cost and talent describe one workforce. |
| Governance | [World Bank WGI](https://www.worldbank.org/en/publication/worldwide-governance-indicators) | Mean of five governance dimensions, each carrying the bounds of its own 90% confidence interval. |
| Capability | [gbs-agentic-shift](https://github.com/morichtereur/gbs-agentic-shift) | What the market demonstrably staffs, from 2,110 classified live GBS postings. |
| Overlap | computed | Hours of the market's working day that fall inside the headquarters' working day. Deterministic — no source to be stale. |
| Durability | ILOSTAT, derived | How slowly the wage gap has been closing, from each market's own measured drift. A cost advantage is not a fact about the future. |

The capability pillar is the one that is not available off the shelf. Every
commercial location index measures talent *supply*. This measures what the
market actually hires for — India runs 72% transactional, Switzerland 80%
judgment — and whether an outsourcing ecosystem already operates there. It
reuses the classifier from the sibling study by import rather than
reimplementation, and a test asserts that both land on the same 2,110 postings,
so the two readouts cannot quietly drift apart.

## Cities: Wrocław yes, Pune no

A site selection does not choose Poland. It chooses Wrocław, or Katowice, or
Warsaw — and on this evidence those are not the same decision at all.

| market | internal spread | cheapest | dearest |
|---|---:|---|---|
| **Poland** | **2.69×** | Katowice 0.67× | Warsaw 1.81× |
| Spain | 1.61× | Seville 0.77× | Madrid 1.23× |
| Netherlands | 1.45× | Eindhoven 0.89× | Amsterdam 1.29× |
| Germany | 1.23× | Düsseldorf 1.04× | Munich 1.29× |

Poland's national figure hides a 2.7-fold internal range. Warsaw costs more per
employee than the Spanish national average and nearly as much as the German one,
while Katowice sits a third below the Polish average. Any ranking that treats
"Poland" as one row is answering a question nobody asked — and the error it
makes is larger than the gap between several of the countries it is comparing.

Germany, by contrast, is nearly flat at 1.23×, so the national figure is a fair
summary there. **Country-level resolution is not uniformly wrong; it is wrong by
a different amount in every country**, which is worse, because it is invisible.

This layer covers four markets. Eurostat's regional accounts do not include
Switzerland, no longer include the UK, and never included India, Mexico, South
Africa or Singapore. **Pune cannot be placed beside Wrocław on comparable public
evidence, and this repository does not pretend otherwise.** Singapore is the one
market where the question does not arise — it is a city already.

Two further limits on the city view: only the *cost* pillar is city-resolved, so
governance, talent, capability and overlap are national figures wearing a city's
name; and because Poland contributes seven candidates against Singapore's one, a
top-three share in city view is partly an artefact of how many cities each
country brings.

## Everything that is resampled

The Monte Carlo varies four things at once, so a market's frequency is its
survival rate across all of them together:

- **Priorities** — 10,000 weightings drawn from a Dirichlet centred on the
  declared weights, so every draw is one somebody could argue for.
- **Governance** — each WGI dimension drawn inside its published 90% interval.
  The dimensions are drawn as perfectly correlated by default: no correlation
  matrix ships with WGI, and drawing them independently averages five errors
  down to a fifth of one and makes the composite look firmer than any dimension
  in it. The conservative end is the default; both are reported.
- **Staffing blend** — the ISCO mix behind the wage basket, applied identically
  to the talent basket so the model cannot buy a transactional wage bill for a
  judgment-heavy labour pool.
- **Capability sampling error** — the postings shares are sample proportions,
  from as few as 88 postings in Switzerland, and are redrawn from the binomial
  that produced them. Resampling everyone else's published error while treating
  this project's own measurement as exact would be the easier and less honest
  choice.

## What this cannot tell you

- **City resolution reaches four of ten markets**, cost only. See above.
- **One imputed number, flagged.** Wage observations are three to six years old
  in Germany, Singapore and South Africa, and are carried forward at each
  market's own measured drift. South Africa's series is too short to measure a
  drift, so it uses the panel median with a wider band — the single place a
  number is filled in rather than measured, and it is marked as such wherever it
  appears.
- **Modelled employment.** The talent pillar is an ILO modelled series, which
  buys complete coverage and a common reference year at the cost of being an
  estimate whose own error is not published per country. It also counts the
  national stock of professionals, technicians and clerks, not the
  finance-specific slice, which ILOSTAT does not resolve.
- **No language, tax or incentive pillar.** Language was measured from the
  postings and deliberately left unweighted: the detector reads English-language
  postings, and it returns 0% German for Switzerland on 94 postings, which is
  plainly a false negative rather than a finding. It is reported as a diagnostic
  and scores nothing. Tax and incentives are not covered at all.
- **The demand-side sample is censored.** The postings snapshot was fetched with
  a per-country page cap, so posting *counts* say nothing about market size.
  Every demand-side metric is a ratio within a country's own sample.
- **Point-in-time.** One snapshot cannot show a trend.
- **Ten markets because ten markets have postings data.** The market set is
  inherited from the sibling study, not chosen as a shortlist.

## Run it

```
make install
make run        # rebuilds data/chart_stability.png and RESULTS.md
make dashboard  # rebuilds dashboard.html
make test
```

Every API pull is cached under `data/cache`, so a rerun is reproducible and does
not depend on three public services being up simultaneously. Full numbers in
[RESULTS.md](RESULTS.md); every declared judgement — weights, archetypes, the
staffing blend, the transform, the talent construction, the vintage handling —
is in [`src/config.py`](src/config.py) in one place, so a reader can disagree
with a specific number instead of with the conclusion.

## A note on the ILOSTAT bulk endpoints

ILOSTAT's documented bulk-download paths (`ilo.org/ilostat-files/WEB_bulk_download/...`)
return 404, and the `rplumber.ilo.org` indicator route returns HTTP 200 with an
empty body. The SDMX service at `sdmx.ilo.org/rest` is the route that works.
Recorded here because the documented path costs an hour before it fails.
