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
| India | 100.0% | 1.0 | 1–3 | robust |  |
| Brazil | 71.6% | 3.1 | 1–10 | contingent | cost weight 0.32 vs 0.26 when out |
| Mexico | 51.5% | 4.0 | 1–11 | contingent | cost weight 0.33 vs 0.27 when out |
| United Kingdom | 46.0% | 3.6 | 1–8 | contingent | risk weight 0.11 vs 0.07 when out |
| South Africa | 12.7% | 5.4 | 2–11 | contingent | cost weight 0.35 vs 0.29 when out |
| Germany | 12.3% | 5.5 | 1–10 | contingent | risk weight 0.13 vs 0.08 when out |
| Poland | 3.8% | 6.6 | 2–11 | never |  |
| Spain | 1.9% | 7.1 | 1–11 | never |  |
| Switzerland | 0.1% | 10.2 | 2–11 | never |  |
| Singapore | 0.0% | 9.7 | 3–11 | never |  |
| Netherlands | 0.0% | 9.8 | 4–11 | never |  |

## Judgment centre of excellence

Declared weights: cost 0.13, talent 0.17, risk 0.17, capability 0.22, timezone 0.13, durability 0.04, depth 0.14.
Baseline top 3: **Germany, India, Netherlands**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| Germany | 91.3% | 2.0 | 1–8 | robust |  |
| India | 78.1% | 2.3 | 1–10 | contingent | talent weight 0.18 vs 0.14 when out |
| Netherlands | 40.6% | 4.1 | 1–9 | contingent | capability weight 0.25 vs 0.20 when out |
| United Kingdom | 37.2% | 4.0 | 1–9 | contingent | risk weight 0.19 vs 0.16 when out |
| Poland | 32.5% | 4.2 | 1–10 | contingent | depth weight 0.16 vs 0.13 when out |
| Brazil | 12.9% | 5.9 | 1–10 | contingent | cost weight 0.16 vs 0.12 when out |
| Switzerland | 4.0% | 8.0 | 1–11 | never |  |
| South Africa | 2.9% | 6.9 | 1–10 | never |  |
| Singapore | 0.4% | 8.6 | 1–11 | never |  |
| Spain | 0.0% | 9.4 | 4–11 | never |  |
| Mexico | 0.0% | 10.7 | 7–11 | never |  |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | South Africa 7.1pp | Netherlands 11.6pp |
| Vintage: age-adjusted or as-observed | South Africa 6.0pp | Germany 1.0pp |
| Normalisation: log or linear | Mexico 25.0pp | Poland 24.3pp |
| Talent pillar: employed stock or education pipeline | South Africa 15.6pp | Germany 17.7pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, Brazil, Mexico; education-pipeline talent gives India, Brazil, Mexico.
- **Judgment centre of excellence** — employed-stock talent gives Germany, India, Netherlands; education-pipeline talent gives India, Germany, Netherlands.
