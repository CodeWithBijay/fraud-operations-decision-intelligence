# Feature Validation

## HoursSincePreviousTxn

Status: VALIDATED

Checks performed:

- Customer-level entity boundary verified.
- First observed customer transaction returns NULL.
- Arithmetic calculations verified.
- Same-timestamp transactions do not act as historical observations.
- Only strictly earlier TransactionDT values qualify as history.
- Future transactions do not affect the feature.
- Current transaction fraud outcome is not used.

Result:

PASS
## TxnCount_24h

Status: VALIDATED

Checks performed:

- Customer-level entity boundary verified.
- First observed customer transaction returns 0.
- Rolling 24-hour historical window verified.
- Window expiration verified.
- Same-timestamp transactions do not count one another.
- Only strictly earlier TransactionDT values qualify.
- Future transactions do not affect the feature.
- Current transaction fraud outcome is not used.

Result:

PASS
## CustomerAvgAmt_30d

Status: VALIDATED

Checks performed:

- Customer-level entity boundary verified.
- First observed customer transaction returns NULL.
- Average calculation verified.
- Same-timestamp transactions do not contribute to one another.
- Only strictly earlier TransactionDT values qualify.
- Future transactions do not affect the feature.
- Current transaction fraud outcome is not used.

Result:

PASS
## CustomerAmountZScore

Purpose:

Measure how unusual the current transaction amount is relative to the
customer's recent spending distribution.

Entity:

CustomerID

Historical Window:

30 days

History Rule:

historical TransactionDT < current TransactionDT

Calculation:

(TransactionAmt - CustomerAvgAmt_30d)
/
CustomerStdDevAmt_30d

Requirements:

- historical average available
- historical standard deviation available

If standard deviation is NULL or zero:

CustomerAmountZScore = NULL