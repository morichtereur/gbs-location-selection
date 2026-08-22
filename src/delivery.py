"""Which postings are genuinely GBS or GCC finance work, and which model they are.

Visible phrase lists rather than a model, for the same reason the sibling
study's taxonomy is: a reader can check a specific entry and disagree with it,
instead of disagreeing with a black box.

Adzuna truncates every description at 500 characters, so all three gates read a
title plus an opening paragraph, never a full advertisement. A posting that only
identifies itself as shared-services work further down is missed. Recall is
therefore a floor, not an estimate, and the in-scope counts below should be read
as "at least this many".

Three gates, in order. A posting must be finance or accounting work; it must
sit in a shared-services or capability-centre delivery model; and it must not
be one of the things that match those words without being the work — selling
services *to* GCCs, advising on them, or recruiting for them.

The delivery models are kept apart because they are different decisions. Work
placed in a captive capability centre, a captive shared-services centre, or a
third party is three different commitments of capital, control and risk, and a
location that suits one need not suit another:

- **GCC** — a captive capability centre, named as such.
- **GBS** — captive shared services: global business services, an SSC, a
  finance service centre.
- **BPO** — the same work at a third-party provider. In scope of the fetch,
  out of scope of this study, because a provider's location decision is not
  the client's.
"""

from __future__ import annotations

import importlib.util
import re

from src import config as C

# --- gate 1: is this finance or accounting work? --------------------------
# English first, then the languages the sampled markets actually advertise in.
# Leaving these out is not a neutral omission: Brazil returned 947 postings and
# the classifier recognised seven, because every Portuguese one was invisible
# to an English-only gate.
FINANCE = re.compile(
    r"\b(accounts payable|accounts receivable|record to report|order to cash|"
    r"procure to pay|general ledger|accounting|accountant|bookkeep|"
    r"reconcilia|financial report|financial statement|month.end close|"
    r"intercompany|accounts assistant|finance analyst|financial analyst|"
    r"controller|controlling|treasury|invoice|billing|credit control|"
    r"tax compliance|fp&a|\bap\b|\bar\b|\br2r\b|\bp2p\b|\bo2c\b|"
    # Portuguese
    r"contas a pagar|contas a receber|contabil|concilia[çc]|faturamento|"
    r"financeir|ci[êe]ncias cont[áa]beis|"
    # Spanish
    r"cuentas por pagar|cuentas por cobrar|contabilidad|conciliaci[óo]n|"
    r"facturaci[óo]n|tesorer[íi]a|"
    # Polish
    r"ksi[ęe]gow|rozrachunk|faktur|zobowi[ąa]za[nń]|nale[żz]no[śs]ci)",
    re.I,
)

# The processes a service centre actually runs, as opposed to finance in
# general. Used to qualify the language signal below.
TRANSACTIONAL_PROCESS = re.compile(
    r"\b(accounts payable|accounts receivable|record to report|order to cash|"
    r"procure to pay|general ledger|reconcilia|invoice|billing|credit control|"
    r"\bap\b|\bar\b|\br2r\b|\bp2p\b|\bo2c\b|\brtr\b|\bptp\b|\botc\b|"
    r"contas a pagar|contas a receber|concilia[çc]|faturamento|"
    r"cuentas por pagar|cuentas por cobrar|facturaci[óo]n|"
    r"rozrachunk|faktur)",
    re.I,
)

# --- gate 2: is it a shared-services or capability-centre model? ----------
# "GIC" was in this list and had to come out: it matched GIC Private Limited,
# Singapore's sovereign wealth fund, and labelled its portfolio-finance roles as
# capability-centre work. A three-letter acronym that is also a large employer's
# name is not a usable signal.
GCC_TERMS = re.compile(
    r"\b(global capability cent(er|re)|capability cent(er|re)|\bgcc\b|"
    r"global competency cent(er|re)|global in.house cent(er|re))",
    re.I,
)
GBS_TERMS = re.compile(
    r"\b(global business services|\bgbs\b|shared service|\bssc\b|"
    r"centrum usług wspólnych|servicios compartidos|"
    r"servi[çc]os compartilhados|centro de servi[çc]os|\bcsc\b|"
    r"business service cent(er|re)|finance service cent(er|re)|"
    r"captive cent(er|re)|delivery cent(er|re))",
    re.I,
)

# A shared-services centre in Central Europe hires by language before it hires
# by process: "Accountant with German" in Kraków is an SSC advertisement in all
# but name. Supporting evidence only — never enough on its own, because a
# language requirement also appears on ordinary local finance roles.
SSC_LANGUAGE = re.compile(
    r"\b(with (german|french|dutch|italian|spanish|nordic|swedish|danish|"
    r"norwegian|finnish|portuguese|czech|hungarian)|"
    r"(german|french|dutch|italian|nordic)[- ]speaking)\b",
    re.I,
)

# Finance vocabulary appears in workplaces that are plainly not GBS. A hotel
# cashier team lead matched every gate before this list existed.
WRONG_SETTING = re.compile(
    r"\b(hotel|hospitality|restaurant|guest|front desk|housekeeping|"
    r"retail store|store manager|branch manager|cashier|barista|"
    r"construction site|nursing|clinic)\b",
    re.I,
)

# Group reporting and statutory consolidation sit in the retained organisation,
# not the service centre — the work a GBS is designed *not* to move.
RETAINED_WORK = re.compile(
    r"\b(group financial reporting|group accountant|statutory reporting|"
    r"group consolidat|head of finance|finance director|cfo)\b",
    re.I,
)

# --- gate 3: matches the words without being the work ---------------------
# Selling to capability centres, or staffing them, is a different labour market
# that uses exactly the same vocabulary.
NOT_THE_WORK = re.compile(
    r"\b(sales|business development|account executive|pre.?sales|"
    r"solution consultant|client partner|recruit|talent acquisition|"
    r"staffing|headhunt|bid manager|proposal manager)\b",
    re.I,
)


def _org_type():
    path = C.POSTINGS_DB.parent.parent / "src" / "orgtype.py"
    spec = importlib.util.spec_from_file_location("shift_orgtype", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.org_type


def classify(title: str, description: str, company: str, org_type) -> str:
    """One of 'gcc', 'gbs', 'bpo', or a reason the posting is out of scope."""
    title = title or ""
    text = f"{title} || {description or ''}"

    # The exclusion is checked against the title only. A finance-delivery
    # posting often mentions "sales ledger" or an internal sales team in its
    # description; a sales job says so in its title.
    if NOT_THE_WORK.search(title):
        return "out:not_the_work"

    kind = org_type(company)
    if kind == "advisory":
        return "out:advisory"

    if WRONG_SETTING.search(text):
        return "out:wrong_setting"

    if not FINANCE.search(text):
        return "out:not_finance"

    is_gcc = bool(GCC_TERMS.search(text))
    is_gbs = bool(GBS_TERMS.search(text))
    if not (is_gcc or is_gbs):
        # A language requirement plus transactional finance is the Central
        # European SSC signature, and carries the posting on its own.
        if SSC_LANGUAGE.search(text) and TRANSACTIONAL_PROCESS.search(text):
            is_gbs = True
        else:
            return "out:not_shared_services"

    # Retained work that merely mentions the centre it reports into.
    if RETAINED_WORK.search(title) and not GCC_TERMS.search(title) \
            and not GBS_TERMS.search(title):
        return "out:retained_work"

    if kind == "bpo":
        return "bpo"
    # A capability centre named as such takes precedence: GCCs commonly
    # describe themselves with both vocabularies.
    return "gcc" if is_gcc else "gbs"


IN_SCOPE = ("gcc", "gbs")
