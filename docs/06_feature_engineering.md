# 06 - Feature Engineering

## 1. Purpose

This document defines the feature-engineering methodology used by the
fraud-risk decision-support project.

Feature engineering begins only after completion and validation of the
Version 1 relational dataset and its PostgreSQL implementation.

The objective is to construct transaction-level and historical
behavioral features without introducing information that would have
been unavailable when a transaction was evaluated.


## 2. Point-in-Time Correctness

Historical features must be point-in-time correct.

For a transaction occurring at TransactionDT = t, a historical feature
may use only transactions satisfying:

historical TransactionDT < current TransactionDT

Transactions occurring after the current transaction must never
contribute to its feature values.

Transactions with the same TransactionDT are not automatically treated
as earlier observations because the source data do not establish a
within-timestamp event ordering for the project.

This conservative rule prevents future transaction information from
being incorporated into historical predictor values.


## 3. Current Transaction Versus Historical Information

Feature engineering distinguishes between current-transaction
information and historical information.

Current source attributes available on the transaction itself may be
used as predictors where methodologically appropriate.

Examples include:

- TransactionAmt;
- ProductCD;
- card-related source fields;
- address-related source fields;
- distance-related source fields;
- identity attributes where available.

Historical behavioral features must use only observations occurring
before the current transaction.


## 4. Fraud Outcome Isolation

The current transaction's isFraud value is an outcome variable.

It must not be used when constructing predictor features for that
transaction.

The isFraud field will be used later as the supervised-learning target
and for model evaluation.

Feature-generation logic must therefore remain independent of the
current transaction's fraud outcome.


## 5. Historical Entity Boundaries

Historical features must respect the analytical entity represented by
the feature.

Customer-level features use historical transactions associated with the
same CustomerID.

Account-level features use historical transactions associated with the
same AccountID.

Device-level features use historical transactions associated with the
same non-null DeviceID.

Entity relationships must remain consistent with the validated Version
1 relational dataset.


## 6. Missing Device Evidence

DeviceID is nullable by design.

A NULL DeviceID represents insufficient source evidence for the
analytical device relationship.

A missing DeviceID must not automatically be interpreted as a newly
observed device.

Device-history features that require a persistent DeviceID must preserve
the distinction between:

- a known device with no previous observed history; and
- a transaction for which DeviceID could not be established.


## 7. Candidate Historical Features

Candidate historical features include:

- TxnCount_1h;
- TxnCount_24h;
- TxnAmount_24h;
- HoursSincePreviousTxn;
- CustomerAvgAmt_30d;
- transaction-amount deviation from historical customer behavior;
- IsNewDevice.

These fields are candidate derived features.

They will be implemented and validated individually rather than assumed
to be valid simply because they appear in the conceptual feature list.


## 8. Leakage-Prevention Rule

For every derived historical feature:

1. identify the entity whose history is used;
2. identify the current transaction time;
3. restrict the feature input to observations strictly earlier than the
   current TransactionDT;
4. exclude the current transaction's outcome;
5. exclude future observations;
6. preserve NULL or insufficient-history states where appropriate;
7. validate the resulting feature before using it for modeling.

No modeling stage may begin until the implemented historical features
have