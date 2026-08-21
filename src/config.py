"""Central config: the market set, the indicators, and every declared judgement.

The point of this project is that a location shortlist is decided by choices
that are usually made in a workshop and then presented as measurement. So the
choices live here, in one file, where a reader can disagree with a specific
number instead of with the conclusion.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
DB_PATH = DATA / "panel.duckdb"

# The postings sample that supplies the demand-side pillar. Same snapshot the
# GBS Agentic Shift study ran on — this project does not re-fetch it, so the
# two readouts cannot silently diverge.
POSTINGS_DB = Path(
    ROOT.parent / "gbs-agentic-shift" / "data" / "postings.duckdb"
)

# The ten markets are not a judgement about where centres should go. They are
# the markets the postings snapshot covers, and the demand-side pillar is only
# real for those. Adding an eleventh market means fetching postings for it
# first, otherwise a quarter of its panel is blank.
MARKETS: dict[str, dict[str, str]] = {
    "ch": {"iso3": "CHE", "name": "Switzerland", "type": "retained"},
    "de": {"iso3": "DEU", "name": "Germany", "type": "retained"},
    "nl": {"iso3": "NLD", "name": "Netherlands", "type": "retained"},
    "gb": {"iso3": "GBR", "name": "United Kingdom", "type": "retained"},
    "es": {"iso3": "ESP", "name": "Spain", "type": "mixed"},
    "sg": {"iso3": "SGP", "name": "Singapore", "type": "mixed"},
    "pl": {"iso3": "POL", "name": "Poland", "type": "delivery"},
    "mx": {"iso3": "MEX", "name": "Mexico", "type": "delivery"},
    "za": {"iso3": "ZAF", "name": "South Africa", "type": "delivery"},
    "in": {"iso3": "IND", "name": "India", "type": "delivery"},
}

ISO3_TO_ISO2 = {m["iso3"]: k for k, m in MARKETS.items()}

# --- Cost -----------------------------------------------------------------
# ILOSTAT publishes earnings by ISCO-08 major group and no finer. There is no
# "accountant" line, so a finance centre's wage bill has to be approximated by
# a basket of the three groups its staffing pyramid actually draws on:
#   2 — Professionals (includes accountants, ISCO 2411)
#   3 — Technicians and associate professionals (accounting associates, 3313)
#   4 — Clerical support workers (accounting and bookkeeping clerks, 4311)
# The blend below is a declared staffing assumption, not a measurement, which
# is exactly why it is resampled in the Monte Carlo rather than fixed.
ILO_DATAFLOW = "DF_EAR_EMTA_SEX_OCU_CUR_NB"
# Employed stock by the same ISCO groups. ILO modelled estimates, so coverage
# is complete and the reference year is common across markets.
ILO_EMP_DATAFLOW = "DF_EMP_2EMP_SEX_OCU_NB"
ISCO_GROUPS = ("OCU_ISCO08_2", "OCU_ISCO08_3", "OCU_ISCO08_4")
WAGE_BLEND = {"OCU_ISCO08_2": 0.30, "OCU_ISCO08_3": 0.45, "OCU_ISCO08_4": 0.25}
# How far the blend is allowed to move when resampled: +/- this much on each
# share before renormalising. A centre doing more judgment work is heavier on
# ISCO 2; a transactional one is heavier on ISCO 4.
WAGE_BLEND_JITTER = 0.10

# USD is the cost the buyer actually pays. PPP is pulled alongside it because
# it answers a different question — how good the wage is for the employee, and
# therefore how hard the market will be to retain in. They are not
# interchangeable and the panel keeps both.
CURRENCIES = ("CUR_TYPE_USD", "CUR_TYPE_PPP")

# --- Risk -----------------------------------------------------------------
# WGI publishes a 0-100 score and the bounds of its own 90% confidence
# interval. Most scorecards take the point estimate and drop the interval,
# which is the one piece of information that says how much the number can be
# trusted. This keeps it and samples inside it.
WGI_DIMENSIONS = {
    "PV": "Political Stability",
    "GE": "Government Effectiveness",
    "RL": "Rule of Law",
    "RQ": "Regulatory Quality",
    "CC": "Control of Corruption",
    "VA": "Voice and Accountability",
}
# Voice and Accountability is excluded from the operating-risk composite by
# default: it measures civic freedoms, which matter morally but do not bear
# directly on whether a finance centre can operate. Named here so the choice
# is visible and reversible rather than buried.
WGI_IN_COMPOSITE = ("PV", "GE", "RL", "RQ", "CC")

# --- Talent ---------------------------------------------------------------
# Two constructions of the same pillar, because they answer different
# questions and disagree about the answer.
#
# "employment" is the default: the employed stock in ISCO-08 groups 2, 3 and 4,
# blended with the same staffing weights as the wage basket. It measures people
# already doing this work, in the same occupational terms the cost pillar uses.
#
# "education" is the pipeline instead of the stock — tertiary enrolment times
# the share of graduates in Business, Administration and Law. UIS publishes no
# absolute graduate count, so this is a scale proxy and never a headcount.
#
# The two are not interchangeable and the ratio between the largest and
# smallest market differs by a factor of five between them, so which one is
# used is a declared choice and the alternative is reported.
TALENT_SOURCE = "employment"
UIS_ENROLMENT = "25053"
UIS_BUSINESS_SHARE = "FOSGP.5T8.F400"

# --- Archetypes -----------------------------------------------------------
# What kind of centre is being placed changes which market wins, and that is
# the substantive point rather than a configuration detail. A transactional
# hub is bought on cost and scale; a judgment centre is bought on whether the
# market demonstrably staffs judgment work at all.
ARCHETYPES = {
    "transactional_hub": {
        "label": "Transactional hub",
        "weights": {"cost": 0.45, "talent": 0.25, "risk": 0.15, "capability": 0.15},
        # Which end of the postings mix counts as fit for this archetype.
        "capability_metric": "transactional_share",
    },
    "judgment_centre": {
        "label": "Judgment centre of excellence",
        "weights": {"cost": 0.20, "talent": 0.25, "risk": 0.25, "capability": 0.30},
        "capability_metric": "judgment_share",
    },
}

# --- Vintage --------------------------------------------------------------
# Earnings observations are three to six years old in three of the ten markets.
# Comparing 2020 South African wages against 2025 Swiss ones understates the
# first, so observations are carried forward to the reference year at each
# market's own measured wage drift rather than at an assumed inflation rate.
#
# The adjustment is uncertain, and treated that way: drift is drawn around the
# measured rate rather than applied as a point correction, using the spread of
# measured rates across the panel as the scale. South Africa has too short a
# series to measure a rate at all, so it draws around the panel median with a
# wider spread — the one place a number is filled in rather than measured, and
# it is flagged in the output every time it happens.
AGE_ADJUST = True
DRIFT_SIGMA = 0.021
DRIFT_SIGMA_UNMEASURED_MULTIPLE = 1.5

# --- Monte Carlo ----------------------------------------------------------
DRAWS = 10_000
SEED = 20260821
# Dirichlet concentration on the declared weights. Higher means the draws stay
# near the stated priorities; lower means almost any weighting is entertained.
# 40 keeps a pillar's weight roughly within +/- 10 points of its declared
# value, which is the range a client would actually argue over.
WEIGHT_CONCENTRATION = 40.0
TOP_N = 3
# Frequency thresholds for calling a market's top-3 place robust or contingent.
ROBUST_AT = 0.90
CONTINGENT_AT = 0.10
