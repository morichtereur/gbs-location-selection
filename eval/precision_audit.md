# Precision audit — delivery-model classifier

Three audits, sixty postings, each drawn at random from the in-scope population
and adjudicated by reading the title, employer and the 500 characters Adzuna
returns.

| audit | classifier state | correct | wrong | unclear | precision |
|---|---|---:|---:|---:|---:|
| 1 (`seed=4242`) | English/Spanish/Polish patterns | 16 | 3 | 1 | ~80% |
| 2 (`seed=90210`) | after Portuguese was added | 11 | 6 | 3 | ~55% |
| 3 (`seed=31337`) | after public-sector and non-finance-role fixes | 10 | 7 | 3 | ~50% |

**Reported precision is roughly 55%**, not the 80% the first audit suggested.

That first number did not survive re-testing. It was one sample of twenty, taken
when the classifier read three languages; widening it to Portuguese raised
recall — Brazil went from 7 recognised postings to 52 — and lowered precision,
and re-auditing showed the 80% had been a favourable draw as much as a better
classifier. Both audits after it land near 55%, which is the number to use.

## What is still wrong, after three rounds of fixes

Fixes did remove whole failure modes: a hotel cashier (audit 1), a municipal
shared-services centre recruiting a civil servant, and an EHS manager whose
employer's blurb happened to list finance functions (both audit 2). What
survives is more stubborn:

- **Retained work with the right vocabulary.** Group controllers, statutory
  reporting leads and entity accountants read like service-centre postings and
  are the opposite of one — they are the work a GBS exists not to move.
- **Recruiter and staffing postings** that mention a client's shared-services
  environment without the role being in it.
- **Finance roles with no centre evidence at all**, where the shared-services
  signal sits past the 500-character truncation or is absent and something else
  matched.

## What this means for the study

The Monte Carlo resamples the binomial sampling error behind every capability
share. **It does not model classification error**, and at 55% precision that is
the larger of the two. The capability pillar should be read as carrying roughly
a 45% contamination rate on top of the sampling interval already shown, and the
ordering of cities that differ only on capability — which is every city outside
Poland — is weaker than the stability column alone implies.

**The study no longer leaves this as a caveat.** `src/stability.py` recovers the
true share from the contaminated one on every draw, using a precision drawn from
these audits and a contaminant mix measured from the broad finance sample. Doing
so reversed the judgment-centre conclusion: Germany fell from 91% to 67% and
India rose from 78% to 92%, because a posting wrongly admitted in India is
probably transactional and one wrongly admitted in Poland is probably judgment.

Germany was never robust as a judgment location. It looked robust because a
known error sat outside the model — which is the strongest argument in this
repository for its own central claim: a number that looks measured can still be
mostly a modelling choice.
