# Results

Ten markets, 10,000 draws per archetype, panel assembled 2026.

## The panel

| market | wage basket USD/mo | obs. year | lag | talent scale proxy | WGI composite | transactional share | postings |
|---|---:|---:|---:|---:|---:|---:|---:|
| India | 336 | 2025 | 1y | 20,051,084 | 52.6 | 72.4% | 272 |
| South Africa | 711 | 2020 | 6y | 1,587,992 | 51.5 | 36.4% | 220 |
| Mexico | 743 | 2025 | 1y | 5,044,526 | 43.7 | 43.5% | 193 |
| Poland | 2,404 | 2025 | 1y | 2,871,214 | 67.1 | 42.9% | 261 |
| Singapore | 3,503 | 2021 | 5y | 678,114 | 88.1 | 34.0% | 215 |
| United Kingdom | 3,567 | 2025 | 1y | 5,469,080 | 76.1 | 52.8% | 271 |
| Spain | 4,069 | 2025 | 1y | 3,056,248 | 67.8 | 38.8% | 196 |
| Germany | 5,048 | 2022 | 4y | 8,221,650 | 79.3 | 31.7% | 240 |
| Netherlands | 6,326 | 2025 | 1y | 1,983,881 | 82.7 | 40.9% | 154 |
| Switzerland | 8,109 | 2025 | 1y | 922,517 | 85.7 | 19.3% | 88 |

## Transactional hub

Declared weights: cost 0.35, talent 0.20, risk 0.10, capability 0.15, timezone 0.10, durability 0.10.
Baseline top 3: **India, United Kingdom, South Africa**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 100.0% | 1.0 | 1–5 | robust |  |
| United Kingdom | 68.4% | 2.9 | 2–5 | contingent | risk weight 0.11 vs 0.08 when out |
| South Africa | 58.3% | 3.4 | 2–10 | contingent | cost weight 0.38 vs 0.30 when out |
| Mexico | 51.5% | 3.9 | 2–10 | contingent | cost weight 0.39 vs 0.31 when out |
| Germany | 20.4% | 4.6 | 1–9 | contingent | talent weight 0.23 vs 0.19 when out |
| Poland | 0.6% | 6.5 | 2–10 | never |  |
| Netherlands | 0.6% | 7.2 | 3–9 | never |  |
| Singapore | 0.1% | 9.0 | 2–10 | never |  |
| Spain | 0.1% | 6.8 | 3–10 | never |  |
| Switzerland | 0.0% | 9.6 | 4–10 | never |  |

## Judgment centre of excellence

Declared weights: cost 0.15, talent 0.20, risk 0.20, capability 0.25, timezone 0.15, durability 0.05.
Baseline top 3: **Germany, Switzerland, Netherlands**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| Germany | 99.8% | 1.3 | 1–5 | robust |  |
| Switzerland | 87.8% | 2.2 | 1–9 | contingent | capability weight 0.26 vs 0.19 when out |
| Netherlands | 49.6% | 4.1 | 1–10 | contingent | risk weight 0.22 vs 0.18 when out |
| United Kingdom | 20.5% | 4.8 | 2–10 | contingent | talent weight 0.25 vs 0.19 when out |
| India | 14.7% | 7.0 | 1–10 | contingent | talent weight 0.26 vs 0.19 when out |
| South Africa | 14.2% | 6.1 | 1–10 | contingent | cost weight 0.21 vs 0.14 when out |
| Spain | 6.9% | 5.6 | 2–10 | never |  |
| Poland | 4.9% | 6.1 | 2–10 | never |  |
| Singapore | 1.4% | 8.3 | 1–10 | never |  |
| Mexico | 0.2% | 9.5 | 2–10 | never |  |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | South Africa 1.1pp | Netherlands 15.4pp |
| Vintage: age-adjusted or as-observed | South Africa 10.4pp | South Africa 3.7pp |
| Normalisation: log or linear | Mexico 28.1pp | Netherlands 12.7pp |
| Talent pillar: employed stock or education pipeline | South Africa 30.2pp | South Africa 22.5pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, United Kingdom, South Africa; education-pipeline talent gives India, South Africa, Mexico.
- **Judgment centre of excellence** — employed-stock talent gives Germany, Switzerland, Netherlands; education-pipeline talent gives Germany, Switzerland, Netherlands.
