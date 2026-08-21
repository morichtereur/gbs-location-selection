# gbs-location-selection

**A shared-services location shortlist, and a measurement of how much of it was ever really in play.**

A location study arrives as three cities and a weighted scorecard. The weights
were set in a workshop, and the weights are what chose the three cities. The
study is then presented as measurement.

This scores ten markets on four pillars from public data, and then does the
part that is usually skipped: re-scores them ten thousand times under every
weighting somebody in that room could have defended, and reports how often each
market survives.

![Rank stability](data/chart_stability.png)

## Key finding

**The same data answers one archetype's question and cannot answer the other's.**

| | transactional hub | judgment centre of excellence |
|---|---|---|
| markets robust in the top 3 (≥90% of weightings) | **2** — India 100.0%, Mexico 98.8% | **none** |
| markets never shortlisted (<10%) | 6 | 3 |
| widest rank range | 2–10 | 1–10, for seven of ten markets |

For a transactional hub, the shortlist is not a matter of opinion. India holds
first place in 10,000 out of 10,000 weightings, and six markets reach the top
three in under 1% of them — Switzerland and Spain in none at all, the other four
in between 7 and 32 draws out of 10,000.

For a judgment centre, nothing is robust. Germany tops the baseline and holds a
top-three place in 85% of weightings; seven markets have a rank range spanning
first to last. The panel does not decide this question. Whoever sets the
weights does, and they should be told that rather than handed a ranking.

## What actually moves the ranking

Three things were varied independently to find out which one the answer is
really hostage to.

| source of uncertainty | largest effect on a market's top-3 frequency |
|---|---|
| Governance scores resampled inside their published 90% interval | 0.5pp (transactional) · 6.4pp (judgment) |
| Priorities — 10,000 draws around the declared weights | India 100% vs Poland 0.1%: decisive for the transactional hub, indecisive for the judgment centre |
| **Normalisation transform — log vs linear** | **Singapore 29.5% → 98.2%, and the judgment top three changes membership** |

The ranking is barely sensitive to the quality of the data and highly sensitive
to a modelling choice nobody argues about. Whether the talent pool is scaled
logarithmically or linearly is a decision made silently, in one line, usually by
whoever built the spreadsheet — and it swings the judgment-centre shortlist
harder than either the published measurement error or the priorities everybody
does argue about. The baseline here uses log scaling, for a stated reason. The
point is not that log is right; it is that the choice is load-bearing and
belongs in the discussion.

The governance result is worth stating on its own. Six of the nine adjacent
pairs in the governance ranking are separated by 0.7 to 3.4 points, while the
World Bank publishes standard errors of roughly 3.2 to 3.9 points on the
underlying dimensions. Singapore, Switzerland, the Netherlands and Germany are
not distinguishable from each other on governance at all, and the publisher says
so in the same file that carries the scores. Ranking them 1-2-3-4 on a scorecard
invents a precision the source explicitly disclaims.

## Poland is never shortlisted, and that is a result about the model

Poland is the canonical European GBS location. It appears in the top three in
0.1% of transactional weightings and 0.4% of judgment ones — effectively never,
under any weighting, for either archetype. On this panel that is arithmetically
correct: Poland is mid-cost, mid-scale, mid-governance, and nothing on the panel
rewards what it is actually bought for.

What Poland is bought for is nearshore proximity to European headquarters,
overlapping working hours, EU legal and data jurisdiction, and language
coverage. **None of those are pillars here.** So the honest reading is not that
Poland is a bad location. It is that a scorecard built on cost, scale,
governance and capability cannot see the reason Poland wins real mandates — and
neither can any commercial location index built on the same four things.

## The four pillars

| pillar | source | what it is |
|---|---|---|
| Cost | [ILOSTAT](https://ilostat.ilo.org/topics/wages/), `DF_EAR_EMTA_SEX_OCU_CUR_NB` via SDMX | Blended monthly wage basket across ISCO-08 major groups 2, 3 and 4, in USD. PPP pulled alongside it. |
| Talent | [UNESCO UIS](https://databrowser.uis.unesco.org/) | Tertiary enrolment × share of graduates in Business, Administration and Law. A scale proxy, not a graduate count. |
| Risk | [World Bank WGI](https://www.worldbank.org/en/publication/worldwide-governance-indicators) | Mean of five governance dimensions, each carrying the bounds of its own 90% confidence interval. |
| Capability | [gbs-agentic-shift](https://github.com/morichtereur/gbs-agentic-shift) | What the market demonstrably staffs, from 2,110 classified live GBS postings. |

The capability pillar is the one that is not available off the shelf. Every
commercial location index measures talent *supply*. This measures what the
market actually hires for — India runs 72% transactional, Switzerland 80%
judgment — and whether an outsourcing ecosystem already operates there. It
reuses the classifier from the sibling study by import rather than
reimplementation, and a test asserts that both land on the same 2,110 postings,
so the two readouts cannot quietly drift apart.

## What this cannot tell you

- **No city resolution.** ILOSTAT earnings are national. Kraków and Warsaw are
  one number here, and the intra-country spread that a real site selection turns
  on is invisible.
- **Uneven vintages.** Germany's wage observation is 2022, Singapore's 2021,
  South Africa's 2020, against 2025 for the other seven. Each market's own
  measured wage drift is computed and reported, but the baseline does not
  age-adjust — the lag is shown per market instead of papered over.
- **No proximity, timezone, language, tax or incentive pillar.** See Poland.
- **The demand-side sample is censored.** The postings snapshot was fetched with
  a per-country page cap, so posting *counts* say nothing about market size.
  Every demand-side metric is therefore a ratio within a country's own sample.
- **Point-in-time.** One snapshot cannot show a trend.
- **Ten markets because ten markets have postings data.** The market set is
  inherited from the sibling study, not chosen as a shortlist.

## Run it

```
make install
make run     # rebuilds data/chart_stability.png and RESULTS.md
make test
```

Every API pull is cached under `data/cache`, so a rerun is reproducible and does
not depend on three public services being up simultaneously. Full numbers in
[RESULTS.md](RESULTS.md); every declared judgement — weights, archetypes, the
wage blend, the transform — is in [`src/config.py`](src/config.py) in one place,
so a reader can disagree with a specific number instead of with the conclusion.

## A note on the ILOSTAT bulk endpoints

ILOSTAT's documented bulk-download paths (`ilo.org/ilostat-files/WEB_bulk_download/...`)
return 404, and the `rplumber.ilo.org` indicator route returns HTTP 200 with an
empty body. The SDMX service at `sdmx.ilo.org/rest` is the route that works.
Recorded here because the documented path costs an hour before it fails.
