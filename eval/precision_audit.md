# Precision audit — delivery-model classifier

Twenty in-scope postings drawn at random (`seed=4242`) from the GBS/GCC sample
and adjudicated by reading the title, employer and the 500 characters Adzuna
returns. Recorded so a reader can disagree with a specific row.

| # | verdict | posting | why |
|---|---|---|---|
| 1 | correct | P2P Manager, Wrocław | "creating a new business services center" |
| 2 | **wrong** | Credit Collection Agent, NL | AR team, no centre evidence anywhere in the text |
| 3 | correct | BASF, DE | the "Global Business Services" unit, named |
| 4 | unclear | Senior AP Controller, ZA | AP function lead; the centre reference, if any, is past the truncation |
| 5 | **wrong** | Financial Analyst, PL | IT cost management, not a service-centre process |
| 6 | correct | Statutory & GL Accountant, PL | "preferably in a Shared Services environment" |
| 7 | correct | Tax Services Specialist, PL | Boehringer's EMEA tax service organisation |
| 8 | **wrong** | Finance & Consolidations Lead, SG | full set of accounts for a corporate division — retained work |
| 9 | correct | AP Administrator, GB | "our shared service centre in Newcastle upon Tyne" |
| 10 | correct | Kraft Heinz GBS, Mexico City | GBS named in the title |
| 11 | correct | Finance SSC AR&TR Supervisor, PL | SSC in the title |
| 12 | correct | Bertelsmann Center of Expertise, DE | a named centre of expertise |
| 13 | correct | Księgowość, Katowice | "centrum usług wspólnych" |
| 14 | correct | Finance Shared Services GL, GB | named in the title |
| 15 | correct | Shared Services Accountant, GB | named in the title |
| 16 | correct | Head of Business Process, ZA | process governance across a shared-services org |
| 17 | correct | Senior GL Accountant, IN | inDrive "Accounting Hub in India", P2P |
| 18 | correct | Novo Nordisk GBS, Bangalore | GBS named |
| 19 | correct | Accountant, Łódź | "w strukturach SSC" |
| 20 | correct | Manager Finance AP/AR, NL | Kruidvat "Finance Shared Service Centre" |

**16 correct, 3 wrong, 1 unclear — precision ≈ 80%** (0.84 if the unclear row is
excluded). Twenty rows is a small audit: the 95% interval runs roughly 56% to
94%, so this establishes the order of magnitude, not a decimal.

Recall is not measured and is certainly worse. Adzuna truncates descriptions at
500 characters, so any posting that identifies itself as centre work later in
the advertisement is invisible to every gate. Counts here are floors.
