# E02 — Reports, Generated Summaries and Predictive Models (TEST-07 to TEST-17)

Sources: `evidence/validation_results.json` (database run 2026-11-15); `models/fraud_model_metrics.json` and
`models/alert_volume_metrics.json` (Week 11 final test, produced by `src/modeling/evaluate_week11.py`);
`docs/20_week11_evaluation_report.md`; smoke test `scripts/smoke_test_app.py`.

### A0. Definitions per reporting function
| Function | Formula | Unit | Aggregation and filter | Denominator | Period |
|---|---|---|---|---|---|
| Queue banner: amount in review | Σ amount of alerts ranked ≤ capacity under the chosen policy | US dollars | Alerts of the selected day | — | One simulated day |
| Queue banner: est. fraud $ covered | Σ (p × amount) of reviewed alerts ÷ Σ (p × amount) of all the day's alerts | % | Alerts of the selected day | **Today's alerts** (a model estimate) | One day |
| Capacity trade-off | Same estimate at capacity + 50 minus at capacity; tested KPI 1 values by capacity | percentage points; % | Day's alerts; final test | Today's alerts; **all of a day's transactions** (tested) | One day; test days 130–182 |
| Fraud model page: KPI 1 | Real fraud $ inside the top-k by policy ÷ all of the day's real fraud $, averaged over days | % | All transactions per test day | **All fraud dollars of the day** | 53 test days |
| Volume page | Poisson forecast of tomorrow's alerts with a 90% range; overflow = alerts − capacity | alerts/day | Daily alert counts | — | Test days 139–182 |
| What-if takeaway | p and rank recomputed with edited inputs | %, rank | One alert within its day's queue | — | Selected day |
| Decision history | Rows of ops_decision_log for the alert | — | Selected alert | — | All saved decisions |

## A. Reports and charts
| Function | Check | Expected | Observed |
|---|---|---|---|
| Day selector "Day N (k alerts)" | Count per day equals `alert_queue` | Day 1 = 264, day 171 = 665 | Database: 264 and 665. **App display to confirm in the session (TEST-07)** |
| Queue "Amount in review" (normal case) | Policy P1, day 171, capacity 50: sum of the 50 largest amounts | $25,997.55 by SQL | **App display to confirm (TEST-08)** |
| Queue boundary case | Capacity ≥ alerts (day 1 at capacity 300) | Everything reviewed, "Not reviewed 0" | Code path confirmed in the smoke test; displayed values to confirm |
| Queue boundary: capacity > alerts (day 160, capacity 150) | Everything reviewed; trade-off says no gain | "All 104 alerts fit", $76,321 in review (= $53,519 + $22,801), 0 not reviewed; trade-off: "extra reviewers would not add coverage today" (TEST-35) |
| Queue boundary: minimum capacity (day 160, capacity 5) | Top 5 by P4; amount = their sum | $8,680 in review = $1,600 + $600 + $2,161 + $2,743.95 + $1,575.50 = $8,680.45; $67,640 not reviewed (TEST-35) |
| Queue invalid capacity (< 5 or > 300) | Not possible to enter | The slider enforces 5–300 in steps of 5 (TEST-35) |
| Fraud model page values | Displayed tables equal the stored test results | P4 capture at 25/50/100/200 = 0.216/0.327/0.482/0.645; PR-AUC 0.3826, ROC-AUC 0.8454, Brier 0.0261, identical to fraud_model_metrics.json; the trust box says ~33% vs. 20% (TEST-36) |
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
- **Does the evaluation represent the intended setting?** Partly. It is time-ordered, run once, and covers the
  same alert rules and features the app uses. But: (1) labels are known immediately, whereas in practice fraud is
  confirmed weeks later; (2) the data come from one source and period (6 months, no seasonality); (3) customers,
  accounts and devices are generated, and 525 extreme z-scores and merged high-volume IDs (E01) affect the inputs;
  (4) capacity is assumed. Results therefore describe the simulated environment.
- **Sensitivity to generation assumptions (TEST-37, not tested):** alert volume moves −9.6% to +8.1% under
  threshold changes (E01 §F), but the fraud and volume models were **not retrained** under alternative thresholds,
  ID-grouping rules or z-score floors. Plan: re-run `evaluate_week11.py` with R5 = $400/$500, a std floor of $1 and a
  finer CustomerID rule, and compare KPI 1 and the volume MAE.
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
