# Results

Ten markets, 10,000 draws per archetype, panel assembled 2026.

## The panel

| market | wage basket USD/mo | obs. year | lag | talent scale proxy | WGI composite | transactional share | postings |
|---|---:|---:|---:|---:|---:|---:|---:|
| India | 336 | 2025 | 1y | 20,051,084 | 52.6 | 61.2% | 103 |
| South Africa | 711 | 2020 | 6y | 1,587,992 | 51.5 | 53.8% | 26 |
| Mexico | 743 | 2025 | 1y | 5,044,526 | 43.7 | 85.7% | 14 |
| Poland | 2,404 | 2025 | 1y | 2,871,214 | 67.1 | 55.7% | 97 |
| Singapore | 3,503 | 2021 | 5y | 678,114 | 88.1 | 52.0% | 25 |
| United Kingdom | 3,567 | 2025 | 1y | 5,469,080 | 76.1 | 69.8% | 43 |
| Spain | 4,069 | 2025 | 1y | 3,056,248 | 67.8 | 72.7% | 11 |
| Germany | 5,048 | 2022 | 4y | 8,221,650 | 79.3 | 55.3% | 38 |
| Netherlands | 6,326 | 2025 | 1y | 1,983,881 | 82.7 | 33.3% | 9 |
| Switzerland | 8,109 | 2025 | 1y | 922,517 | 85.7 | 60.0% | 5 |

## Transactional hub

Declared weights: cost 0.35, talent 0.20, risk 0.10, capability 0.15, timezone 0.10, durability 0.10.
Baseline top 3: **India, Mexico, United Kingdom**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| India | 100.0% | 1.0 | 1–6 | robust |  |
| Mexico | 76.7% | 2.9 | 1–10 | contingent | cost weight 0.37 vs 0.29 when out |
| South Africa | 49.4% | 4.0 | 1–10 | contingent | cost weight 0.39 vs 0.31 when out |
| United Kingdom | 45.0% | 3.6 | 1–8 | contingent | risk weight 0.12 vs 0.09 when out |
| Germany | 21.3% | 4.7 | 1–10 | contingent | talent weight 0.23 vs 0.19 when out |
| Spain | 6.2% | 5.6 | 1–10 | never |  |
| Switzerland | 1.1% | 8.3 | 1–10 | never |  |
| Netherlands | 0.2% | 8.7 | 2–10 | never |  |
| Singapore | 0.1% | 9.0 | 2–10 | never |  |
| Poland | 0.1% | 7.2 | 3–10 | never |  |

## Judgment centre of excellence

Declared weights: cost 0.15, talent 0.20, risk 0.20, capability 0.25, timezone 0.15, durability 0.05.
Baseline top 3: **Netherlands, Germany, India**.

| market | top-3 frequency | mean rank | rank range | verdict | what it takes |
|---|---:|---:|---:|---|---|
| Germany | 93.4% | 2.0 | 1–8 | robust |  |
| Netherlands | 85.6% | 2.2 | 1–9 | contingent | risk weight 0.20 vs 0.18 when out |
| India | 63.1% | 3.2 | 1–9 | contingent | talent weight 0.22 vs 0.17 when out |
| Switzerland | 22.2% | 5.6 | 1–10 | contingent | risk weight 0.22 vs 0.19 when out |
| United Kingdom | 17.1% | 4.7 | 1–9 | contingent | risk weight 0.22 vs 0.19 when out |
| Poland | 8.4% | 5.3 | 1–10 | never |  |
| South Africa | 7.7% | 6.2 | 1–10 | never |  |
| Singapore | 2.3% | 7.7 | 1–10 | never |  |
| Spain | 0.0% | 8.3 | 3–10 | never |  |
| Mexico | 0.0% | 9.9 | 3–10 | never |  |

## What actually moves the ranking

Largest change in any market's top-3 frequency when one thing is varied
and everything else is held fixed. The first row is every published
measurement error in the panel, taken together. The rest are choices a
modeller makes silently.

| varied | transactional hub | judgment centre |
|---|---:|---:|
| All published measurement error | United Kingdom 12.2pp | Netherlands 13.4pp |
| Vintage: age-adjusted or as-observed | United Kingdom 9.0pp | South Africa 1.2pp |
| Normalisation: log or linear | Mexico 15.9pp | Germany 8.4pp |
| Talent pillar: employed stock or education pipeline | South Africa 28.4pp | Germany 17.1pp |

Two of those choices change the membership of the shortlist, not just the
confidence in it:

- **Transactional hub** — employed-stock talent gives India, Mexico, United Kingdom; education-pipeline talent gives India, Mexico, South Africa.
- **Judgment centre of excellence** — employed-stock talent gives Netherlands, Germany, India; education-pipeline talent gives Netherlands, Germany, India.
