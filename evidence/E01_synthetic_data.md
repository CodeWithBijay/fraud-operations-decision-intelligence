# E01 — Synthetic Data Validation (TEST-01 to TEST-06)

Database: Neon project `fraud_decision_intelligence`, tables `transaction_features` (590,540 rows), `alert_queue`
(23,688), `transaction` (23,688 model-input rows, alerts only), `alert_rule_config`. Run: 2026-11-15, read-only, on Neon; reproduced on the local source database the same evening with identical results.
Reproduce: `python3 scripts/validate_week12.py` → `evidence/validation_results.json`.

## A. Generation and provenance
- **Source:** IEEE-CIS Fraud Detection `train_transaction.csv` and `train_identity.csv` (public Kaggle competition
  data; competition-use terms). Empirical fields (amount, time, product, card, IEEE C/D counts) are unchanged.
- **Generated fields:** CustomerID, AccountID and DeviceID, created by deterministic grouping rules
  (`docs/04_data_generation.md` §7): CustomerID = `card1 + addr1 + P_emaildomain`, with documented fallbacks;
  AccountID nests card attributes within a customer; DeviceID nests `DeviceInfo`/identity fields within a customer.
  The rules are deterministic (no random seed), so a rerun on the same source gives the same IDs. Fraud labels were
  never used in generation (`docs/04` §7.1, §7.2).
- **Derived fields** (point-in-time, prior data only): prior transaction count, hours since the previous transaction,
  24-hour count, 30-day mean, standard deviation and z-score, and the cold-start flag (`docs/06`, `docs/07`).
- **Simulated time:** `sim_day = floor(TransactionDT / 86,400)`, giving days 1–182.
- **Alerts:** six label-free rules (`alert_rule_config`). R1 is a 24-hour count ≥ 8 (95th percentile); R2 is an
  amount z-score ≥ 3; R3 is hours since the previous transaction ≤ 0.0439 (5th percentile); R4 is a new customer;
  R5 is an amount ≥ $445 (95th percentile); R6 is the first use of a device by an existing customer. **An alert is
  raised when at least two rules fire.**
- **Use restrictions:** IEEE-CIS is released for the Kaggle competition. Its identity fields are anonymized, but it
  is still real transaction data, so the database is not published, and the app shows generated IDs only.

## B. Structural and logical validity
| Rule tested | Violations |
|---|---|
| Duplicate transaction IDs (590,540 rows) | 0 |
| Required fields null (customer, account, time, amount) | 0 |
| Amount ≤ 0 (range 0.251 – 31,937.39) | 0 |
| Negative counts, gaps or standard deviations | 0 |
| Cold-start flag ≠ (prior count = 0) | 0 |
| New customer with history values | 0 |
| Existing customer missing the time gap | 0 |
| 24-hour count > prior count | 0 |
| Alerts without a feature row / duplicate alerts / alerts without model inputs | 0 / 0 / 0 |
| **Customers with two "first" transactions** | **3 of 89,522** |
| Device ID missing | 471,919 (79.9%), by design: identity data exists for about 24% of IEEE-CIS transactions |

**Resolution:** the 3 customers whose first two transactions share a timestamp are left as they are and documented.
They affect at most 6 cold-start flags (0.001%) and cannot change any KPI.

## C. Alert rules recomputed independently (TEST-03)
All six flags were recomputed from the features with the stored thresholds and compared with `alert_queue`:
**0 flag mismatches, 0 risk-score mismatches; 23,688 transactions meet at least two rules, and exactly those 23,688
are alerts** (22,976 with 2 rules, 691 with 3, 21 with 4). A further 181,089 transactions meet exactly one rule and
are, correctly, not alerts.

## D. Statistical and domain plausibility (TEST-04)
- **Against the source:** amount mean 135.03 and median 68.77 match the raw IEEE-CIS audit (`docs/04` §6.5:
  135.0272 and 68.769). This confirms the data were loaded correctly. It is **not** independent evidence of
  real-world realism, because the data are the source.
- **Generated IDs:** the median customer has 2 transactions, and 42,992 customers have only one. But **20
  generated customers have more than 1,000 transactions, and one has 4,015 in 182 days**, which is implausible for a real cardholder. The grouping
  rule merges many cards that share `card1 + addr1 + email`. Velocity and z-score features, and so rules R1–R3, are
  distorted for such IDs.
- **No independent real-world reference** exists for the generated customer, account and device structure.
  **Empirical realism of the generated IDs remains unvalidated**; agreement with our own rules shows internal
  consistency only.

## E. Decision-relevant coverage (TEST-05)
- **Days:** 182, with alerts from 34 to 665 a day (median 112.5, mean 130.2). 171 days exceed a capacity of 50,
  114 exceed 100, and 44 exceed 150. Overflow is the normal condition, so both KPIs can be exercised.
- **Rare but consequential cases are present:** one extreme spike day (day 171: 665 alerts), a second spike
  (day 172: 369), 12 alerts of $5,000 or more, and new customers (89,525 cold-start transactions).
- **Subgroups in the alerts:** product W 14,605, C 5,224, R 1,912, S 1,378, H 569; debit 14,843, credit 8,780,
  card type missing 64.
- **Gaps:** there are no labels for days beyond the dataset, and no seasonality beyond 6 months (holiday peaks
  absent). There is no merchant ID, and no real analyst-capacity data (capacity is an assumption).

## F. Sensitivity to generation assumptions (TEST-06)
Total alerts when one threshold moves (baseline 23,688):

| Change | Alerts | Change |
|---|---|---|
| R1 24-hour count ≥ 7 / ≥ 9 | 24,596 / 22,951 | +3.8% / −3.1% |
| R2 z-score ≥ 2.5 | 24,871 | +5.0% |
| R5 amount ≥ $400 / ≥ $500 | 25,612 / 21,411 | +8.1% / −9.6% |

KPI 2 (overflow) scales with these totals, so reported overflow days depend on the R5 and R2 thresholds within
about ±10%. KPI 1 ranks within whatever queue exists, so it is less exposed. Re-running the fraud model under
other thresholds was **not tested**; this is listed as a retest in the matrix.

## G. Privacy
The source is public, anonymized competition data. No personal data was added: the generated IDs are hashes of
anonymized fields (for example `CUST_639C588C7FA7F0C5`). The app never sends transaction rows to the Assistant's AI
model. The Neon database is private (credentials only in Streamlit Secrets). Being synthetic or anonymized does not
make the data free to redistribute, so the database is not shared publicly.
