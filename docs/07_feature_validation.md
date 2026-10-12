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

Status: VALIDATED

Checks performed:

- Historical average verified
- Historical standard deviation verified
- First transaction returns NULL
- Insufficient-history cases return NULL
- Positive z-scores verified
- Negative z-scores verified
- Point-in-time correctness verified
- Same-timestamp behavior inherited from validated historical features
- No fraud-label leakage

Result:

PASS