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

# Origins for Exhibit 3 only. These are never scored and never enter the
# ranking: the study needs seven pillars per market and these carry one. They
# exist because "we are moving work out of France" is a question the tool was
# refusing to answer for no better reason than that France is not a candidate.
# ILOSTAT has no earnings in this dataflow for Canada, Australia or Japan.
BASELINE_EXTRA = {
    "us": {"name": "United States", "iso3": "USA"},
    "fr": {"name": "France", "iso3": "FRA"},
    "it": {"name": "Italy", "iso3": "ITA"},
    "ie": {"name": "Ireland", "iso3": "IRL"},
    "be": {"name": "Belgium", "iso3": "BEL"},
    "at": {"name": "Austria", "iso3": "AUT"},
    "se": {"name": "Sweden", "iso3": "SWE"},
    "dk": {"name": "Denmark", "iso3": "DNK"},
    "no": {"name": "Norway", "iso3": "NOR"},
    "fi": {"name": "Finland", "iso3": "FIN"},
}

# The six established locations Adzuna has no endpoint for. Five of the seven
# pillars reach them -- wages, employed stock, governance, overlap and wage
# drift all come from sources that treat every country alike -- and the two
# that do not are exactly the two the postings carry. They are reported here,
# never scored and never ranked: a score on five of seven pillars would look
# like the ranked cities' score and would not mean the same thing.
#
# Nor can a second job board close it. A different feed's employer count is
# not comparable with Adzuna's, so splicing one in would move Manila into the
# ranking on evidence that is not like the rest.
BEYOND_SAMPLE = {
    "ph": {"name": "Philippines", "iso3": "PHL", "city": "Manila", "utc": 8.0},
    "my": {"name": "Malaysia", "iso3": "MYS", "city": "Kuala Lumpur", "utc": 8.0},
    "pt": {"name": "Portugal", "iso3": "PRT", "city": "Lisbon", "utc": 1.0},
    "ro": {"name": "Romania", "iso3": "ROU", "city": "Bucharest", "utc": 2.0},
    "cz": {"name": "Czechia", "iso3": "CZE", "city": "Prague", "utc": 1.0},
    "hu": {"name": "Hungary", "iso3": "HUN", "city": "Budapest", "utc": 1.0},
    # Nearshore and offshore locations a finance shortlist reaches for that
    # Adzuna also has no endpoint for. Same treatment: priced, never ranked.
    "do": {"name": "Dominican Republic", "iso3": "DOM", "city": "Santo Domingo", "utc": -4.0},
    "cr": {"name": "Costa Rica", "iso3": "CRI", "city": "San José", "utc": -6.0},
    "co": {"name": "Colombia", "iso3": "COL", "city": "Bogotá", "utc": -5.0},
    "vn": {"name": "Vietnam", "iso3": "VNM", "city": "Ho Chi Minh City", "utc": 7.0},
    "eg": {"name": "Egypt", "iso3": "EGY", "city": "Cairo", "utc": 2.0},
}

# Tested and not addable at all. ILOSTAT's earnings-by-occupation dataflow
# returns 404 for both, so Wuxi, Dalian and Casablanca have no cost figure on
# the basis every other market here uses. Employment and governance do exist
# for them; a row carrying two pillars and not the decisive one would be worse
# than no row.
UNPRICEABLE = {"China": "Wuxi, Dalian, Chengdu", "Morocco": "Casablanca, Rabat"}

# A market's own series has to be internally coherent before it is shown.
# Professionals out-earn clerical staff everywhere: the ratio runs 1.3x in
# Vietnam and Romania to 2.9x in South Africa across every market here. Egypt
# reports 1.06x -- USD 117 against 110 -- which is not a labour market, it is a
# broken series, and it would have put Cairo on the exhibit at a third of
# India's cost. Checked rather than judged, so the exclusion is reproducible.
MIN_PROFESSIONAL_PREMIUM = 1.15

ISO3_TO_ISO2 = {m["iso3"]: k for k, m in MARKETS.items()}
ISO3_TO_ISO2.update({m["iso3"]: k for k, m in BEYOND_SAMPLE.items()})
ISO3_TO_ISO2.update({m["iso3"]: k for k, m in BASELINE_EXTRA.items()})

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

# Which cost a reader is asking about. USD is what the sponsor pays. PPP is what
# the same wage buys locally, which is a different question with a different
# answer: an Indian wage of $336 is worth $1,478 in local purchasing power, so a
# market that looks cheap to a buyer may not look cheap to the person being
# hired — and that is what a centre has to retain against.
COST_BASIS = "usd"   # "usd" or "ppp"

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
#   precision   audits 4 and 5, the two run against the classifier that ships —
#               24 clearly correct of 40. Drawn from a Beta so the uncertainty in
#               the audit itself propagates rather than being fixed at a point
#               estimate from forty postings. This is a floor: eight of those
#               forty could not be resolved from a truncated advertisement and
#               are counted against precision rather than for it, so the true
#               rate is higher and the model errs toward wider uncertainty.
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
AUDIT_CORRECT = 24
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
# Where the work sits today. Restricted to markets ILOSTAT gives us a wage for,
# because a baseline without a measured wage would make the delta a guess. These
# are the plausible retained locations; the offshore markets are not offered as a
# starting point, though a Singapore baseline can still put Warsaw above it.
BASELINE_MARKETS = ("ch", "nl", "de", "gb", "es", "sg")
BASELINE_DEFAULT = "ch"
# A centre is not staffed one-for-one on day one. Kept visible and adjustable
# rather than buried, because it moves the answer more than the wage gap does.
FTE_DEFAULT = 100

