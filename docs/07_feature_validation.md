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