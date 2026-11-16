# E05 — End-to-End Decision Walkthroughs

Each walkthrough follows one decision: decision need → input data → model output → UI presentation → user
interpretation → action, marking every link as **verified**, **partly verified** or **not evidenced**. Matrix rows:
TEST-28 (routine queue decision) and TEST-29 (spike planning).

**How the evidence was produced.** The 104 production alerts for day 160 (all columns of `alert_queue`,
`transaction` and `transaction_features`) were copied read-only from Neon into a local test database. The
unmodified app (commit `6c74225`) was rendered headlessly with Streamlit AppTest, signed in as the Lead, with the
defaults P4 and capacity 50. Every value below was read from what the app rendered (`E05_day160_trace.json`).

## Walkthrough 1: routine queue decision (day 160)
"Routine" (the course's *typical* scenario) means an ordinary test-period day with no spike: 104 alerts, close to the
median of 112.5 across 182 days, with capacity at its usual 50. It is one example, not proof of all typical days.
**Matrix rows used:** TEST-03 (rules), TEST-07/08 (display), TEST-12 (estimate note), TEST-13 (policy vs. baselines),
TEST-14 (calibration), TEST-35/36 (report checks), TEST-32 (decision log), TEST-20 (user interpretation, pending), TEST-28.

| Link | What happened | Status |
|---|---|---|
| 1. Decision need | The Fraud Ops Lead must choose which day-160 alerts the team reviews with 50 slots (R1). | — |
| 2. Input data | 104 alerts, each produced by ≥2 of the 6 rules. Followed alert: **Txn 3513661**, customer `CUST_E6D31F05EC50923E`, **$1,600.00**, at 04:09; rules fired: **Amount spike (z ≥ 3)** and **Large amount (≥ $445)**. | Verified: rules recomputed with 0 mismatches (TEST-03) |
| 3. Model output | Fraud probability **32.7%** (90% model range 28.7%–35.5%); expected exposure **$522.80** = 0.327 × $1,600. | Verified that the app computes it; the outcome (fraud or not) is **not evidenced**, because labels are not in the app database |
| 4. Ranking and capacity | Under P4 the alert is **#1 of 104**. #2 is a $600 alert at **72.5%** risk (exposure $435.05): P4 puts the larger expected loss first, even though #2 is more likely to be fraud. The capacity cut falls between **#50** (Txn 3514340, $511.95, 2.8%, exposure $14.53) and **#51** (Txn 3515630, $202.88, 7.1%, exposure $14.32). The boundary is a near-tie of $0.21. | Verified (rendered queue table) |
| 5. UI presentation | Banner: "**Review the top 50 alerts today** · 54 alerts ($22,801) will not be reviewed · Amount in review **$53,519** · Est. fraud $ covered **92%** · Not reviewed 54". Note: "Est. fraud $ covered is the model's own estimate … the tested KPI … is lower: about **33%** at 50 reviews a day". Lead's trade-off: "+50 reviews would raise estimated fraud covered by **8 points**". "Review these first" lists #1 Txn 3513661 with Open. Investigation page: "#1 of 104", the two rules ticked, and "transactions scored at a similar level turned out to be fraud **19.3%** of the time". | Verified that the UI computes and presents these values (headless render). Confirmed on screen 2026-11-15 (`evidence/screenshots/e05_day160_queue.png`) |
| 6. Two measures that conflict | The 92% is an estimate over **today's alerts only**, built from probabilities. The 33% is the **tested share of all fraud dollars** over 53 past days. They are different quantities, and the 92% is optimistic: the app itself shows that alerts scored like #1 (32.7%) were fraud 19.3% of the time. | Verified (both shown, with the note) |
| 7. User interpretation | Whether a Lead reads 92% as an estimate rather than a promise, and understands why #1 beats the 72.5% alert. | **Not evidenced** until the task-based test (TEST-20) |
| 8. Action (review workflow, not an endorsement of P4) | (a) Assign alerts #1–#50 in rank order. (b) Treat 92% as the model's view of today's queue and plan on the tested ~33% of all fraud dollars. (c) Because #50 and #51 differ by $0.21, let analysts with spare time take #51–#55 next. (d) If the Lead prefers likelihood over loss, switching to P3 changes 16 of the 50 reviewed alerts (P1 also changes 16). (e) Each analyst opens the alert, checks the rules and history, and records a decision. The model ranks; it does not decide. | Recommended workflow; outcome not evidenced |

**Comparison with the earlier model.** In Week 11, the selected model (32.7% at 50) and the Week 10 specification
(33.0%) were both scored by `src/modeling/evaluate_week11.py` on the **same 53 test days with the same
denominator**, so the figures are comparable. The 0.3-point difference is small next to day-to-day variation
(single test days go as low as 3.6%). It is reported as "no KPI gain", not as a loss or a win, and its statistical
significance was not tested.

**Handoff limit (R3, not part of the Lead's decision):** if an analyst opens a **new-customer** alert (#48,
Txn 3513305), the history fields are empty by design and the app now says so. Investigation quality for new
customers is outside this walkthrough (TEST-27).

**Conclusion (TEST-28):** **supports the decision only under stated conditions.** The data, ranking, capacity cut
and display were verified for a real day. The actual fraud outcome of the reviewed alerts, and users' interpretation
of the 92% estimate, are **not evidenced**. The evidence supports a *retrospective* comparison of policies (P4
caught the most fraud dollars at 50 in the final test), not a guarantee for any single day.

## Walkthrough 2: spike planning (day 170 → day 171)
Challenging because it combines a **boundary condition** (665 alerts, 13× capacity), **insufficient evidence** (nothing in
the history foresees it) and **conflicting objectives** (overtime cost vs. unreviewed fraud).
**Matrix rows used:** TEST-17 (volume model), TEST-18 (busy-day/spike failure), TEST-08 (day-171 display), TEST-30 (user
interpretation, pending), TEST-29.

| Link | What happened | Status |
|---|---|---|
| 1. Decision need | On day 170 the Lead decides staffing for day 171 (R2). Conflicting objectives: avoid overtime cost vs. avoid unreviewed fraud. | — |
| 2. Input data | Day 170 had 84 alerts; days 163–169 averaged 154 (including a 340-alert spike on day 164, which faded within a day); nothing signals a spike on day 171. | Verified (database daily counts) |
| 3. Model output | Forecast for day 171: **56 alerts (90% range 27–92)**. | Verified (`alert_volume_metrics.json` test predictions) |
| 4. Reality | **665 alerts** arrived on day 171, 12× the forecast and 7× the upper bound. | Verified (database) |
| 5. UI presentation | The Volume page would show 56 against capacity 50 (overflow likely but small), the range, and the busy-day/spike limitation note. | Verified on screen (`evidence/screenshots/e05_day170_volume.png`) |
| 6. User interpretation | A Lead trusting the forecast plans near-normal staffing. | Not evidenced |
| 7. Consequence and action | At capacity 50, 615 alerts (92%) go unreviewed on day 171. Even planning to the upper bound (92) leaves 573 unreviewed. The safe action is to use outside signals (campaigns, outages, attack reports). On day 171 itself the queue still ranks the 665 alerts by expected exposure (P1 top 50 = $25,997.55 of $93,329.24). | Verified figures; action is a recommendation |

**Conclusion (TEST-29):** **does not yet support** the staffing decision for sudden spikes. Corrective action: an
intraday early-warning signal and an upper-bound planning rule (TEST-18).
