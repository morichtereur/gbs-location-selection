# Results

Ten markets scored on six pillars, 10,000 draws per archetype. Panel assembled 2026; capability from the GBS/GCC posting sample. Every figure below is reproduced by `make run`.

## The panel

Cost is the blended ISCO-08 2/3/4 wage basket in USD, aged to a common year at each market's own measured drift. Talent is the employed stock in the same three groups. Governance is the mean of five World Bank dimensions. Capability and its sample size come from postings classified as GBS or GCC work — note how small some of them are.

| market | cost USD/mo | obs. year | lag | wage drift | employed stock | governance | transactional | postings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| India | 336 | 2025 | 1y | 1.7% | 20,051,084 | 52.6 | 64.0% | 100 |
| South Africa | 711 | 2020 | 6y | 3.1% * | 1,587,992 | 51.5 | 55.6% | 18 |
| Mexico | 743 | 2025 | 1y | 3.8% | 5,044,526 | 43.7 | 91.3% | 23 |
| Brazil | 824 | 2025 | 1y | 1.5% | 10,288,351 | 48.6 | 52.9% | 17 |
| Poland | 2,404 | 2025 | 1y | 8.5% | 2,871,214 | 67.1 | 57.3% | 96 |
| Singapore | 3,503 | 2021 | 5y | 1.4% | 678,114 | 88.1 | 62.5% | 16 |
| United Kingdom | 3,567 | 2025 | 1y | 3.6% | 5,469,080 | 76.1 | 69.8% | 53 |
| Spain | 4,069 | 2025 | 1y | 4.6% | 3,056,248 | 67.8 | 88.9% | 9 |
| Germany | 5,048 | 2022 | 4y | 3.0% | 8,221,650 | 79.3 | 48.5% | 33 |
| Netherlands | 6,326 | 2025 | 1y | 3.2% | 1,983,881 | 82.7 | 37.5% | 8 |
| Switzerland | 8,109 | 2025 | 1y | 2.2% | 922,517 | 85.7 | 60.0% | 5 |

`*` drift not measurable from the available series; the panel median is used, and it is the only imputed number in the panel.

## Transactional hub

Declared weights: cost 0.30, talent 0.18, risk 0.09, capability 0.13, timezone 0.09, durability 0.09, depth 0.12.
Baseline top 3: **India, Brazil, Mexico**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 99.8% | 1.0 | 1–7 | robust |  |
| Brazil | 69.8% | 3.2 | 1–11 | contingent | cost weight 0.31 vs 0.27 when out |
| United Kingdom | 50.9% | 3.5 | 1–10 | contingent | risk weight 0.10 vs 0.07 when out |
| Mexico | 46.2% | 4.2 | 1–11 | contingent | cost weight 0.33 vs 0.28 when out |
| South Africa | 16.6% | 5.3 | 1–11 | contingent | cost weight 0.34 vs 0.29 when out |
| Germany | 10.1% | 5.8 | 1–11 | contingent | risk weight 0.13 vs 0.09 when out |
| Poland | 5.2% | 6.4 | 2–11 | never |  |
| Spain | 1.0% | 7.2 | 1–11 | never |  |
| Singapore | 0.2% | 9.4 | 2–11 | never |  |
| Switzerland | 0.1% | 10.0 | 2–11 | never |  |
| Netherlands | 0.1% | 10.0 | 3–11 | never |  |

## Judgment centre

Declared weights: cost 0.13, talent 0.17, risk 0.17, capability 0.22, timezone 0.13, durability 0.04, depth 0.14.
Baseline top 3: **Germany, India, Netherlands**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 90.2% | 1.7 | 1–8 | robust |  |
| Germany | 78.9% | 2.6 | 1–9 | contingent | talent weight 0.18 vs 0.15 when out |
| Netherlands | 45.0% | 4.0 | 1–10 | contingent | capability weight 0.24 vs 0.20 when out |
| Poland | 31.3% | 4.2 | 1–10 | contingent | depth weight 0.17 vs 0.13 when out |
| United Kingdom | 29.8% | 4.3 | 1–9 | contingent | depth weight 0.16 vs 0.13 when out |
| Brazil | 17.7% | 5.5 | 1–10 | contingent | cost weight 0.15 vs 0.12 when out |
| Switzerland | 3.4% | 8.3 | 1–11 | never |  |
| South Africa | 3.3% | 7.0 | 1–11 | never |  |
| Singapore | 0.4% | 9.3 | 1–11 | never |  |
| Spain | 0.0% | 8.8 | 4–11 | never |  |
| Mexico | 0.0% | 10.3 | 6–11 | never |  |

## Arbitrage work against value work

Across 378 classified GBS and GCC postings: **62% transactional**, **37% judgment**, **0.3% agent-ops**. The base is still processing work, and AI-adjacent roles barely register in hiring. One snapshot cannot show a trend; it fixes the starting point.

| market | transactional | judgment | agent-ops | n |
|---|---:|---:|---:|---:|
| Switzerland | 60% | 40% | 0% | 5 |
| Germany | 48% | 52% | 0% | 33 |
| Netherlands | 38% | 62% | 0% | 8 |
| United Kingdom | 70% | 30% | 0% | 53 |
| Spain | 89% | 11% | 0% | 9 |
| Singapore | 62% | 38% | 0% | 16 |
| Poland | 57% | 43% | 0% | 96 |
| Mexico | 91% | 4% | 4% | 23 |
| South Africa | 56% | 44% | 0% | 18 |
| India | 64% | 36% | 0% | 100 |
| Brazil | 53% | 47% | 0% | 17 |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | Mexico 14.8pp | Germany 20.0pp |
| Vintage: age-adjusted or as-observed | South Africa 6.1pp | Germany 1.4pp |
| Normalisation: log or linear | Mexico 26.1pp | Poland 21.7pp |
| Talent pillar: employed stock or education pipeline | United Kingdom 16.3pp | Germany 18.5pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, Brazil, Mexico; education-pipeline talent gives India, Brazil, Mexico.
- **Judgment centre** — employed-stock talent gives Germany, India, Netherlands; education-pipeline talent gives India, Germany, Netherlands.
