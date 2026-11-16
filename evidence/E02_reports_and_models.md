# E02 — Reports, Generated Summaries and Predictive Models (TEST-07 to TEST-17)

Sources: `evidence/validation_results.json` (database run 2026-11-15); `models/fraud_model_metrics.json` and
`models/alert_volume_metrics.json` (Week 11 final test, produced by `src/modeling/evaluate_week11.py`);
`docs/20_week11_evaluation_report.md`; smoke test `scripts/smoke_test_app.py`.

## A. Reports and charts
| Function | Check | Expected | Observed |
|---|---|---|---|
| Day selector "Day N (k alerts)" | Count per day equals `alert_queue` | Day 1 = 264, day 171 = 665 | Database: 264 and 665. **App display to confirm in the session (TEST-07)** |
| Queue "Amount in review" (normal case) | Policy P1, day 171, capacity 50: sum of the 50 largest amounts | $25,997.55 by SQL | **App display to confirm (TEST-08)** |
| Queue boundary case | Capacity ≥ alerts (day 1 at capacity 300) | Everything reviewed, "Not reviewed 0" | Code path confirmed in the smoke test; displayed values to confirm |
| Volume page actual counts | The model's saved test actuals equal the database daily counts | 0 differences | **0 differences on 44 test days** (TEST-09) |
| Volume metrics | MAE and coverage recomputed from the saved predictions | Equal to the report | MAE 41.508 = 41.508; same-as-yesterday 56.773 = 56.773; coverage 84.1% = 84.1% (TEST-09) |
| Invalid input (what-if) | 24-hour count > prior count + 1 | Blocked with an error | Blocked: "inconsistent" error shown (smoke test) (TEST-10) |
| Unsupported input | Amount ×3 (and $50,000) | Result shown with a range warning | Takeaway shows "⚠ Caution … outside the range"; comparison table shown (TEST-10) |
| Generated what-if summary | Figures equal the table; no causal wording | Probability, rank and action match the table; the wording says "the model's estimate", "not proof" | Takeaway lines are built from the same `res` values as the table; the full summary keeps "associations, not causes" (TEST-11) |
| Estimate vs. actual | The queue's "Est. fraud $ covered" is labelled as an estimate | A note on the queue page and the model page | Notes added Week 12 after user feedback (TEST-12) |

**Denominators.** The queue's *Est. fraud $ covered* = Σ expected exposure of the reviewed alerts ÷ Σ expected
exposure of **today's alerts** (a model estimate). KPI 1 = real fraud dollars caught ÷ real fraud dollars of **all**
the day's transactions (`evaluate_week11.py` lines 80–100 rank every transaction per day). The two answer different
questions, which explains 72% vs. 33%.

## B. Fraud probability model (KPI 1)
- **Evaluation setting:** time-ordered split. 60% development, 15% validation, 25% final test (147,635 transactions,
  days 130–182, fraud rate 3.45%). It was run once, which represents "score tomorrow's transactions with a model
  trained on the past" (TEST-13).
- **Against baselines** (fraud value captured at 50 reviews a day): P4 expected exposure 32.7%; P1 largest amount
  19.7%; P3 probability only 20.9%; P2 rule score 15.5%; P0 random 2.0%. PR-AUC 0.383 against 0.035–0.040 for the
  baselines (TEST-13).
- **Calibration:** expected calibration error 0.0031 across 10 deciles; the top decile predicted 21.4% against 19.3%
  observed, a slight over-estimate (TEST-14).
- **Subgroups and costly errors** (share of fraud caught in the top 5%): product C 75%, R 64%, H 51%, S 51%,
  **W 11% (PR-AUC 0.072)**; credit 58%, **debit 30%**; over $1,000 33%; new customers 48%. The worst test day
  (day 182) captured 3.6% at 50. Costly errors: high-value fraud on product W and debit cards ranks low (TEST-15).
- **Leakage and availability:** 0 of 501,015 history rows used a later transaction; time periods do not overlap;
  no single feature has suspiciously high AUC (Week 11). All predictors are point-in-time or present at
  authorization in the source (IEEE C/D counts); the fraud label is not stored in the app database (TEST-16).
- **Uncertainty:** a 90% range per alert from 30 bootstrap refits.
- **Do not use when:** the product is W or the card is debit (weak ranking); amounts or counts are outside the
  training range (the app warns); the data come from a different institution or period (no drift monitoring yet);
  or to make an automatic decline (decision support only).
- **Synthetic caveat:** labels and transactions are real IEEE-CIS data, but customers, accounts, devices and
  capacity are generated or assumed. Performance is shown **within this simulated setting**, not as evidence of
  real-world readiness.

## C. Alert volume model (KPI 2)
- **Setting:** train days 8–112, validation 113–138, test 139–182 (44 days), run once.
- **Against baselines:** MAE 41.5 against same-as-yesterday 56.8, 7-day average 60.7 and same weekday 59.1. The
  candidate with older lags (44.4) was rejected on validation (TEST-17).
- **Overflow accuracy:** capacity 50: 91% (2 missed, 2 false alarms); capacity 100: 73% (9 missed, 3 false alarms);
  capacity 150: 91% (2 missed, 2 false alarms).
- **Subgroups:** quiet days MAE 14.3 and coverage 93%; **busy days MAE 90.0, bias +56, coverage 67%**; Thursdays
  MAE 151 (spike days 164 and 171).
- **Sensitivity:** total alerts move −9.6% to +8.1% under plausible changes to the rule thresholds (E01 §F). The
  volume model was **not** retrained under the alternative thresholds.
- **Do not use when:** a known event or campaign may cause a spike; or on busy days, without using the upper end of
  the range.
