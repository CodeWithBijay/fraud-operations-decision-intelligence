# E03 — UI Elements, Roles and the Assistant (TEST-18 to TEST-27)

App version: commit `6c74225` (2026-11-15) plus the Week 12 fixes listed in §D. Automated checks:
`cd scripts && python3 smoke_test_app.py` (Streamlit AppTest, headless, against the project database).

## A. Automated UI checks (smoke test, 2026-11-15)
```
Sign-in page shown       OK        (TEST-24)
Wrong password blocked   OK        (TEST-24)
Analyst pages limited    OK        (3 pages; capacity slider disabled) (TEST-25)
Alert queue              OK
Alert investigation      OK
Fraud risk model         OK
Alert volume forecast    OK
What-if (amount x3)      OK - table + summary shown | errors: 0   (TEST-10)
Invalid input check      OK - blocked                             (TEST-10)
Assistant chatbot        OK - answer + sources | errors: 0         (TEST-21)
RESULT: ALL PAGES OK
```
Passwords are stored as salted PBKDF2-SHA256 hashes (200,000 iterations) in Streamlit Secrets
(`scripts/make_user.py`). After 5 failed attempts, sign-in locks for 60 seconds. These are role views for a
classroom demonstration, not bank-grade access control: there is no audit trail or account management.

## B. UI function → requirement map
| UI element | Requirement | Validation question | Evidence |
|---|---|---|---|
| Decision banner and KPI tiles (Queue) | R1 | Correct value, unit, period, comparison? | TEST-07/08 (database recalculation) and user task T1 |
| "Review these first" + Open | R1, R3 | Can the user find the first alert and open it? | User task T1–T2 |
| Settings bar (day, policy, capacity) | R1, R2, R5 | Is the active population clear? Lead-only controls? | The settings bar shows "signed in as … (role)"; TEST-25 |
| Capacity trade-off box (Lead) | R2 | Does it show the extra coverage from more reviewers? | TEST-19 and user task T4 |
| What-if inputs | R3 | Valid inputs enforced? Controllable vs. fixed? | TEST-10; inputs grouped "you can change" / "fixed" |
| Baseline vs. scenario table and takeaway | R3 | Baseline, modified inputs and changes distinguishable? | TEST-11 and user task T3 |
| Explanation charts | R3 | Read without treating them as causes? | `NOT_CAUSAL` caption on every explanation; user task T2 |
| Warnings and trust boxes | R1–R3 | Unsupported scenarios and limits recognized? | TEST-10 and user task T3 |
| Volume forecast and range | R2 | Forecast, range and capacity comparison readable? | User task T4 |
| Assistant chatbot and glossary | R4 | Correct, sourced, plain answers? | §C and user task T5 |

## C. Assistant (retrieval-augmented chatbot) tests
Criterion, set before testing: for each standard question, the correct glossary or report section is among the top
4 sources, and no answer states a figure or rule that contradicts the documents.

| Question | Top source | Result |
|---|---|---|
| What does PR-AUC mean? | Glossary "PR-AUC" (#2) and "ROC-AUC" (#1) | Pass |
| Why do the queue and model pages show different coverage? | Week 11 report §6, then glossary "Estimate vs. actual" | Pass |
| How accurate is the alert volume forecast? | Glossary "KPI 2" | Pass |
| Where is the fraud model weak? | Glossary "Weak spots" | Pass |
| what is KPIs | **None relevant**: "KPIs" did not match "KPI" | **Fail → fixed** (plural matching plus a glossary "KPIs" entry), retest Pass (TEST-22) |
| what is alert | Glossary "Alert": answered "flagged by **at least one** of six rules" | **Fail**: contradicts the data (alerts need **at least two** rules; E01 §C). Fixed in the glossary, retest Pass (TEST-23) |

The Assistant sends only the retrieved passages, the recent chat and the question to Gemini; no transaction data.
Gemini answers depend on an external service; when it is unavailable, the page shows the sources only
(URLError/HTTPError handled, observed during setup when Mac certificates were missing).

## D. Changes made in response to validation findings (Week 12)
1. Estimate vs. actual notes on the queue and model pages (user feedback, Nov 4).
2. A three-line what-if takeaway, with the range warning repeated (user feedback).
3. A "New customer: no history" note instead of unexplained zeros (user feedback).
4. A capacity trade-off line for the Lead (user feedback).
5. Sign-in with Lead and Analyst roles; policy and capacity locked for analysts (R5).
6. The Assistant chatbot and plain-language glossary (user feedback: jargon).
7. Glossary corrected: an alert needs at least two rules (TEST-23 fail).
8. The Assistant matches plural words; a glossary "KPIs" entry (TEST-22 fail).
