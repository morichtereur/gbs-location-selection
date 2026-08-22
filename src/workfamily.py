"""Local-language supplement to the English work-family taxonomy.

The taxonomy this project reuses from the sibling study is English-only, which
is correct for the sample it was built on and wrong for this one. Brazil
returned 52 GBS postings and the taxonomy could decide eight of them: the other
44 are written in Portuguese and came back ambiguous, so they were dropped from
the capability denominator. Measuring a market's work mix on whichever postings
happen to be in English is a bias, not a sample.

This runs **only on postings the English taxonomy declined to decide**, so it
can add recall and cannot overturn the primary classifier. Visible phrase lists,
same as everything else here, and the share still decided by neither is
reported per market rather than hidden.
"""

from __future__ import annotations

import re

# Processing work: the ledger entries a service centre actually runs.
TRANSACTIONAL = re.compile(
    r"("
    # Portuguese
    r"contas a pagar|contas a receber|faturamento|concilia[çc][ãa]o|"
    r"lan[çc]amento cont[áa]bil|escritura[çc][ãa]o|folha de pagamento|"
    # Spanish
    r"cuentas por pagar|cuentas por cobrar|facturaci[óo]n|conciliaci[óo]n|"
    r"registro cont[áa]ble|n[óo]mina|"
    # Polish
    r"ksi[ęe]gowani|faktur|rozrachunk|zobowi[ąa]za[nń]|nale[żz]no[śs]ci|"
    r"list[ay] p[łl]ac"
    r")",
    re.I,
)

# Work that turns numbers into a decision.
JUDGMENT = re.compile(
    r"("
    # Portuguese
    r"controladoria|an[áa]lise financeira|planejamento financeiro|"
    r"or[çc]amento|auditoria|business partner|assessoria|"
    # Spanish
    r"controlling|an[áa]lisis financiero|planificaci[óo]n financiera|"
    r"presupuesto|auditor[íi]a|"
    # Polish
    r"kontroling|analiz[ay] finansow|bud[żz]et|audyt|raportowani"
    r")",
    re.I,
)


def decide(text: str) -> str | None:
    """'transactional', 'judgment', or None when this cannot decide either.

    A posting matching both counts as neither: the point of the supplement is
    recall on clear cases, not adjudication of hard ones.
    """
    t = TRANSACTIONAL.search(text or "")
    j = JUDGMENT.search(text or "")
    if bool(t) == bool(j):
        return None
    return "transactional" if t else "judgment"
