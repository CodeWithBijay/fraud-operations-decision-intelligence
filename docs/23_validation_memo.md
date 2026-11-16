# Validation Memo: FraudOps Decision Intelligence (Weeks 12–13)

**To:** Prof. Mudigonda, AA 5960 · **From:** Bijay Bahadur Paudel and Gerald Hlabiso · **Date:** 15 November 2026
**Evidence:** `validation/Week12_Validation_Matrix.xlsx` (39 rows), `evidence/` (E01–E05, `validation_results.json`),
`docs/22_decision_requirements.md`. Reproduce with `scripts/validate_week12.py` and `scripts/smoke_test_app.py`.

## 1. What we validated
The intended decision-maker is a Fraud Operations Lead who must (R1) choose which of the day's alerts the team
reviews within about 50 reviews a day, (R2) plan tomorrow's capacity, (R3) let analysts investigate one alert and
test a what-if, (R4) understand the numbers and their limits, and (R5) keep policy and capacity under the Lead's
control. The KPIs are unchanged: KPI 1 is fraud value captured at capacity; KPI 2 is daily alert overflow. The model criteria
were pre-registered in Week 11; the Week 12 criteria were written in the same session as the checks, some after earlier results were known (marked in the matrix), and none was changed or lowered. We tested 39 claims (including two retests): 23 pass,
9 partial pass, 6 fail, 1 not tested.

## 2. Supported claims
- **The alert data are internally consistent.** On 590,540 transactions there were zero duplicate IDs and zero
  missing required fields. Every point-in-time rule holds. Recomputing all six alert rules from the features
  reproduces the queue exactly: 0 mismatches, and the 23,688 alerts are exactly the transactions with at least two
  rules (TEST-01, TEST-03).
- **The default queue policy helps the Lead's main decision.** On the single final test, ranking by expected
  exposure captured 32.7% of fraud dollars at 50 reviews a day, against 19.7% for largest-amount-first and 2.0% at
  random. Probabilities are well calibrated (expected calibration error 0.003), and no leakage was found
  (TEST-13, TEST-14, TEST-16).
- **The volume forecast beats naive forecasts.** MAE 41.5 against 56.8 for same-as-yesterday; 91% overflow
  accuracy at capacity 50. Its figures reconcile exactly with the database on all 44 test days (TEST-09, TEST-17).
- **The what-if and summaries behave correctly.** Invalid inputs are blocked, out-of-range inputs are warned, and
  the takeaway uses the same values as the table with non-causal wording (TEST-10, TEST-11).
- **Roles work.** Unauthenticated users see only the sign-in page; analysts cannot change policy or capacity;
  passwords are stored only as salted hashes (TEST-24 to TEST-26).

## 3. Unsupported claims, failures and risks
1. **Product W and debit cards are under-served (TEST-15, Fail).** Product W is 80% of transactions, but only 11%
   of its fraud reaches the top 5% of scores (PR-AUC 0.072); for debit cards it is 30%. The queue therefore favours
   other products. *Consequence:* the largest fraud stream is reviewed least.
2. **Spikes cannot be anticipated (TEST-18, TEST-29, Fail).** On day 171, 665 alerts arrived against a forecast of
   56 (upper bound 92). On busy days the 90% range covered only 67% of actuals, with a bias of +56. *Consequence:*
   a Lead trusting the forecast could leave about 90% of alerts unreviewed on a spike day.
3. **Generated customer IDs are implausible at the extremes (TEST-04, Partial).** One generated "customer" has
   4,015 transactions in 182 days, because the grouping rule merges cards. Velocity and z-score rules are distorted
   for such IDs. Separately, 525 transactions have extreme amount z-scores (customers whose earlier
   amounts were identical), which affects 35 amount-spike alerts (TEST-33, Fail). **The real-world realism of the generated IDs is unvalidated:** amounts match the source, but that
   only confirms a faithful load.
4. **Generated help text contradicted the data (TEST-23, Fail, then fixed).** The glossary, and therefore the
   Assistant, said an alert needs "at least one" rule; the data show at least two. A plural question ("KPIs")
   returned nothing (TEST-22). Both were fixed and retested (TEST-22R, TEST-23R pass). This shows that generated
   explanations need the same validation as numbers.
5. **On-screen values verified (TEST-07, TEST-08, Pass).** Counts and queue totals shown in the app match the database.
6. **Limited user evidence (TEST-20, 27, 30, 31, all Partial pass).** One informal review (Nov 4) and one task-based
   session (Nov 15, `evidence/E04`) with one participant outside the group, not fraud-operations staff. He chose the
   right first alert but by risk % only, read the largest driver as a cause, and confused forecast with actual.
7. **Assumptions:** capacity (50) is assumed, not observed; there is only 6 months of data with no seasonality; and
   the Assistant depends on an external AI service (with a search-only fallback).

## 4. Corrective actions and priorities
| Priority | Action | Closes |
|---|---|---|
| 1 | Flag product-W and debit alerts in the queue with a "weak model area" badge, and add W-specific features or a separate W model; re-run TEST-13 and TEST-15 | Failure 1 |
| 2 | Add an intraday early-warning signal (alerts in the first hours) and a "plan to upper bound on volatile weeks" rule on the Volume page; re-run TEST-18 | Failure 2 |
| 3 | Flag generated customers with more than 1,000 transactions; test a finer grouping rule (add card2/card5); re-run TEST-03, TEST-04, TEST-13 | Risk 3 |
| 4 | Confirm TEST-07 and TEST-08 in the app with screenshots; add an automated display test | Risk 5 |
| 5 | Add the Assistant's standard questions to the smoke test; validate every glossary figure against `validation_results.json` | Failure 4 |
| 6 | Run a second task-based session with someone closer to the role (for example a bank or fraud professional) | Risk 6 |

## 5. Suitability
**Suitable for classroom demonstration: yes.** The workflow is complete, internally consistent, reproducible and
honest about its limits.
**Controlled pilot: not yet.** A pilot would need a check on real (non-generated) customer identities, the
product-W fix, spike handling, and testing with real fraud analysts; even then it should run alongside the existing
process.
**Operational use: no.** The evidence comes from a simulated setting (public data, generated identities, assumed
capacity, instant labels). Strong performance on this test data is not evidence of real-world readiness, and two
consequential failures (product W, spikes) remain open.
