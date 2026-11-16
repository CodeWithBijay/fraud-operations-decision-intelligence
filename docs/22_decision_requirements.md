# 22 — Decision-Support Requirements (Weeks 12–13)

**Intended decision-maker:** the Fraud Operations Lead of a card-issuing bank's alert-review team, who sets the
daily review policy and capacity, plus the Fraud Analysts who work the queue under that policy.
**Requirement sources:** no practising fraud-operations lead was available. Requirements therefore come from
(a) the project team's assumptions, documented since Week 1; (b) the course brief; (c) one knowledgeable
substitute: a classmate outside the team who tested the app as an analyst (`docs/19b`, `evidence/E04`); and
(d) the public IEEE-CIS dataset documentation (`docs/04`). Each matrix row names its source.
**KPIs (unchanged since Week 9):** KPI 1, fraud value captured at review capacity; KPI 2, daily alert overflow
above capacity. Definitions are in `docs/21_glossary.md`.
**Acceptance criteria** for the model rows were pre-registered in Week 11. The Week 12 data, report and UI criteria were written on 15 Nov in the same working session as the checks, some after earlier results were known; the matrix marks these rows, and no criterion was changed or lowered after testing. The model thresholds (KPI 1 must
beat every baseline; volume MAE must beat the naive forecasts) were pre-registered in Week 11.

## R1 — Prioritize today's alerts within review capacity (KPI 1)
- **Decision, frequency, constraints:** every morning, decide which of the day's alerts to review first.
  The volume averages 130 alerts a day (34 to 665) against a capacity of about 50 reviews, so most days overflow.
- **Information needed:** the day's alerts; each alert's fraud probability, amount and expected exposure
  (probability × amount); the queue policy; capacity; the alert reasons.
- **How the app should help:** rank the queue by a chosen policy, show what fits inside capacity, state today's
  decision in one line, list the alerts to review first, and compare policies.
- **Consequence of bad information:** fraud dollars go unreviewed (direct loss), or analysts spend capacity on
  low-value alerts. An overstated coverage figure could lead the Lead to under-staff.
- **Acceptance criteria:** (1) every alert is produced by the documented rules (0 mismatches); (2) the displayed
  queue totals equal an independent recalculation; (3) on the final test, the default policy captures more fraud
  value at 50 reviews a day than every baseline; (4) a user outside the team identifies the alert to review first
  and why, with no more than a hint.

## R2 — Plan capacity for tomorrow (KPI 2)
- **Decision, frequency, constraints:** each afternoon, decide whether tomorrow needs extra reviewers or overtime.
  Staff must be arranged a day ahead, and spikes (for example day 171) can arrive without warning.
- **Information needed:** tomorrow's forecast alert count with an uncertainty range, capacity, and overflow risk.
- **How the app should help:** show the forecast against capacity, with a 90% range and a plain overflow verdict,
  and say when the forecast is unreliable (busy days, spikes).
- **Consequence of bad information:** under-forecasting leaves alerts unreviewed; over-forecasting wastes staff cost.
- **Acceptance criteria:** (1) the forecast MAE is below every naive baseline on the test days; (2) the 90% range
  covers at least 80% of test days; (3) overflow days at capacity 50 are classified with at least 85% accuracy;
  (4) the page states the busy-day bias and the spike limitation.

## R3 — Investigate one alert and test a what-if before deciding (KPI 1)
- **Decision, frequency, constraints:** for each reviewed alert (about 50 a day), decide whether to confirm,
  escalate or clear it, in a few minutes.
- **Information needed:** the alert's rules, its model drivers, the customer's history, and a scenario comparison.
- **How the app should help:** explain the score without implying cause; separate controllable inputs from fixed
  conditions; block impossible inputs; warn about values outside the training range; compare baseline and scenario;
  give a short takeaway.
- **Consequence of bad information:** treating associations as causes, or trusting extrapolated scenarios, could
  wrongly clear fraud or wrongly block a customer.
- **Acceptance criteria:** (1) invalid inputs are blocked and out-of-range inputs warned (normal, boundary and
  invalid cases); (2) the takeaway states the probability change, the rank change and any warning; (3) the
  explanations carry non-causal wording; (4) a user outside the team runs a what-if and states whether the action
  changes.

## R4 — Understand the numbers, terms and limits (supports R1–R3)
- **Decision, frequency, constraints:** as needed; users are not analytics specialists.
- **Information needed:** plain-language definitions; estimate vs. actual; known weak spots.
- **How the app should help:** a glossary and an Assistant chatbot that answers only from the project's documents,
  with sources; notes on the pages where confusion was observed.
- **Consequence of bad information:** misread metrics lead to over-trust (for example reading 72% estimated
  coverage as the tested 33%).
- **Acceptance criteria:** (1) for the 4 standard questions, the correct glossary or report section is among the
  top 4 sources; (2) the answers contain no figure that contradicts the source documents; (3) the queue page
  explains estimate vs. actual.

## R5 — Role-appropriate access (supports R1–R2)
- **Decision:** only the Lead changes the policy and capacity; analysts work the queue.
- **Consequence:** an analyst changing capacity could silently change the whole team's priorities.
- **Acceptance criteria:** (1) unauthenticated users see only the sign-in page; (2) a wrong password is rejected;
  (3) the Analyst role sees only the Queue, Investigate and Assistant pages, with policy and capacity locked;
  (4) passwords are stored only as salted hashes.
