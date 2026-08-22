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
    "br": {"iso3": "BRA", "name": "Brazil", "type": "delivery"},
}

# Markets that belong in a GBS study and cannot be added, with the reason
# tested rather than assumed. Adzuna returns 404 for each of these with valid
# credentials — the endpoints do not exist, so this is not a permissions
# problem — and the Jooble key that covered Central Europe in the sibling study
# now returns 403 on every market.
#
# ILOSTAT, the World Bank and the derived pillars all cover them: five of the
# seven pillars are ready. Only the postings feed is missing, so a working
# Jooble key or an equivalent source would add all six at once.
UNREACHABLE = {
    "ro": "Romania", "cz": "Czechia", "hu": "Hungary",
    "pt": "Portugal", "ph": "Philippines", "my": "Malaysia",
}

# Sources audited for these markets and rejected, so the next person does not
# repeat the search:
#
#   EURES        the EU's own portal covers every one of them, and its terms of
#                use prohibit automated extraction for re-publication. Ruled out
#                on terms, not on technique.
#   Arbeitnow    free and open, but it carries German and UK applicant-tracking
#                feeds only, has no keyword search, and asks not to be paginated
#                heavily.
#   Careerjet    the legacy public API is closed to new callers; v4 requires a
#                commercial partnership.
#   OECD         regional income covers 51 countries and none of the ones that
#                would help here — Brazil, India and Singapore have no regional
#                rows at all and South Africa effectively none.
#
# Jooble covers all six and is free. It is the supported route, and the adapter
# below is written and waiting on a key.
JOOBLE_MARKETS = tuple(UNREACHABLE)

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
# USD is what the buyer pays. PPP says how good the wage is locally, and so how
# hard the market is to retain in. LCU is here to answer a third question the
# other two cannot: when a cost gap closes, is that wages rising or the currency
# moving? Those are different risks with different responses, and USD alone
# cannot tell them apart.
CURRENCIES = ("CUR_TYPE_USD", "CUR_TYPE_PPP", "CUR_TYPE_LCU")

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

# --- GBS centres ----------------------------------------------------------
# An earlier version of this study ranked NUTS-2 regions, which put Munich,
# Hamburg and Amsterdam on a shared-services shortlist. Nobody places a
# delivery centre in Munich. The candidate set is now evidenced rather than
# administrative: a location qualifies as a GBS centre if GBS and
# finance-operations roles are actually advertised there, by more than one
# employer.
#
# Both thresholds matter, and the second does the real work. Posting volume
# alone admits Rheda-Wiedenbrück, where 17 postings come from two employers,
# and Oberkochen, where five come from one. Those are a single company's
# office, not a labour market a programme could hire into. Requiring several
# distinct employers separates a hub from a headquarters.
#
# The thresholds are arbitrary in the way every threshold is. They are stated
# here, and `make centres` prints exactly which locations they exclude.
MIN_CENTRE_POSTINGS = 5
MIN_CENTRE_EMPLOYERS = 4

# Centres inside one country share every pillar except capability, and often
# cost. So the ranking between Pune and Bangalore rests entirely on a share
# estimated from eleven postings against twenty-four — a difference that is
# sampling noise wearing the clothes of a finding.
#
# Each centre's capability share is therefore shrunk toward its country's,
# weighted by how much evidence the centre actually has:
#
#     shrunk = (n * centre + k * national) / (n + k)
#
# k is the number of postings' worth of belief given to the national figure
# before a centre's own data outweighs it. At k = 30 a centre with eleven
# postings is about a quarter its own and three quarters its country's, which
# is the right posture toward eleven postings. The qualitative conclusion —
# that centres within one country are not separable on this evidence — holds
# across any k from roughly 10 to 100; only the arithmetic moves.
CAPABILITY_PRIOR_STRENGTH = 30

