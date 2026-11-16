# 21 — Plain-Language Glossary

Short explanations of the terms used in the FraudOps app, written for a Fraud Operations Lead or analyst
without an analytics background. Numbers come from the Week 11 final test (`docs/20_week11_evaluation_report.md`).

## Alert
A transaction flagged because at least two of six label-free alert rules fired at once: high 24-hour velocity, amount spike, rapid
repeat, new customer, large amount, and new device. A transaction that trips only one rule is not an alert. An alert is a reason to look, not proof of fraud.

## Review capacity
How many alerts the analyst team can review in one day. The Fraud Ops Lead sets it; the default is 50. Alerts
beyond capacity wait or expire.

## Fraud probability
The fraud model's estimate of the chance that a transaction is fraud, for example 34.7%. It ranks cases for review;
it does not prove fraud. Most high-probability alerts are still legitimate.

## Expected exposure
Fraud probability multiplied by the transaction amount. A 35% chance on a $2,080 payment is about $720 of expected
fraud. The default queue policy (P4) reviews the alerts with the highest expected exposure first.

## Queue policies (P0 to P4)
Ways of ordering the alert queue. P0 is random, P1 is largest amount first, P2 is the alert-rule score, P3 is the
model's fraud probability, and P4 is expected exposure (probability times amount). P4 performed best in testing.

## KPIs (key performance indicators)
The two measures the project uses to judge whether the tool helps the Fraud Ops Lead. KPI 1 is fraud value captured
at capacity: the share of a day's real fraud dollars inside the alerts the team reviews (32.7% at 50 reviews a day
in the final test). KPI 2 is daily alert overflow: alerts above review capacity, forecast by the volume model so the
Lead can plan staff.

## KPI 1: fraud value captured at capacity
The share of a day's real fraud dollars that falls inside the alerts the team reviews. In the final test, reviewing
50 alerts a day under P4 caught 32.7% of fraud dollars, compared with 19.7% for largest amount first, 15.5% for the
rule score, and 2.0% at random. At 25, 100 and 200 reviews a day, P4 caught 21.6%, 48.2% and 64.5%.

## KPI 2: daily alert overflow
The number of alerts above review capacity on a day. The volume model forecasts tomorrow's alert count so the Lead
can plan staff. In the final test it was off by 41.5 alerts a day on average and correctly flagged overflow days
91% of the time at a capacity of 50 and 73% at a capacity of 100.

## Estimate vs. actual
The Alert queue page shows "Est. fraud $ covered": the model's own estimate, counting only today's alerts. The
Fraud risk model page shows KPI 1: real fraud dollars caught in the final test, counting all of a day's
transactions. They measure different things, so the estimate (for example 72%) is usually higher than the tested
result (about 33% at 50 reviews a day).

## PR-AUC (precision-recall area under the curve)
A score from 0 to 1 for how well the model puts real fraud at the top of its list. Random ordering scores about the
fraud rate (about 0.035 here). The selected fraud model scored 0.383, about ten times better than random.

## ROC-AUC
A score from 0.5 (random) to 1 (perfect) for how well the model separates fraud from non-fraud. The selected model
scored 0.845. Because fraud is rare, PR-AUC is the more useful of the two here.

## Brier score
The average squared gap between the predicted probability and what actually happened (0 or 1). Lower is better.
The selected model scored 0.0261. It matters because expected exposure uses the probability directly.

## Calibration
Whether the predicted probabilities match reality: of transactions scored around 20%, about 20% should turn out to
be fraud. Good calibration makes expected exposure trustworthy.

## 90% range
The interval shown around a prediction. For the fraud model it reflects uncertainty in the model's coefficients;
for the volume forecast it is the range expected to contain the actual alert count about 90% of the time (it did
on 84% of test days).

## Baseline
A simple method the models are compared against, such as random order, largest amount first, or "same as
yesterday" for the volume forecast. A model is only useful if it beats its baselines.

## What-if scenario
A change to one alert's inputs (for example a larger amount) to see how the model's estimate and the queue rank
respond. It shows how the model reacts, not what would really happen, and it does not prove cause.

## Weak spots
The fraud model is weaker on product code W (about 80% of transactions) and on debit cards. The volume model cannot
anticipate sudden spikes (day 171: 665 alerts against a forecast of 56) and under-forecasts busy days by about 56
alerts, so planners should use the upper end of the range on busy days.

## Roles
The Fraud Ops Lead sees every page and sets the queue policy and review capacity. A Fraud Analyst works the queue,
investigates alerts and records decisions. These are role views for a classroom demonstration, not bank-grade access
control.

## Data
Public IEEE-CIS transactions with generated customer, account and device identities. Results describe this
simulated setting, not proven performance at a real bank. Fraud labels are final here but arrive late in real life.
