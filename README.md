# FraudOps Decision Intelligence
### Predictive Modeling and What-If Analysis for Fraud Alert Operations

| | |
|---|---|
| **Course** | AA 5960 — Master's Research Project, MS Analytics, Saint Louis University |
| **Deliverable** | Week 10: Predictive Modeling and What-If Analysis |
| **Team** | Bijay and Gerald |
| **Repository** | `fraud-operations-decision-intelligence` |

---

## Executive summary

Fraud teams rarely lack alerts; they lack the time to review them all. This project builds a decision-support application for a **Fraud Operations Lead** whose analysts can review only a limited number of alerts per day.

The Week 10 release adds two predictive models, each tied to a key performance indicator:

- A **fraud probability model** (logistic regression) that ranks alerts by expected fraud exposure. At 50 reviews per day it captures **33.9%** of daily fraud dollars, compared with **21.4%** for reviewing the largest amounts first and **15.5%** for the Week 9 rules — about **1.6 times more fraud dollars with the same staff**.
- An **alert volume model** (Poisson regression) that forecasts tomorrow's alerts with a 90% range. Its average error is **36 alerts per day**, compared with 50 for the best simple baseline, and its range contained the actual count on **89%** of test days.

The application explains both models at two levels — overall importance and contributions to a single prediction — and lets the Lead run what-if scenarios. After every scenario it writes a summary of the inputs, the new prediction, the change from baseline, the implications and the limitations.

---

## 1. Introduction

### 1.1 Problem

A digital bank's alerting rules create more fraud alerts each day than its analysts can review. Alerts not reviewed within 24 hours may let fraud through, while every review costs analyst time. The Lead must decide which alerts to review first and how much review capacity to plan.

### 1.2 Decision-maker and decisions

| Decision | Question | Frequency |
|---|---|---|
| Alert prioritization | Which of today's alerts should the team review first? | Every shift |
| Capacity planning | How many alerts should we expect tomorrow, and will they exceed capacity? | Daily, the evening before |

The application ranks, explains and forecasts. The Lead and analysts make the decisions and record them in the application.

---

## 2. Objectives and key performance indicators

| KPI | Definition | Why it matters |
|---|---|---|
| **KPI 1 — Fraud value captured at capacity** | Fraud dollars inside the top-K reviewed transactions ÷ all fraud dollars that day (K = review capacity) | Measures how much loss the review effort prevents with the same staff; links directly to fraud losses |
| **KPI 2 — Daily alert overflow** | max(alerts created − review capacity, 0) | Overflow means missed deadlines and unreviewed fraud, or overtime; forecasting it supports staffing and service levels |

KPI 1 concerns *using* capacity well; KPI 2 concerns *planning* it. KPI 1 is measured in dollars rather than correct predictions because a model can be accurate and still miss the large frauds that cause most of the loss.

---

## 3. Data

| Component | Type | Description |
|---|---|---|
| IEEE-CIS Fraud Detection | Sourced | 590,540 card transactions with amount, relative time, product code, card type, anonymized count (C1–C14) and time-delta (D) variables, and the fraud label |
| Customer, account and device identities | Generated | Created and validated in Weeks 7–8 so that customer history can be calculated |
| Behavioral features | Derived | Built in PostgreSQL for all transactions using only the customer's earlier transactions (point-in-time) |
| Alert queue | Derived | 23,688 alerts over 182 simulated days, created by six rules whose thresholds never use the fraud label |
| Decision log | Application | Analyst actions recorded in the application |

The behavioral features were rebuilt with SQL window functions: the full 590,540-row build takes about 4.5 seconds and matches the earlier validated version on all 10,000 sampled rows. A new-customer indicator keeps the 89,525 first transactions instead of dropping them.

---

## 4. Methodology

### 4.1 Fraud probability model (KPI 1)

