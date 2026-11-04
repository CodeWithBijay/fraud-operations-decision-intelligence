# 19b — User Test Findings (Week 11)

**Participant:** P1, a classmate outside the project team, acting in the user role of a Fraud Operations analyst.
**Format:** informal, self-guided review of the live app, followed by written feedback. The participant explored the
app freely; the five tasks in the protocol (`docs/19_user_test_protocol.md`) were not run one by one, and no timings or
ratings were recorded.
**Date:** November 2026.

## What the participant did
- Reviewed the alert queue and how alerts are prioritized by fraud risk and expected exposure.
- Opened an alert on the investigation page (reasons, customer history, model prediction).
- Ran a what-if scenario: transaction amount about $2,080 → $5,000. Fraud probability rose from 34.7% to 41.7%; the
  alert stayed ranked #1; the app warned that $5,000 was outside the model's usual training range.

## What worked
- The app focuses on decisions, not only predictions.
- The alert queue was easy to understand; the prioritization was clear.
- The investigation page explained why a transaction was flagged.
- The side-by-side what-if comparison and the out-of-range warning were useful.

## Issues found and planned changes

| # | Finding | Severity | Planned change |
|---|---|---|---|
| 1 | Pages feel overwhelming, especially model evaluation | Medium | Key results first; technical tables in expandable sections |
| 2 | Terms such as PR-AUC, Brier score, calibration and expected exposure are not beginner-friendly | Medium | Plain-language meaning next to each term |
| 3 | What-if summary is long | Medium | Short takeaway at the top: what changed, whether the action changed, what to do |
| 4 | Estimated fraud $ covered (Queue page) vs. actual fraud value captured (model page) looked contradictory | High | Note explaining estimate for today's alerts vs. actual final-test result |
| 5 | Capacity slider gives no trade-off guidance | Medium | Show the extra coverage from more review capacity |
| 6 | Zeros in history fields for a new customer were ambiguous | Medium | Show "new customer, no history" and lock those inputs |
| 7 | Out-of-range warning is easy to miss near the final result | Medium | Repeat the warning in the takeaway |

## Status
Changes made because of this test are listed in the commit history and in section 7 of the Week 11 report.
Items not yet changed remain listed above as planned.