# --- Fully loaded cost ----------------------------------------------------
# ILOSTAT publishes the wage, and a wage is not what a role costs. Three things
# sit between the two, and all three are *assumptions the reader sets* rather
# than anything measured here. They are defaulted, labelled as assumptions on
# the exhibit, and adjustable, on the same basis as WAGE_BLEND: a reader should
# be able to disagree with a number instead of with the conclusion.
#
# What each one is:
#
#   LOADING_FACTOR      employer social charges, holiday and statutory benefit
#                       accrual, as a share of gross wage. Applied to the origin
#                       and the destination alike, because the panel carries no
#                       country-specific employer-charge schedule. That is a
#                       real limitation and the exhibit states it: a uniform
#                       factor scales every gap and therefore cannot reorder
#                       anything, while real charges differ by market — the
#                       Brazilian schedule is far heavier than the Indian one —
#                       and pricing that difference is exactly what this cannot
#                       do. There is no free, comparable, per-country source for
#                       all eleven markets; if one is found this becomes a
#                       measured pillar rather than a slider.
#
#   ATTRITION_UPLIFT    the cost of holding target headcount in a market that
#                       turns over: recruitment, onboarding, and the
#                       productivity gap of a replacement, as a share of the
#                       loaded wage bill. Applied to the destination only. The
#                       retained organisation at the origin is not being stood
#                       up, so it does not carry a ramp cost — that asymmetry is
#                       a declared judgement, and it is the one input here that
#                       can move the order of cities, because it scales with a
#                       city's own wage.
#
#   HORIZON_YEARS       how far forward to carry both sides, each at its own
#                       measured wage drift. This one is not an invented rate:
#                       the drift is already measured per market for the vintage
#                       adjustment, and it is what the durability pillar scores.
#                       Default 0 — today — because a non-zero default would
#                       apply a compounding projection the reader never asked
#                       for. Pushing it out is how the durability finding stops
#                       being abstract: Poland's gap closes and India's does
#                       not.
#
# 0.25 and 0.15 are round mid-range placeholders, not findings. Nothing in this
# repository measures either, and the page says so where they are set.
LOADING_FACTOR_DEFAULT = 0.25
ATTRITION_UPLIFT_DEFAULT = 0.15
HORIZON_YEARS_DEFAULT = 0
# Guard rails for the inputs, so a typo cannot produce a negative wage bill or
# a projection past the point where compounding a measured rate means anything.
LOADING_FACTOR_MAX = 1.0
ATTRITION_UPLIFT_MAX = 1.0
HORIZON_YEARS_MAX = 10

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
        "blurb": "High-volume processing: accounts payable and receivable, payroll, "
                 "the ledger. Bought on cost and the size of the labour pool.",
        "why": "Cost carries the most weight because processing work is bought on "
               "unit cost, and scale next because these centres hire in hundreds.",
        "weights": {
            "cost": 0.30, "talent": 0.18, "risk": 0.09,
            "capability": 0.13, "timezone": 0.09, "durability": 0.09,
            "depth": 0.12,
        },
        # Which end of the postings mix counts as fit for this archetype.
        "capability_metric": "transactional_share",
    },
    "judgment_centre": {
        # The pair has to be parallel and has to name the work. "Centre of
        # excellence" names an organisational form instead, and is ambiguous
        # besides — a procure-to-pay CoE is transactional. "Judgment" carries
        # the distinction the whole study rests on, which "excellence" does not.
        #
        # Naming the pair "GBS versus CoE" was also considered and rejected:
        # GBS is the umbrella containing both, so that would assert a centre of
        # excellence is not part of a GBS.
        "label": "Judgment centre",
        "blurb": "Judgment work: analysis, controlling, business partnering, reporting. "
                 "Bought on whether a market already does this work and can keep doing it.",
        "why": "Capability leads because this work needs a market that already "
               "staffs it, with governance and overlap close behind; cost matters "
               "least, because these centres are small and hired for scarce skills.",
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

# --- Separability ---------------------------------------------------------
# A ranked list of thirteen cities asserts twelve orderings, and the draws do
# not support all of them: seven of the fifty-five pairs come out closer than
# 65/35, which is a coin toss wearing a rank number. Printing 2nd and 3rd for a
# pair that swaps in half the draws undoes every other honesty mechanism here.
#
# Cities are therefore grouped into bands. Two neighbours join the same band
# when neither outranks the other in at least this share of draws — the tool
# says "these are not distinguishable" instead of inventing an order.
SEPARABLE_AT = 0.65


# --- Publication ----------------------------------------------------------
# Where the tool is served, and where a link-preview crawler can fetch its card
# image. The dashboard is a single self-contained file vendored into the
# personal site, so the image cannot ride along inside it: a data: URI is
# rejected by every crawler that matters, and og:image has to be an absolute
# https URL. The raw URL of this repository is used because it is the repository
# that owns the image and it works with no cross-repo step. Point it at
# `PUBLISHED_URL + "og.png"` once the site's sync copies the file alongside
# index.html.
PUBLISHED_URL = "https://morichtereur.github.io/location-dashboard/"
OG_IMAGE_URL = (
    "https://raw.githubusercontent.com/morichtereur/"
    "gbs-location-selection/main/data/og.png"
)