| Element | Choice |
|---|---|
| Target | Whether a transaction is fraudulent |
| Predictors | 7 behavioral features (amount, hours since previous transaction, transactions in prior 24h, customer's 30-day average, amount z-score, prior transaction count, new-customer flag) and IEEE-CIS attributes recorded with the transaction (C1–C14, D1, D15, product code, credit vs. debit) |
| Algorithm | Logistic regression on standardized predictors |
| Rationale | Produces probabilities that can be checked for calibration, needed for expected exposure = probability × amount; every prediction can be explained exactly; fast enough to refit 30 times for uncertainty ranges |
| Comparisons | Behavior-only model (Experiment A) and gradient boosting (accuracy benchmark) |
| Validation | Chronological: train on the earliest 70% of time (413,378 transactions), test on the latest 30% (177,162) |

### 4.2 Alert volume model (KPI 2)

| Element | Choice |
|---|---|
| Target | Number of alerts tomorrow |
| Predictors | Alerts yesterday, average alerts over the previous 7 days, simulated weekday, trend — all known the evening before |
| Algorithm | Poisson regression with a negative-binomial 90% prediction range |
| Rationale | Counts are never negative and vary more on busy days; measured variance was about 7.6 × the mean, so the negative binomial gives an honest range |
| Validation | Train on days 8–129, test one day ahead on days 130–182, against "same as yesterday" and "7-day average" baselines |

### 4.3 Explanations

Both models are linear on their link scale, so each predictor's contribution to a prediction is exact:

```
contribution of predictor j = coefficient_j × (value_j − training average_j)
```

For linear models these contributions equal SHAP values. The application shows **overall importance** (average contributions across the test period) separately from **contributions to a single prediction**, and states that both describe associations, not causes.

---

## 5. Results

### 5.1 Fraud model — predictive performance (test period)

| Model | PR-AUC | ROC-AUC | Brier |
|---|---|---|---|
| **Logistic regression (selected)** | **0.393** | **0.842** | **0.0258** |
| Behavior features only | 0.060 | 0.637 | 0.0331 |
| Gradient boosting (benchmark) | 0.469 | 0.878 | 0.0239 |
| Week 9 rule score | 0.041 | 0.507 | — |

The test fraud rate is 3.46%, which equals the PR-AUC of a random ranking.

### 5.2 KPI 1 — fraud value captured (average per test day)

| Policy | K = 25 | K = 50 | K = 100 | K = 200 |
|---|---|---|---|---|
| Random | 0.7% | 1.3% | 3.6% | 8.0% |
| Largest amount | 10.2% | 21.4% | 36.1% | 49.3% |
| Rule risk score | 9.4% | 15.5% | 25.7% | 45.8% |
| Model probability | 11.3% | 20.5% | 31.6% | 42.0% |
| **Expected exposure** | **19.9%** | **33.9%** | **49.2%** | **65.0%** |

### 5.3 Alert volume model and KPI 2 (test days)

| Method | Average error | Average % error |
|---|---|---|
| **Poisson regression (selected)** | **36.1 alerts** | **23.9%** |
| Same as yesterday | 50.3 alerts | 39.1% |
| Previous 7-day average | 51.7 alerts | 49.0% |

| Capacity | Actual overflow days | Predicted overflow days | Overflow-day accuracy |
|---|---|---|---|
| 50 | 48 | 47 | 91% |
| 100 | 22 | 14 | 74% |
| 150 | 3 | 3 | 93% |

### 5.4 Key findings

1. Behavioral features alone carry little fraud signal; adding IEEE-CIS source attributes raised PR-AUC from 0.06 to 0.39.
2. Ranking by expected exposure beats ranking by probability alone on the dollar-based KPI, because large frauds dominate losses.
3. Logistic regression gives up some accuracy compared with gradient boosting, in exchange for exact, readable explanations.
4. Yesterday's alert volume is the strongest driver of tomorrow's forecast.

---

## 6. The application

| Page | Purpose |
|---|---|
| **Alert queue** | Today's alerts ranked by the chosen policy; capacity warning; policy comparison; volume trends; team performance |
| **Alert investigation** | One alert: rules fired, customer history, model explanation, what-if analysis with automatic summary, decision recording |
| **Fraud risk model** | KPI 1, model card, test performance, calibration, overall predictor importance |
| **Alert volume forecast** | KPI 2, forecast vs. actual with 90% range, overall importance, day forecast with contributions, what-if analysis with automatic summary |

A shared **Decision settings** toolbar (simulated day, queue policy, review capacity) applies to every page. Each what-if summary has five parts: inputs, updated prediction, change from baseline, implication, and limitations. Results are presented as model-based scenarios, not guaranteed real-world effects.

---

## 7. Setup and reproduction

### 7.1 Requirements

- PostgreSQL 17 with database `fraud_risk_db` and user `fraud_app`
- Python 3.11 or newer
- Python packages listed in `requirements.txt`

### 7.2 Install

```bash
cd fraud-risk-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 7.3 Build features, alerts and models (in this order)

```bash
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/features/build_transaction_features.sql
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/features/validate_transaction_features.sql
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/alerts/build_alert_queue.sql
psql -U fraud_app -d fraud_risk_db -h localhost -f sql/alerts/summarize_alert_queue.sql
python3 src/modeling/train_fraud_model.py
python3 src/modeling/train_alert_volume_model.py
```

Trained models are committed in `models/`, so the last two steps can be skipped if the database matches.

### 7.4 Run

```bash
source .venv/bin/activate
streamlit run app/app.py
```

The application opens at `http://localhost:8501`. If the database user has a password, run `export PGPASSWORD='...'` first.

### 7.5 Repository structure

| Path | Content |
|---|---|
| `app/app.py` | Streamlit application |
| `.streamlit/config.toml` | Theme |
| `src/modeling/` | Shared predictor preparation (`common.py`) and the two training scripts |
| `models/` | Saved models and test metrics |
| `sql/features/`, `sql/alerts/`, `sql/ops/` | Feature, alert and decision-log SQL |
| `scripts/export_week10_data.sh` | Exports the shareable data tables |
| `docs/` | Project documentation |
| `requirements.txt` | Python dependencies |

---

## 8. Data access

The raw IEEE-CIS files are not redistributed, because the Kaggle competition's rules limit redistribution. Generated and derived tables are exported by `scripts/export_week10_data.sh` and shared with the instructor through the submission folder. Steps for authorized users to obtain the source data are in [`docs/DATA_ACCESS.md`](docs/DATA_ACCESS.md).

---

## 9. Limitations

1. Results describe a simulated environment built on one public dataset with generated identities, not a real bank.
2. The C and D variables are anonymized, so their business meaning cannot be interpreted precisely.
3. Gradient boosting was more accurate; logistic regression was chosen for explainability.
4. Importance, contributions and what-if results are associations, not causal effects.
5. The fraud model's range covers coefficient uncertainty only; the volume range covered 89% of test days.
6. Review capacity is a user-set assumption, and team metrics come only from decisions recorded in the application.

---

## 10. Conclusion and next steps

The application now supports both of the Lead's decisions with validated predictive models: ranking by expected exposure captures substantially more fraud dollars than the existing alternatives, and the volume forecast anticipates overflow better than simple baselines. Every prediction is explained, and scenarios are summarized with their limitations.

Week 11 will evaluate decision support more fully: comparing queue policies across all test days and capacities, adding clearly labelled cost assumptions, and monitoring drift in features and model performance.

---

## 11. Group member contributions

| Member | Contributions |
|---|---|
| **Bijay** | Defined the decision-maker, decisions and KPIs. Loaded and validated the IEEE-CIS data in PostgreSQL, generated and validated customer, account and device identities, and built the point-in-time features. Designed the six label-free alert rules and the alert queue. Developed the Streamlit application: alert queue, alert investigation, model pages, explanations, what-if analysis, automatic summaries and decision log. Co-developed the predictive models and the documentation with Gerald. |
| **Gerald** | Co-developed and evaluated the two predictive models: the fraud probability model for KPI 1 and the alert volume model for KPI 2, including the comparisons with the behavior-only model, gradient boosting and simple baselines. Co-wrote the project documentation and the presentation, and contributed to the demonstration video. |

**Use of generative AI.** Microsoft Copilot and Claude were used to plan the work, draft and debug SQL and Python code, and draft documentation. All code was run and checked against the project database, and all reported results come from the project's own scripts. Links to the AI conversations are provided with the submission.

---

## Supporting documents

| Document | Content |
|---|---|
| [`docs/15_application_guide.md`](docs/15_application_guide.md) | Full application guide |
| [`docs/16_week10_presentation_script.md`](docs/16_week10_presentation_script.md) | 7-minute video script |
| [`docs/17_week10_progress_report.md`](docs/17_week10_progress_report.md) | Progress report |
| [`docs/18_contributions.md`](docs/18_contributions.md) | Contributions and use of generative AI |
| [`docs/DATA_ACCESS.md`](docs/DATA_ACCESS.md) | Data sharing and restrictions |
