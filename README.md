# 17 — Progress Report (Week 10)

**Project:** FraudOps Decision Intelligence — decision support for a Fraud Operations Lead
**Course:** AA 5960 Master's Research Project, MS Analytics, Saint Louis University
**Team:** Bijay and Gerald

---

## 1. Summary

The project now has a working decision-support application backed by a validated PostgreSQL database and two predictive models. The Fraud Operations Lead can rank each day's alerts by expected fraud exposure, see how much of the queue fits inside review capacity, forecast tomorrow's alert volume, understand why each prediction was made, and test what-if scenarios with automatically written summaries.

## 2. Work completed to date

| Phase | Weeks | Outcome |
|---|---|---|
| Project definition | 1–3 | Decision-maker, problem and research questions defined; literature review completed |
| Data planning | 4–5 | Data sources, metrics and data structure specified; IEEE-CIS chosen as the empirical base with generated context |
| Interface design | 6 | Decision logic, use cases, workflow and low-fidelity wireframes |
| Data acquisition, generation and validation | 7–8 | 590,540 transactions loaded into PostgreSQL; customer, account and device identities generated and validated; point-in-time features built and validated |
| First prototype | 9 | Alert queue (23,688 alerts from six label-free rules), alert detail screen, decision log, policy comparison and team metrics |
| Predictive modeling and what-if | 10 | Two KPIs, two predictive models, explanations, what-if analysis, automatic summaries, redesigned interface |

## 3. Week 10 accomplishments

**KPIs.** (1) *Fraud value captured at capacity* — share of daily fraud dollars inside the reviewed alerts; (2) *Daily alert overflow* — alerts beyond review capacity.

**Engineering.**
- Rewrote the five behavioral features with SQL window functions: the full 590,540-row build now takes about 4.5 seconds instead of hours, and matches the earlier validated version on all 10,000 sampled rows. This removed the need for the 10,000-row modeling sample used before.
- Added a new-customer (cold-start) indicator instead of dropping 89,525 first transactions.

**Fraud model (KPI 1).** Logistic regression on behavioral and IEEE-CIS predictors, trained on the earliest 70% of time and tested on the latest 30%.

| | PR-AUC | ROC-AUC |
|---|---|---|
| Selected model | 0.393 | 0.842 |
| Behavior features only (Experiment A) | 0.060 | 0.637 |
| Gradient boosting (comparison) | 0.469 | 0.878 |
| Week 9 rules | 0.041 | 0.507 |

At 50 reviews per day, ranking by expected exposure captures **33.9%** of fraud dollars, compared with 21.4% for "largest amount first" and 15.5% for the Week 9 rules.

**Alert volume model (KPI 2).** Poisson regression with a negative-binomial 90% range. Average error 36.1 alerts per day (vs. 50.3 and 51.7 for the two simple baselines); the range contained the actual count on 89% of test days.

**Application.** Four pages (Alert queue, Alert investigation, Fraud risk model, Alert volume forecast) with overall importance and single-prediction contributions shown separately, non-causal interpretations, what-if analysis with a labelled baseline for both models, and a five-part automatic summary after every scenario. The interface was rebuilt with a top navigation bar, page banners, a shared settings toolbar and meaningful page names.

**Documentation.** Application guide (`docs/15_application_guide.md`), README with setup steps, data-access note, and the presentation script.

## 4. Findings so far

1. The behavioral features alone carry little fraud signal; the IEEE-CIS source attributes raise performance substantially (PR-AUC 0.06 → 0.39). This answers the Phase 1 question of what the generated behavioral context adds.
2. Ranking by expected exposure (probability × amount) outperforms ranking by probability alone on the dollar-based KPI, because large frauds dominate losses.
3. Logistic regression gives up some accuracy compared with gradient boosting, in exchange for exact, readable explanations of every prediction.

## 5. Issues and how they were handled

| Issue | Handling |
|---|---|
| Feature queries too slow for the full dataset | Rewritten with window functions and materialized as a table |
| First fraud model weaker than a simple amount rule on KPI 1 | Added IEEE-CIS source predictors; documented as Experiment A vs. B |
| Week 9 and Week 10 submitted late | Work is now on schedule for Week 11 |
| Source-data terms limit redistribution | Raw files not shared; generated and derived tables shared with the instructor; access steps documented |

## 6. Next steps (Week 11)

- Evaluate decision support: compare queue policies over all test days, with sensitivity to capacity.
- Add simple cost assumptions (review cost, loss given fraud) as clearly labelled scenario parameters.
- Monitor drift: compare feature distributions and model performance over time.
- Optionally deploy a demonstration version with exported data.
