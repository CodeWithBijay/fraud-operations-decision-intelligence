# E05 — End-to-End Decision Walkthroughs

Traced as: decision need → input data → report or model output → UI presentation → user interpretation →
proposed action and limits. Matrix rows: TEST-28 (typical) and TEST-29 (challenging).

## Scenario 1: a typical day (day 160, test period)
| Step | Trace |
|---|---|
| Decision need | The Lead must review the right ~50 of today's alerts and know whether tomorrow overflows (R1, R2). |
| Input data | 104 alerts on day 160 in `alert_queue`, all produced by the documented two-rule logic (TEST-03: 0 mismatches). |
| Model output | Fraud probability per alert (logistic regression); expected exposure = p × amount; tomorrow's (day 161) forecast 96 (range 57–143). |
| UI presentation | Queue: "Review the top 50 alerts today", 54 not reviewed, estimated coverage with the estimate-vs-actual note, "Review these first" with Open. Lead: capacity trade-off line. Volume page: 96 against capacity 50, with range. |
| User interpretation | The analyst works the top 50 by expected exposure and opens #1 to see the rules and drivers. The Lead sees that day 161 is very likely to overflow at 50 (lower bound 57 > 50). |
| Action and limits | Review the top 50; plan at least the current staffing for day 161 (actual: 102, inside the range). In testing, this policy caught about 33% of a day's fraud dollars at 50 reviews, against 20% for largest-amount-first (TEST-13). It is weaker if the day's fraud is mostly product W or debit cards. |
| **Conclusion** | **Supports the decision under stated conditions:** within the simulated IEEE-CIS setting, with capacity as an assumption, and with the product-W and debit weakness disclosed. |

## Scenario 2: a challenging day (planning on day 170 for the spike on day 171)
| Step | Trace |
|---|---|
| Decision need | On day 170 the Lead decides staffing for day 171 (R2). Conflicting objectives: avoid overtime cost vs. avoid unreviewed fraud. |
| Input data | Day 170 had 84 alerts; the history shows no warning of the spike. |
| Model output | Forecast for day 171: **56 (range 27–92)**. Actual: **665 alerts**, 12× the forecast and far outside the range (TEST-18). |
| UI presentation | The Volume page shows a forecast just above capacity 50, a range reaching 92, and the busy-day/spike limitation note. The queue on day 171 then shows 615 not reviewed. |
| User interpretation | A Lead trusting the point forecast would plan near-normal staffing, so on day 171 about 92% of alerts would go unreviewed at capacity 50. Even the upper bound (92) would leave 573 unreviewed. |
| Action and limits | The tool cannot anticipate this spike; the Lead needs outside signals (campaigns, outages, known attacks). On the spike day itself, the queue still ranks the 665 alerts by expected exposure, so the 50 reviews go to the highest-value alerts. Day 182 is another hard case: only 3.6% of fraud value captured at 50. |
| **Conclusion** | **Does not yet support the staffing decision for sudden spikes.** The queue still supports prioritization within capacity on the spike day. Corrective action: an intraday early-warning signal (alerts in the first hours), plus a rule to plan to the upper bound on volatile weeks (matrix TEST-18). |
