# FraudOps Decision Intelligence

> ## 📌 Weeks 12–13: Validation of the Decision-Support Application
> **Start here.** This section summarizes the validation submission; earlier weeks follow below.

| Deliverable | Where |
|---|---|
| **Validation matrix** (39 tests: 23 Pass, 9 Partial, 6 Fail, 1 Not tested; course template) | [`validation/Week12_Validation_Matrix.xlsx`](validation/Week12_Validation_Matrix.xlsx) |
| **Validation memo** (2–3 pages) | [`docs/23_validation_memo.md`](docs/23_validation_memo.md) |
| **Decision requirements** R1–R5 | [`docs/22_decision_requirements.md`](docs/22_decision_requirements.md) |
| **Evidence folder** (labelled E01–E05, raw results) | [`evidence/`](evidence/) · index: [`evidence/README.md`](evidence/README.md) |
| Synthetic-data validation | [`evidence/E01_synthetic_data.md`](evidence/E01_synthetic_data.md) |
| Reports and predictive models | [`evidence/E02_reports_and_models.md`](evidence/E02_reports_and_models.md) |
| UI, roles and Assistant | [`evidence/E03_ui_and_assistant.md`](evidence/E03_ui_and_assistant.md) |
| Task-based user test | [`evidence/E04_user_test_2026-11-15.md`](evidence/E04_user_test_2026-11-15.md) |
| Two end-to-end walkthroughs | [`evidence/E05_end_to_end_walkthroughs.md`](evidence/E05_end_to_end_walkthroughs.md) |
| Reproducible validation scripts | [`scripts/validate_week12.py`](scripts/validate_week12.py) · [`scripts/smoke_test_app.py`](scripts/smoke_test_app.py) |
| Group contributions | [`docs/18_contributions.md`](docs/18_contributions.md) |
| Plain-language glossary | [`docs/21_glossary.md`](docs/21_glossary.md) |
| 🎬 Video: 7-minute demo | [Watch on Google Drive (link added Nov 16)](#) |
| 🎬 Video: 12-minute validation-matrix walkthrough | [Watch on Google Drive (link added Nov 16)](#) |
| Live app | [https://fraud-operations-decision-intelligence-group4.streamlit.app](https://fraud-operations-decision-intelligence-group4.streamlit.app) (sign in with the account provided in the Canvas submission) |

**Decision-maker:** Fraud Operations Lead (with Fraud Analysts). **KPIs (unchanged):** KPI 1, fraud value captured
at review capacity; KPI 2, daily alert overflow.

### Key findings
| Area | Result |
|---|---|
| Synthetic data | 590,540 records: 0 duplicates, 0 missing required fields. All six alert rules recomputed independently reproduce the 23,688 alerts exactly (0 mismatches). **Partial:** 20 generated customers have more than 1,000 transactions, so the realism of the generated IDs is unvalidated. |
| Reports | Volume figures reconcile with the database on all 44 test days; the queue totals have an independent SQL recalculation (day 171: $25,997.55 under P1 at capacity 50). |
| Fraud model (KPI 1) | 32.7% of fraud dollars captured at 50 reviews a day, against 19.7% for largest-amount-first and 2.0% at random; well calibrated (ECE 0.003). **Fail:** product W (11% caught) and debit cards (30%) are under-served. |
| Volume model (KPI 2) | MAE 41.5, against 56.8 for same-as-yesterday; 91% overflow accuracy at capacity 50. **Fail:** spikes (day 171: forecast 56, actual 665); busy-day coverage 67%. |
| UI and roles | Smoke test passes on all pages; invalid inputs are blocked; analysts cannot change policy or capacity; passwords stored as salted hashes. |
| Assistant (RAG) | 4 of 4 standard questions answered from the correct sources. **Two defects found and fixed:** the glossary said "at least one rule" (alerts need two), and plural questions ("KPIs") found nothing. Both retested and passing. |

**Conclusion:** suitable for **classroom demonstration**; **not yet** for a controlled pilot (product W, spikes and
generated identities must be addressed first); **not** for operational use. See the memo for corrective actions.

### Application changes made because of validation and user feedback
Sign-in with Lead/Analyst roles · estimate-vs-actual notes · a three-line what-if takeaway with range warnings ·
a "new customer, no history" note · a capacity trade-off for the Lead · the FraudOps Assistant chatbot (Gemini with
retrieval from the project documents) and a glossary · a corrected alert definition · plural-word search.

### Reproduce the validation
```bash
pip install -r requirements.txt
python3 scripts/validate_week12.py          # read-only SQL checks -> evidence/validation_results.json
cd scripts && python3 smoke_test_app.py     # headless UI test of every page, roles and the Assistant
```
Database settings come from `.streamlit/secrets.toml` (not in Git) or the `PG*` environment variables.
The previous submission is preserved at commit `e15d032` (Week 11).

---

### Model Evaluation and Decision Support for Fraud Alert Operations

| | |
|---|---|
| **Course** | AA 5960 — Master's Research Project, MS Analytics, Saint Louis University |
| **Deliverable** | Week 11: Model Evaluation and Decision Support |
| **Team** | Bijay and Gerald |
| **Repository** | `fraud-operations-decision-intelligence` |
| **Week 10 version** | Git tag `week10-submission`; application preserved in `app/week10/app.py` |

---

## Executive summary

Fraud teams rarely lack alerts; they lack the time to review them all. This project builds a decision-support application for a **Fraud Operations Lead** whose analysts can review only a limited number of alerts per day.

Week 11 evaluates the two predictive models honestly and turns their results into decision support:

- **Evaluation design.** Data were split by time into development (60%), validation (15%) and a final test (25%). Every modeling choice was made on validation data using rules written down in advance; the final test was run **once**. Five leakage checks passed.
- **Fraud model (KPI 1).** On the final test, reviewing the 50 alerts with the highest **expected exposure** (fraud probability × amount) each day caught **32.7%** of fraud dollars, compared with **19.7%** for reviewing the largest amounts first, **15.5%** for the Week 9 rules and **2.0%** at random.
- **Alert volume model (KPI 2).** The forecast was off by **41.5 alerts per day**, compared with **56.8** for the best simple baseline, and identified overflow days at a capacity of 50 with **91%** accuracy. It under-forecasts sudden spikes.
- **One improvement per model.** Extra transaction attributes were **kept** for the fraud model (validation gain +1.6 points), though the gain did not carry over to the final test. Extra lags were **rejected** for the volume model.
- **Application.** Each page now states how far to trust the model, separates explanations of one alert from overall importance, labels which inputs the Lead controls, blocks impossible scenarios, compares baseline and scenario side by side, and summarizes the trade-off without causal claims.

---

## 1. Problem and decisions

A digital bank's alerting rules create more fraud alerts each day than its analysts can review. Alerts not reviewed within 24 hours may let fraud through, and every review costs analyst time.

| Decision | Question | Frequency |
|---|---|---|
| Alert prioritization | Which of today's alerts should the team review first? | Every shift |
| Capacity planning | How many alerts should we expect tomorrow, and will they exceed capacity? | Daily, the evening before |

The application ranks, explains and forecasts. The Lead and analysts make the decisions and record them in the application.

## 2. Key performance indicators

| KPI | Definition | Why it matters |
|---|---|---|
| **KPI 1 — Fraud value captured at capacity** | Fraud dollars in the K alerts reviewed ÷ all fraud dollars that day (K = review capacity) | How much loss the review effort prevents with the same staff |
| **KPI 2 — Daily alert overflow** | max(alerts created − review capacity, 0) | Overflow means missed deadlines and unreviewed fraud, or overtime |

## 3. Data

| Component | Type | Description |
|---|---|---|
| IEEE-CIS Fraud Detection | Sourced | 590,540 card transactions with amount, time, product code, card details, anonymized count (C1–C14) and time-delta (D) variables, email domain, and the fraud label |
| Customer, account and device identities | Generated | Created and validated in Weeks 7–8 so that customer history can be calculated |
| Behavioral features | Derived | Built in PostgreSQL from each customer's earlier transactions only (point-in-time) |
| Alert queue | Derived | 23,688 alerts over 182 simulated days from six rules that never use the fraud label |
| Decision log | Application | Analyst actions recorded in the application |

---

## 4. Evaluation design (Week 11)

### 4.1 Time split

| Period | Transactions | Days | Fraud rate | Use |
|---|---|---|---|---|
| Development | 354,324 | 1–101 | 3.38% | Fit candidate models |
| Validation | 88,581 | 101–130 | 4.04% | Make every modeling choice |
| Final test | 147,635 | 130–182 | 3.45% | Run once, after the choice was fixed |

The tool is used on future days, so a random split would let future patterns leak into training. The volume model uses the same 60/15/25 split on days.

### 4.2 Leakage checks (all passed)

History features use only earlier transactions (0 of 501,015 rows used a later one); the 24-hour count never exceeds prior history; periods do not overlap; and no single raw predictor separates fraud suspiciously well (strongest: C4, AUC 0.68). **Caveats:** Week 9 alert thresholds were percentiles of the full period, a slight look-ahead in the rule baseline and alert counts (not in the fraud model); the anonymized C and D variables are taken as recorded at transaction time, as documented by the provider.

### 4.3 Models

| | Fraud probability model (KPI 1) | Alert volume model (KPI 2) |
|---|---|---|
| Target | Whether a transaction is fraudulent | Number of alerts tomorrow |
| Algorithm | Logistic regression on standardized predictors | Poisson regression with a negative-binomial 90% range |
| Predictors | 7 behavioral features, IEEE-CIS attributes (C1–C14, D1, D10–D15, product, credit vs. debit, purchaser email, card network): 48 in total | Alerts yesterday, previous 7-day average, weekday, trend: all known the evening before |
| Uncertainty | 90% range from 30 bootstrap refits | Negative-binomial prediction interval |
| Why | Calibrated probabilities (needed for probability × amount) and exact explanations | Counts are never negative and vary more on busy days |

### 4.4 Pre-registered selection rules

- **Fraud:** keep the candidate only if validation fraud value captured at 50 reviews/day improves by at least 0.5 points.
- **Volume:** keep the candidate only if validation average error falls by at least 2%.
- Otherwise keep the simpler Week 10 specification.

---

## 5. Results (final test, run once)

### 5.1 Fraud model against baselines

| Model | PR-AUC | ROC-AUC | Brier | Fraud $ captured at 50/day |
|---|---|---|---|---|
| **Selected (48 predictors)** | **0.383** | **0.845** | **0.0261** | **32.7%** |
| Week 10 specification (29 predictors) | 0.367 | 0.840 | 0.0265 | 33.0% |
| Largest amount first | 0.038 | 0.487 | — | 19.7% |
| Week 9 rule score | 0.040 | 0.499 | — | 15.5% |
| Random | 0.035 | 0.505 | — | 2.0% |

### 5.2 KPI 1: fraud value captured by queue policy

| Policy | 25/day | 50/day | 100/day | 200/day |
|---|---|---|---|---|
| **P4 Expected exposure (probability × amount)** | **21.6%** | **32.7%** | **48.2%** | **64.5%** |
| P3 Model probability | 11.8% | 20.9% | 31.7% | 44.1% |
| P1 Largest amount | 8.9% | 19.7% | 35.2% | 48.6% |
| P2 Rule score | 8.8% | 15.5% | 24.7% | 44.4% |
| P0 Random | 1.2% | 2.0% | 4.3% | 8.4% |

### 5.3 Alert volume model and KPI 2

| Method | Average error (alerts/day) | Average % error | 90% range coverage |
|---|---|---|---|
| **Poisson regression (selected)** | **41.5** | **26.6%** | **84%** |
| Candidate with extra lags | 44.4 | 30.3% | 86% |
| Same as yesterday | 56.8 | 42.5% | — |
| Same weekday last week | 59.1 | 71.6% | — |
| Previous 7-day average | 60.7 | 57.0% | — |

| Capacity | Actual overflow days | Predicted | Accuracy | Missed | False alarms |
|---|---|---|---|---|---|
| 50 | 39 | 39 | 91% | 2 | 2 |
| 100 | 21 | 15 | 73% | 9 | 3 |
| 150 | 3 | 3 | 91% | 2 | 2 |

### 5.4 Where the models are weaker

- **Product W** (80% of test transactions): only 11% of its fraud reaches the model's top 5%, against 43% overall.
- **Debit cards** are weaker than credit cards (30% vs. 58% of fraud in the top 5%).
- **Over-prediction** for product S (9.1% predicted vs. 5.5% actual) and amounts over $1,000 (6.2% vs. 2.8%).
- **Volume spikes:** busy days are under-forecast by 56 alerts on average (day 171: 665 actual vs. 56 forecast), so test error is three times the validation error. Quiet and typical days are within about 9 alerts.

### 5.5 One improvement per model

| Model | Candidate | Validation | Decision | Final test |
|---|---|---|---|---|
| Fraud | + D10–D14, purchaser email, card network | Capture at 50: 35.5% → 37.2% | **Kept** | Better PR-AUC and Brier; capture 32.7% vs. 33.0%, so the KPI gain did not carry over |
| Volume | + alerts two days ago, same weekday last week | Error 13.8 → 13.9 | **Rejected** | Also worse (44.4 vs. 41.5) |

The fraud model was not switched back after the test, because that would be tuning on the test.

---

## 6. The application

| Page | Purpose |
|---|---|
| **Alert queue** | Today's alerts ranked by the chosen policy; capacity warning; policy comparison; volume trends; team performance |
| **Alert investigation** | Rules fired and customer history; trust box and explanation of this alert; what-if analysis; decision recording |
| **Fraud risk model** | Trust box, model card with variable roles, KPI 1, baselines, calibration, weak segments, overall importance, Week 11 evaluation details |
| **Alert volume forecast** | Trust box, model card, forecast vs. actual with 90% range, KPI 2, weak segments, overall importance, staffing what-if |

**Week 11 decision-support features**

| Requirement | Implementation |
|---|---|
| Performance and limits in plain language | "How much to trust" boxes built from the final-test results |
| Local vs. global explanations | "This alert only" contribution chart on the investigation page; overall importance on the model pages; both labeled as associations, not causes |
| Controllable vs. fixed variables | What-if inputs grouped as ① scenario inputs or decision lever, ② fixed characteristics or external conditions, ③ recorded attributes or calendar |
| Input checks and ranges | Impossible combinations are blocked; values outside the 1st–99th training percentile trigger a warning |
| Side-by-side comparison | Baseline vs. scenario table: inputs, probability, range, exposure, queue rank, inside capacity |
| Summary with trade-offs | Inputs, comparison, trade-off (alert displaced, or overflow saved per extra review slot), implication, limitations |

---

## 7. User test

**Status: conducted on 15 Nov 2026** with one participant outside the group ([`evidence/E04_user_test_2026-11-15.md`](evidence/E04_user_test_2026-11-15.md)). All four user rows (TEST-20, 27, 30, 31) are **Partial pass**: he chose the right first alert but by risk % only, read the largest driver as a cause, and confused forecast with actual. An earlier informal review is in [`docs/19b_user_test_findings.md`](docs/19b_user_test_findings.md).

---

## 8. Setup and reproduction

### 8.1 Requirements
- PostgreSQL 17 with database `fraud_risk_db` and user `fraud_app`
- Python 3.11 or newer, with the packages in `requirements.txt`

### 8.2 Install
```bash
cd fraud-risk-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 8.3 Build features and alerts
```bash
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/features/build_transaction_features.sql
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/alerts/build_alert_queue.sql
```

### 8.4 Evaluate and build the models (Week 11)
```bash
python3 src/modeling/week11_split_and_leakage.py            # time split and leakage checks
python3 src/modeling/evaluate_week11.py --validation-only   # model selection; no test data used
python3 src/modeling/evaluate_week11.py                     # final test once, error analysis, saves models
```
Results are written to `reports/week11/`; the final models are saved in `models/`.

### 8.5 Run
```bash
python3 scripts/smoke_test_app.py    # opens every page headlessly; should end with "ALL PAGES OK"
streamlit run app/app.py
```
The application opens at `http://localhost:8501`. If the database user has a password, run `export PGPASSWORD='...'` first.

### 8.6 Repository structure

| Path | Content |
|---|---|
| `app/app.py` | Week 11 Streamlit application (`app/week10/app.py`: Week 10 version) |
| `src/modeling/common.py` | Shared predictor preparation and feature sets |
| `src/modeling/week11_split_and_leakage.py`, `evaluate_week11.py` | Week 11 evaluation |
| `models/` | Saved models and test metrics |
| `reports/week11/` | Evaluation results (JSON and CSV) |
| `sql/` | Feature, alert and decision-log SQL |
| `scripts/` | App smoke test and app patches |
| `docs/` | Report, user-test materials, contributions |

---

## 9. Data access

The raw IEEE-CIS files are not redistributed, because the Kaggle competition's rules limit redistribution. Authorized users can download them from the IEEE-CIS Fraud Detection competition on Kaggle and load them into PostgreSQL; the generated and derived tables are then rebuilt with the SQL in `sql/`.

---

## 10. Limitations

1. Results describe a simulated setting on one public dataset with generated identities, not a real bank.
2. Fraud labels here are final; in real operations they arrive with delay.
3. The fraud model is weak on product W, the largest segment.
4. The volume model cannot anticipate sudden spikes and assumes the alert rules stay unchanged.
5. Explanations and what-if results are associations, not causal effects; C1–C14 are anonymized and correlated.
6. Review capacity is a user-set assumption.
7. User evidence is one task-based session with one non-expert participant (TEST-20, 27, 30, 31: Partial pass).

## 11. Next steps

Make the changes found in the user test (`evidence/E04`) and retest; fix the validation failures listed in the memo (product W, volume spikes, the amount z-score defect). Further work: segment-specific modeling for product W, same-day early signals for volume spikes, and drift monitoring.

---

## 12. Group member contributions

| Member | Contributions |
|---|---|
| **Bijay** | Defined the decision-maker, decisions and KPIs; loaded and validated the data; generated identities; built the point-in-time features and the alert rules. Built the Week 11 time split and leakage checks, ran model selection and the final test, and implemented the Week 11 application updates. Prepared the user-test protocol. |
| **Gerald** | Co-developed the predictive models and the Week 11 evaluation design and improvement candidates; reviewed the error analysis; contributed to the documentation, the evaluation report and the presentation video. |

**Use of generative AI.** Microsoft Copilot and Claude were used to plan the work, draft and debug code, draft documentation, and run a labeled pilot walkthrough of the app. All code was run against the project database, and all reported results come from the project's own scripts.

---

## Supporting documents

| Document | Content |
|---|---|
| [`docs/20_week11_evaluation_report.md`](docs/20_week11_evaluation_report.md) | Week 11 evaluation report |
| [`evidence/E04_user_test_2026-11-15.md`](evidence/E04_user_test_2026-11-15.md) | Task-based user test (15 Nov 2026) |
| [`docs/19b_user_test_findings.md`](docs/19b_user_test_findings.md) | Earlier informal review by a classmate (Week 11) |
| [`docs/18_contributions.md`](docs/18_contributions.md) | Contributions and use of generative AI |
