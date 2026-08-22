# Results

Ten markets scored on six pillars, 10,000 draws per archetype. Panel assembled 2026; capability from the GBS/GCC posting sample. Every figure below is reproduced by `make run`.

## The panel

Cost is the blended ISCO-08 2/3/4 wage basket in USD, aged to a common year at each market's own measured drift. Talent is the employed stock in the same three groups. Governance is the mean of five World Bank dimensions. Capability and its sample size come from postings classified as GBS or GCC work — note how small some of them are.

| market | cost USD/mo | obs. year | lag | wage drift | employed stock | governance | transactional | postings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| India | 336 | 2025 | 1y | 1.7% | 20,051,084 | 52.6 | 60.6% | 104 |
| South Africa | 711 | 2020 | 6y | 3.1% * | 1,587,992 | 51.5 | 53.8% | 26 |
| Mexico | 743 | 2025 | 1y | 3.8% | 5,044,526 | 43.7 | 91.7% | 24 |
| Brazil | 824 | 2025 | 1y | 1.5% | 10,288,351 | 48.6 | 52.6% | 19 |
| Poland | 2,404 | 2025 | 1y | 8.5% | 2,871,214 | 67.1 | 57.0% | 107 |
| Singapore | 3,503 | 2021 | 5y | 1.4% | 678,114 | 88.1 | 52.0% | 25 |
| United Kingdom | 3,567 | 2025 | 1y | 3.6% | 5,469,080 | 76.1 | 69.8% | 43 |
| Spain | 4,069 | 2025 | 1y | 4.6% | 3,056,248 | 67.8 | 75.0% | 12 |
| Germany | 5,048 | 2022 | 4y | 3.0% | 8,221,650 | 79.3 | 53.8% | 39 |
| Netherlands | 6,326 | 2025 | 1y | 3.2% | 1,983,881 | 82.7 | 33.3% | 9 |
| Switzerland | 8,109 | 2025 | 1y | 2.2% | 922,517 | 85.7 | 60.0% | 5 |

`*` drift not measurable from the available series; the panel median is used, and it is the only imputed number in the panel.

## Transactional hub

Declared weights: cost 0.30, talent 0.18, risk 0.09, capability 0.13, timezone 0.09, durability 0.09, depth 0.12.
Baseline top 3: **India, Brazil, Mexico**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 100.0% | 1.0 | 1–4 | robust |  |
| Brazil | 74.7% | 2.9 | 2–11 | contingent | cost weight 0.31 vs 0.26 when out |
| Mexico | 54.0% | 4.0 | 1–11 | contingent | cost weight 0.32 vs 0.27 when out |
| United Kingdom | 36.7% | 3.8 | 1–8 | contingent | risk weight 0.11 vs 0.08 when out |
| Germany | 15.4% | 5.3 | 1–10 | contingent | risk weight 0.13 vs 0.08 when out |
| South Africa | 14.8% | 5.2 | 2–11 | contingent | cost weight 0.34 vs 0.29 when out |
| Poland | 3.8% | 6.5 | 2–11 | never |  |
| Spain | 0.5% | 7.6 | 2–11 | never |  |
| Switzerland | 0.1% | 10.2 | 2–11 | never |  |
| Netherlands | 0.0% | 9.8 | 3–11 | never |  |
| Singapore | 0.0% | 9.6 | 2–11 | never |  |

## Judgment centre of excellence

Declared weights: cost 0.13, talent 0.17, risk 0.17, capability 0.22, timezone 0.13, durability 0.04, depth 0.14.
Baseline top 3: **India, Germany, Netherlands**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| Germany | 92.2% | 2.0 | 1–9 | robust |  |
| India | 83.2% | 2.1 | 1–10 | contingent | talent weight 0.18 vs 0.13 when out |
| Netherlands | 42.8% | 4.1 | 1–10 | contingent | capability weight 0.24 vs 0.20 when out |
| Poland | 37.5% | 4.1 | 1–10 | contingent | depth weight 0.17 vs 0.12 when out |
| United Kingdom | 20.6% | 4.6 | 1–9 | contingent | risk weight 0.20 vs 0.16 when out |
| Brazil | 16.0% | 5.7 | 1–10 | contingent | cost weight 0.16 vs 0.12 when out |
| Switzerland | 3.8% | 8.1 | 1–11 | never |  |
| South Africa | 3.0% | 6.8 | 1–10 | never |  |
| Singapore | 0.9% | 8.3 | 1–11 | never |  |
| Spain | 0.0% | 9.5 | 6–11 | never |  |
| Mexico | 0.0% | 10.7 | 7–11 | never |  |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | South Africa 7.4pp | Netherlands 11.6pp |
| Vintage: age-adjusted or as-observed | South Africa 5.7pp | Brazil 1.1pp |
| Normalisation: log or linear | Poland 24.2pp | Poland 23.4pp |
| Talent pillar: employed stock or education pipeline | South Africa 15.8pp | Germany 16.0pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, Brazil, Mexico; education-pipeline talent gives India, Brazil, Mexico.
- **Judgment centre of excellence** — employed-stock talent gives India, Germany, Netherlands; education-pipeline talent gives India, Germany, Netherlands.