# --- Classification error -------------------------------------------------
# The capability share is measured on postings a classifier selected, and that
# classifier is about 55% precise (eval/precision_audit.md). Roughly two in five
# postings behind every share are not GBS or GCC work at all.
#
# That was a caveat for one revision too long. It is now modelled, using two
# quantities that were already measured rather than assumed:
#
#   precision   audits 2 and 3, the two run against approximately the classifier
#               that ships — 21 correct of 40. Drawn from a Beta so the
#               uncertainty in the audit itself propagates, rather than fixing
#               precision at a point estimate taken from forty postings.
#   contaminant the work-family mix of the broad finance-operations sample,
#               per market. A posting that is not service-centre work is most
#               likely ordinary finance work, and that population was measured
#               when this study still ran on it.
#
# An observed share is then a mixture, s_obs = p·s_true + (1−p)·s_contaminant,
# and s_true is recovered per draw. The correction can push a share outside
# [0, 1] when the observed value is extreme and p is drawn low; those draws are
# clipped, which biases slightly toward the middle. Stated because clipping a
# deconvolution is exactly the kind of quiet step this study exists to expose.
AUDIT_CORRECT = 21
AUDIT_TOTAL = 40
MODEL_CLASSIFICATION_ERROR = True

# Location strings arrive in the posting's own language, and one city can
# appear several ways. Mapped to a single English name so the counts combine.
CITY_ALIASES = {
    "warszawa": "Warsaw",
    "kraków": "Kraków",
    "wrocław": "Wrocław",
    "łódź": "Łódź",
    "gdańsk": "Gdańsk",
    "poznań": "Poznań",
    "münchen": "Munich",
    "frankfurt am main": "Frankfurt",
    "köln": "Cologne",
    "zürich": "Zurich",
    "genf": "Geneva",
    "kanton genf": "Geneva",
    "kanton zug": "Zug",
    "ciudad de méxico": "Mexico City",
    "méxico city": "Mexico City",
    "bengaluru": "Bangalore",
}

# Evidenced centres that Eurostat can also resolve on cost. A centre absent
# from this map keeps its country's national cost, and the dashboard says so
# rather than implying a precision it does not have.
CENTRE_NUTS = {
    "Warsaw": "PL91", "Kraków": "PL21", "Wrocław": "PL51", "Łódź": "PL71",
    "Gdańsk": "PL63", "Poznań": "PL41", "Katowice": "PL22",
    "Berlin": "DE30", "Hamburg": "DE60", "Munich": "DE21",
    "Frankfurt": "DE71", "Düsseldorf": "DEA1", "Stuttgart": "DE11",
    "Amsterdam": "NL32", "Eindhoven": "NL41",
    "Madrid": "ES30", "Barcelona": "ES51", "Valencia": "ES52", "Seville": "ES61",
}

# --- Proximity ------------------------------------------------------------
# The Poland result in the first version of this study was that Poland is never
# shortlisted, and the honest reading was that the panel could not see what
# Poland is actually bought for. Overlapping working hours is the largest part
# of that, and it is computable rather than a matter of data availability, so
# there was no excuse for leaving it out.
#
# Standard-time UTC offsets. Daylight saving is deliberately ignored: it moves
# most of these markets together, and modelling it would imply a precision that
# a 9-to-5 working-day abstraction does not have.
# The headquarters is not a candidate — it is the clock the candidates are
# measured against, and it needs nothing from the panel but an offset. Tying
# the selector to the eleven scored markets left out the United States, which
# sponsors a large share of GBS work, along with every other place a CFO
# organisation actually sits.
#
# Cities rather than countries: a headquarters is in a city, and the United
# States alone spans five hours. Grouped by region for the selector.
HQ = "zurich"
HQ_LOCATIONS = {
    "Americas": {
        "san-francisco": ("San Francisco", -8.0),
        "chicago": ("Chicago", -6.0),
        "mexico-city": ("Mexico City", -6.0),
        "new-york": ("New York", -5.0),
        "toronto": ("Toronto", -5.0),
        "sao-paulo": ("São Paulo", -3.0),
    },
    "Europe": {
        "dublin": ("Dublin", 0.0),
        "london": ("London", 0.0),
        "amsterdam": ("Amsterdam", 1.0),
        "frankfurt": ("Frankfurt", 1.0),
        "madrid": ("Madrid", 1.0),
        "paris": ("Paris", 1.0),
        "stockholm": ("Stockholm", 1.0),
        "warsaw": ("Warsaw", 1.0),
        "zurich": ("Zurich", 1.0),
    },
    "Middle East & Africa": {
        "johannesburg": ("Johannesburg", 2.0),
        "dubai": ("Dubai", 4.0),
    },
    "Asia-Pacific": {
        "bengaluru": ("Bengaluru", 5.5),
        "singapore": ("Singapore", 8.0),
        "hong-kong": ("Hong Kong", 8.0),
        "shanghai": ("Shanghai", 8.0),
        "tokyo": ("Tokyo", 9.0),
        "sydney": ("Sydney", 10.0),
    },
}

