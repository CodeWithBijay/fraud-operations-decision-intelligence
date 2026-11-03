# 20 — Week 11 Evaluation Report: Model Evaluation and Decision Support

**Project:** Fraud Operations Decision Intelligence (FraudOps) · **Team:** Bijay and Gerald
**Decision-maker:** Fraud Operations Lead with limited review capacity
**Reproduce:** `python3 src/modeling/week11_split_and_leakage.py` then `python3 src/modeling/evaluate_week11.py`
(outputs in `reports/week11/`). App: `streamlit run app/app.py`; Week 10 version kept in `app/week10/app.py`
and git tag `week10-submission`.

## 1. Evaluation design

**Split (by time).** Fraud happens in time and the tool is used on future days, so a random split would leak future
patterns into training.

| Period | Transactions | Days | Fraud rate | Purpose |
|---|---|---|---|---|
| Development | 354,324 | 1–101 | 3.38% | Fit candidate models |
| Validation | 88,581 | 101–130 | 4.04% | Make every modeling choice |
| Final test | 147,635 | 130–182 | 3.45% | Run once, after the choice was fixed |

The volume model uses the same 60/15/25 split on days (final test: the last 44 days).

**Leakage checks (all passed).** History features only look backward (0 of 501,015 rows used a later transaction); the
24-hour count never exceeds prior history; periods do not overlap; and no single raw predictor separates fraud
suspiciously well (strongest: C4, AUC 0.68). *Caveats:* Week 9 alert-rule thresholds were percentiles of the full
period (slight look-ahead in the rule baseline and alert counts, not in the fraud model); C/D variables are anonymized,
so their timing is taken as documented by the provider.

**Pre-registered selection rules.** Fraud: keep the candidate only if validation fraud value captured at 50 reviews/day
rises by ≥ 0.5 points. Volume: keep the candidate only if validation MAE falls by ≥ 2%. Otherwise keep the simpler model.

## 2. Metrics tied to the decisions
- **KPI 1, fraud value captured at capacity K:** the share of a day's fraud dollars inside the K alerts reviewed.
  Supporting: PR-AUC, ROC-AUC, Brier score (probability quality, needed because the queue uses probability × amount).
- **KPI 2, daily alert overflow:** alerts beyond capacity. Supporting: MAE, MAPE, 90% interval coverage, overflow-day
  accuracy, missed overflow days, false alarms.

## 3. Results against baselines (final test, run once)

| Fraud model | PR-AUC | ROC-AUC | Brier | Fraud $ captured at 50/day |
|---|---|---|---|---|
| **Selected: Week 10 + D10–D14, email, card network** | **0.383** | **0.845** | **0.0261** | **32.7%** |
| Week 10 specification (29 predictors) | 0.367 | 0.840 | 0.0265 | 33.0% |
| Baseline: largest amount first | 0.038 | 0.487 | — | 19.7% |
| Baseline: Week 9 rule score | 0.040 | 0.499 | — | 15.5% |
| Baseline: random | 0.035 | 0.505 | — | 2.0% |

| KPI 1 by policy | 25/day | 50/day | 100/day | 200/day |
|---|---|---|---|---|
| **P4 Expected exposure (p × amount)** | **21.6%** | **32.7%** | **48.2%** | **64.5%** |
| P3 Model probability | 11.8% | 20.9% | 31.7% | 44.1% |
| P1 Largest amount | 8.9% | 19.7% | 35.2% | 48.6% |
| P2 Rule score | 8.8% | 15.5% | 24.7% | 44.4% |
| P0 Random | 1.2% | 2.0% | 4.3% | 8.4% |

| Volume model | MAE (alerts/day) | MAPE | 90% coverage |
|---|---|---|---|
| **Selected: Week 10 specification** | **41.5** | **26.6%** | **84%** |
| Candidate: + lag 2 and same weekday last week | 44.4 | 30.3% | 86% |
| Baseline: same as yesterday | 56.8 | 42.5% | — |
| Baseline: same weekday last week | 59.1 | 71.6% | — |
| Baseline: previous 7-day average | 60.7 | 57.0% | — |

