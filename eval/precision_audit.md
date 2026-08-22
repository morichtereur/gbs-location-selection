# Precision audit — delivery-model classifier

Five audits, one hundred postings, each drawn at random from the in-scope
population and adjudicated by reading the title, employer and the 500 characters
Adzuna returns.

| audit | classifier state | correct | wrong | unclear | strict | resolvable |
|---|---|---:|---:|---:|---:|---:|
| 1 (`4242`) | English/Spanish/Polish | 16 | 3 | 1 | 80% | 84% |
| 2 (`90210`) | + Portuguese | 11 | 6 | 3 | 55% | 65% |
| 3 (`31337`) | + public-sector, non-finance-role fixes | 10 | 7 | 3 | 50% | 59% |
| 4 (`24601`) | + counterparty rule | 12 | 6 | 2 | 60% | 67% |
| 5 (`112358`) | + retained-work in body — **ships** | 12 | **2** | 6 | 60% | **86%** |

*Strict* counts every unresolved case as a failure. *Resolvable* excludes them.
The truth is between; the model uses the strict figure so it errs toward wider
uncertainty.

## What the sequence shows

Audit 1's 80% did not survive re-testing. Widening the classifier to read
Portuguese raised recall sharply — Brazil went from 7 recognised postings to 52
— and precision fell to the mid-fifties, where two audits agreed.

Two fixes then moved it, and both came out of reading the failures rather than
guessing:

- **The centre as counterparty.** A posting can name a service centre without
  the role being inside it. "Join our Shared Services team" is the work;
  "liaises with the internal Shared Service Centers" and "review of transactions
  done by the shared service centre" are roles on the other side of the counter,
  usually in the retained organisation the centre serves. 27 postings excluded.
- **Retained work in the body, not just the title.** A tax accountant whose
  opening line is "legal entity reporting and full tax compliance" is retained
  work whatever the employer boilerplate says further down. 14 postings.

Definite errors fell from six or seven per twenty to **two**.

## What still gets through

- Small-company bookkeeping and holding-company controlling that mention finance
  operations without being service-centre work.
- Recruiter postings describing a client's environment rather than the role.
- A BPO operations role advertised through a staffing agency, where the employer
  field names the agency and not the provider.

## Earlier failure modes, since fixed

A hotel cashier cleared every gate before a wrong-setting list existed.
Singapore's sovereign wealth fund was read as a capability centre because "GIC"
was in the acronym list. A municipal shared-services centre recruiting a civil
servant counted as GBS. An EHS manager passed because his employer's blurb
listed finance functions — the gate was reading the company, not the job.

## How this feeds the study

`src/stability.py` recovers the true capability share from the contaminated one
on every draw, using a precision drawn from these audits and a contaminant mix
measured from the broad finance sample. That correction reversed the
judgment-centre conclusion — Germany fell out of robust and India rose into it —
and the reversal holds whether precision is set at 52% or 60%.

Germany was never robust as a judgment location. It looked robust because a
known error sat outside the model, which is the strongest argument in this
repository for its own central claim: a number that looks measured can still be
mostly a modelling choice.