# Flattened for lookup: key -> (label, offset).
HQ_BY_KEY = {k: v for group in HQ_LOCATIONS.values() for k, v in group.items()}

UTC_OFFSET = {
    "ch": 1.0, "de": 1.0, "nl": 1.0, "es": 1.0, "pl": 1.0,
    "gb": 0.0, "za": 2.0, "in": 5.5, "sg": 8.0, "mx": -6.0,
    # Brasília time. Brazil spans four zones; the GBS corridor from São Paulo
    # through Curitiba and Barueri sits in this one.
    "br": -3.0,
}
WORKING_DAY = (9.0, 17.0)

# --- Durability -----------------------------------------------------------
# A wage gap is not a fact about the future. Poland's measured drift is 8.5% a
# year against India's 1.7%, which is the difference between an arbitrage that
# holds and one that closes while the programme is still running. The drift is
# already measured for the vintage adjustment, so this pillar costs no new data
# — it just stops the model from treating today's gap as permanent.
#
# In USD terms drift mixes real wage growth with currency movement, and this
# pillar does not separate them. It answers "has this market been getting more
# expensive to a dollar buyer", which is the question a sponsor asks.

# --- Archetypes -----------------------------------------------------------
# What kind of centre is being placed changes which market wins, and that is
# the substantive point rather than a configuration detail. A transactional
# hub is bought on cost and scale; a judgment centre is bought on whether the
# market demonstrably staffs judgment work at all.
# --- Employer depth ------------------------------------------------------
# How many distinct employers advertise GBS or GCC work in a market. A market
# where sixty-two employers compete for the profile is a different proposition
# from one with five — faster to hire into, harder to retain in.
#
# This is only a fair comparison if the fetch applies the same effort to every
# market *and* runs deep enough that every market exhausts. The first version
# claimed the cap did not bind and that was wrong: probing the page depth at
# which each market stops returning results showed Switzerland and the
# Netherlands exhausting after one page, while the United Kingdom and India
# were still returning full pages at page 40. A 14-page fetch therefore
# truncated the largest markets and not the smallest, understating depth for
# exactly the markets that have the most of it.
#
# The fetch now runs to 42 pages, past the point where every market runs dry, so
# the counts are supply rather than where the fetch stopped. Two conditions keep
# this pillar honest and both must hold: identical search terms everywhere, and
# a page cap high enough that no market is still producing when it is reached.

ARCHETYPES = {
    "transactional_hub": {
        "label": "Transactional hub",
        "weights": {
            "cost": 0.30, "talent": 0.18, "risk": 0.09,
            "capability": 0.13, "timezone": 0.09, "durability": 0.09,
            "depth": 0.12,
        },
        # Which end of the postings mix counts as fit for this archetype.
        "capability_metric": "transactional_share",
    },
    "judgment_centre": {
        "label": "Judgment centre of excellence",
        "weights": {
            "cost": 0.13, "talent": 0.17, "risk": 0.17,
            "capability": 0.22, "timezone": 0.13, "durability": 0.04,
            "depth": 0.14,
        },
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

# "Robust" is a claim about evidence, not just about arithmetic. Mumbai reached
# 90% of weightings on six postings from four employers, edging Pune — which
# has twenty — by two points of a shrunk capability share. The frequency was
# computed correctly and the label was still wrong: no amount of resampling
# turns six postings into a durable finding.
#
# A candidate whose own sample is below this floor is therefore capped at
# "contingent" however often it survives. Country rows, which rest on the whole
# market's sample, are unaffected.
EVIDENCE_FLOOR = 10
