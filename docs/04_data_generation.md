# 04 - Data Generation

## 1. Purpose

This document describes the data-generation process used in the
Drift-Aware Fraud-Risk Decision-Support System.

The project uses an empirical transaction dataset as its starting point
and will generate only the additional information required by the
approved workflow and data schema.

Synthetic data will not be generated until the source data have been
profiled and the required synthetic variables and their generation rules
have been documented.


## 2. Source Data

The project uses the IEEE-CIS Fraud Detection dataset as the empirical
transaction baseline.

The current source files are:

- `train_transaction.csv`
- `train_identity.csv`

The files are stored locally under:

`data/raw/ieee_cis/`

The raw source files will be treated as read-only inputs.

Generation scripts must not overwrite the original source files.


## 3. Source Dataset Roles

### train_transaction.csv

This file contains transaction-level information.

Based on the project requirements, important source fields to inspect
include:

- `TransactionID`
- `TransactionDT`
- `TransactionAmt`
- `isFraud`

Additional transaction variables will be documented after the source
data audit.


### train_identity.csv

This file contains additional identity and device information for
transactions where identity information is available.

The transaction and identity files are connected using:

`TransactionID`


## 4. Input Data Audit

Before synthetic data generation begins, the original source data will
be profiled.

The purpose of the input audit is to understand the source data before
deciding what additional information must be generated.

The audit will measure:

- transaction dataset row count;
- transaction dataset column count;
- identity dataset row count;
- identity dataset column count;
- `TransactionID` integrity;
- transaction-to-identity relationship coverage;
- observed fraud prevalence;
- `TransactionAmt` distribution;
- `TransactionDT` range;
- source-variable missingness.


## 5. Audit Principle

Values measured from the source data will not be manually entered before
the audit.

Counts, percentages, missingness rates, fraud prevalence, amount
statistics, and temporal ranges will be calculated directly from the
original source files.

The audit results will be recorded only after they have been produced by
the input-audit script.


## 6. Audit Results

Audit results have not yet been recorded in this document.

They will be added after the source-data audit has been executed and its
outputs have been reviewed.