| KPI 2 overflow days | Actual | Predicted | Accuracy | Missed | False alarms |
|---|---|---|---|---|---|
| Capacity 50 | 39 | 39 | 91% | 2 | 2 |
| Capacity 100 | 21 | 15 | 73% | 9 | 3 |
| Capacity 150 | 3 | 3 | 91% | 2 | 2 |

## 4. Error analysis
**Fraud model.** 42.8% of fraud cases fall in the top 5% of probabilities. **Product W** (80% of test transactions)
is the main weakness: only 11% of its fraud reaches the top 5% (PR-AUC 0.07). **Debit cards** are weaker than credit
(30% vs. 58%). The model **over-predicts** for product S (9.1% predicted vs. 5.5% actual) and amounts over $1,000
(6.2% vs. 2.8%). The worst test day (182, likely partial) captured 4% at 50 reviews.

**Volume model.** Test error (41.5) is three times the validation error (13.8) because the test period contains sudden
spikes the lag-based model cannot anticipate (day 171: 665 actual vs. 56 forecast; day 164: 340 vs. 65), and it
over-forecasts the day after (day 173: 87 vs. 244). Busy days are under-forecast by 56 alerts on average (67%
coverage); quiet and typical days are within about 9 alerts (93% coverage).

## 5. One improvement per model

| Model | Candidate | Validation | Decision | Final test |
|---|---|---|---|---|
| Fraud | + D10–D14, purchaser email, card network (29 → 48 predictors) | Capture@50 35.5% → 37.2% (+1.6 pts) | **Kept** | Better PR-AUC and Brier; capture@50 32.7% vs. 33.0%: the KPI gain did not carry over |
| Volume | + alerts two days ago, same weekday last week | MAE 13.8 → 13.9 | **Rejected** | Also worse (44.4 vs. 41.5) |

We did not switch back after seeing the test, since that would be tuning on the test. Conclusion: the extra attributes
improve probability quality but give no measurable KPI gain; the volume data have no useful weekly pattern beyond the
7-day average.

## 6. Decision-support updates in the app

| Requirement | Implementation |
|---|---|
| Plain-language performance and limits | "How much to trust" boxes on the investigation and model pages, built from final-test results |
| Local vs. global explanations | "This alert only" contribution chart (exact linear SHAP); overall importance on the model pages; both captioned as non-causal |
| Controllable vs. fixed variables | What-if inputs grouped as ① scenario inputs / decision lever, ② fixed characteristics / external conditions, ③ recorded attributes / calendar; roles table in each model card |
| Input checks, ranges, constraints | Impossible combinations blocked; warnings outside the 1st–99th training percentile |
| Side-by-side comparison | Baseline vs. scenario table: inputs, probability, range, exposure, queue rank, inside capacity |
| Summary with trade-offs, no causal claims | Inputs / Comparison / Trade-off / Implication / Limitations |

**Review fixes:** dollar amounts in summaries and warning boxes displayed as math text (fixed); truncated chart labels
(fixed); the comparison table hid its first row (fixed); "+19 places" was ambiguous (now "#1 → #20, 19 places lower
priority"); a confusing "0 of 53 days" statement was replaced by the worst-day result.

## 7. User test
**Status: not completed by the submission deadline.** The protocol (`docs/19_user_test_protocol.md`) and participant
sheet (`docs/19a_participant_sheet.md`) are ready. A session with a participant outside the group will be run and its
findings, and the resulting app change, added in a follow-up commit.

**Pilot walkthrough (not a user test).** An AI-assisted walkthrough of the five tasks
(`docs/19c_ai_pilot_walkthrough.md`) found one bug, now fixed: dollar amounts in warning boxes displayed as garbled
math text. It flagged three items for the user test to confirm: the row-click wording, missing chart labels and the two
capacity controls.

## 8. Limitations and next steps
- Public IEEE-CIS data with generated identities: results describe this simulated setting, not a real bank.
- Fraud labels arrive with delay in real operations; here they are final.
- The fraud model is weak on product W, the largest segment; next: segment-specific features or a separate model.
- The volume model cannot anticipate spikes; next: same-day early signals, and a refit after rule changes.
- Explanations show associations, not causes; C1–C14 are anonymized and correlated.
