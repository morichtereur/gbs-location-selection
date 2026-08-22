# Results

Ten markets scored on six pillars, 10,000 draws per archetype. Panel assembled 2026; capability from the GBS/GCC posting sample. Every figure below is reproduced by `make run`.

## The panel

Cost is the blended ISCO-08 2/3/4 wage basket in USD, aged to a common year at each market's own measured drift. Talent is the employed stock in the same three groups. Governance is the mean of five World Bank dimensions. Capability and its sample size come from postings classified as GBS or GCC work — note how small some of them are.

| market | cost USD/mo | obs. year | lag | wage drift | employed stock | governance | transactional | postings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| India | 336 | 2025 | 1y | 1.7% | 20,051,084 | 52.6 | 63.1% | 103 |
| South Africa | 711 | 2020 | 6y | 3.1% * | 1,587,992 | 51.5 | 54.5% | 22 |
| Mexico | 743 | 2025 | 1y | 3.8% | 5,044,526 | 43.7 | 91.3% | 23 |
| Brazil | 824 | 2025 | 1y | 1.5% | 10,288,351 | 48.6 | 52.9% | 17 |
| Poland | 2,404 | 2025 | 1y | 8.5% | 2,871,214 | 67.1 | 57.1% | 98 |
| Singapore | 3,503 | 2021 | 5y | 1.4% | 678,114 | 88.1 | 55.6% | 18 |
| United Kingdom | 3,567 | 2025 | 1y | 3.6% | 5,469,080 | 76.1 | 68.5% | 54 |
| Spain | 4,069 | 2025 | 1y | 4.6% | 3,056,248 | 67.8 | 90.0% | 10 |
| Germany | 5,048 | 2022 | 4y | 3.0% | 8,221,650 | 79.3 | 52.6% | 38 |
| Netherlands | 6,326 | 2025 | 1y | 3.2% | 1,983,881 | 82.7 | 33.3% | 9 |
| Switzerland | 8,109 | 2025 | 1y | 2.2% | 922,517 | 85.7 | 60.0% | 5 |

`*` drift not measurable from the available series; the panel median is used, and it is the only imputed number in the panel.

## Transactional hub

Declared weights: cost 0.30, talent 0.18, risk 0.09, capability 0.13, timezone 0.09, durability 0.09, depth 0.12.
Baseline top 3: **India, Brazil, Mexico**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 99.6% | 1.0 | 1–8 | robust |  |
| Brazil | 68.0% | 3.2 | 1–11 | contingent | cost weight 0.32 vs 0.27 when out |
| United Kingdom | 46.4% | 3.7 | 1–9 | contingent | depth weight 0.14 vs 0.11 when out |
| Mexico | 38.5% | 4.5 | 1–11 | contingent | cost weight 0.34 vs 0.28 when out |
| Germany | 21.6% | 5.0 | 1–11 | contingent | risk weight 0.12 vs 0.08 when out |
| South Africa | 21.1% | 5.1 | 1–11 | contingent | cost weight 0.34 vs 0.29 when out |
| Poland | 4.1% | 6.5 | 1–11 | never |  |
| Spain | 0.5% | 7.5 | 1–11 | never |  |
| Singapore | 0.1% | 9.5 | 3–11 | never |  |
| Switzerland | 0.1% | 9.9 | 2–11 | never |  |
| Netherlands | 0.0% | 10.1 | 3–11 | never |  |

## Judgment centre of excellence

Declared weights: cost 0.13, talent 0.17, risk 0.17, capability 0.22, timezone 0.13, durability 0.04, depth 0.14.
Baseline top 3: **Germany, India, Netherlands**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 92.5% | 1.6 | 1–9 | robust |  |
| Germany | 66.8% | 3.1 | 1–9 | contingent | talent weight 0.18 vs 0.16 when out |
| Netherlands | 57.7% | 3.4 | 1–11 | contingent | capability weight 0.24 vs 0.19 when out |
| United Kingdom | 31.1% | 4.2 | 1–9 | contingent | depth weight 0.16 vs 0.13 when out |
| Poland | 26.7% | 4.5 | 1–11 | contingent | depth weight 0.17 vs 0.13 when out |
| Brazil | 17.1% | 5.7 | 1–11 | contingent | cost weight 0.16 vs 0.12 when out |
| South Africa | 4.3% | 6.9 | 1–11 | never |  |
| Switzerland | 3.1% | 8.5 | 1–11 | never |  |
| Singapore | 0.8% | 8.8 | 1–11 | never |  |
| Spain | 0.0% | 8.9 | 4–11 | never |  |
| Mexico | 0.0% | 10.4 | 6–11 | never |  |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | Mexico 19.1pp | Germany 32.1pp |
| Vintage: age-adjusted or as-observed | South Africa 6.2pp | Germany 2.8pp |
| Normalisation: log or linear | Mexico 22.8pp | Poland 22.3pp |
| Talent pillar: employed stock or education pipeline | South Africa 18.8pp | Germany 20.9pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, Brazil, Mexico; education-pipeline talent gives India, Brazil, Mexico.
- **Judgment centre of excellence** — employed-stock talent gives Germany, India, Netherlands; education-pipeline talent gives India, Netherlands, Germany.
