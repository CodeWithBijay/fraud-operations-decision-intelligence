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



## 6. Input Audit Results

The input audit was executed programmatically against the original
IEEE-CIS source files.

The audit did not generate synthetic data and did not modify the
original source files.


### 6.1 Dataset Structure

The transaction dataset contains:

- 590,540 transaction records;
- 394 columns.

The identity dataset contains:

- 144,233 identity records;
- 41 columns.

The transaction dataset therefore represents the primary transaction
population, while the identity dataset provides additional information
for a subset of transactions.


### 6.2 TransactionID Integrity

The transaction dataset contains:

- 0 missing TransactionID values;
- 0 duplicate TransactionID values.

The identity dataset contains:

- 0 missing TransactionID values;
- 0 duplicate TransactionID values.

The audit identified:

- 0 orphan identity records.

This means every identity record in the audited source data references
a TransactionID that exists in the transaction dataset.


### 6.3 Transaction-to-Identity Coverage

Transactions with corresponding identity information:

144,233

Transactions without corresponding identity information:

446,307

Identity coverage:

24.4239%

Identity information is therefore available for only a subset of the
transaction population.

Transactions without identity information will remain valid
transactions and will not be removed simply because an identity record
is unavailable.


### 6.4 Fraud Outcome

The source transaction data contain:

- 20,663 fraud transactions;
- 569,877 non-fraud transactions;
- 0 missing fraud labels.

Observed fraud prevalence:

3.499%

The fraud outcome will be preserved as an observed source variable.

The fraud label will not be used to manufacture synthetic
prediction-time variables.


### 6.5 Transaction Amount

TransactionAmt contains:

- 0 missing values;
- minimum: 0.251;
- first quartile (25th percentile): 43.321;
- median: 68.769;
- mean: 135.0272;
- third quartile (75th percentile): 125.0;
- 95th percentile: 445.0;
- 99th percentile: 1104.0;
- maximum: 31937.391;
- standard deviation: 239.1625.

The observed mean is higher than the median, and the upper percentiles
extend substantially beyond the median.

The original TransactionAmt values will be preserved rather than
synthetically regenerated.


### 6.6 Transaction Time

TransactionDT contains:

- 0 missing values;
- minimum observed value: 86400;
- maximum observed value: 15811131.

The audit confirmed that the original transaction records are in
chronological order according to TransactionDT.

The original TransactionDT values and chronological order will be
preserved throughout synthetic augmentation.

TransactionDT will be treated as the source dataset's relative temporal
measure and will not be presented as an observed calendar timestamp.


### 6.7 Source Missingness

Detailed column-level missingness results were calculated directly from
the source files and are stored in:

- `reports/input_audit/transaction_missingness.csv`
- `reports/input_audit/identity_missingness.csv`

Missing source values will not be replaced during synthetic generation
unless a separate documented transformation rule requires it.


### 6.8 Input Audit Conclusion

The source-data audit confirms that TransactionID can be used as the
transaction identifier for the audited data because no missing or
duplicate transaction identifiers were identified.

The transaction-to-identity relationship is valid, with no orphan
identity records identified. Identity information is optional because
only 24.4239% of transactions have a corresponding identity record.

TransactionAmt and TransactionDT provide observed monetary and temporal
information and will be preserved in their original source form.

The observed fraud prevalence of 3.499% will also be preserved rather
than synthetically recreated.

These audit results will be used in the next data-generation step to
determine which additional entities and relationships are genuinely
missing from the source data.

## 7. Initial Synthetic Data Requirements

The source-data audit and source-column review were used to determine
which additional persistent entities are required by the project.

The initial version of the project will generate only the relational
identifiers necessary to support the approved data schema and historical
behavior analysis.

No synthetic transaction amount, fraud outcome, or replacement source
variables will be generated.


### 7.1 CustomerID

### CustomerID

**Status:** Required, methodology under evaluation

**Provenance:** Synthetic analytical identifier

The IEEE-CIS source files do not contain an explicit CustomerID field.

A persistent CustomerID is required by this project because several
planned behavioral features require transactions to be associated with
a consistent customer history.

Examples include:

- transaction counts over historical windows;
- historical transaction amounts;
- time since previous customer transaction;
- device-history relationships;
- merchant-history relationships.

The project will not assign CustomerID independently at random.

The project will also not automatically reinterpret an individual
masked IEEE-CIS field as a true customer identifier.

Instead, candidate source attributes will be evaluated to determine
whether a source-informed grouping can provide a useful synthetic
analytical customer identity.

The resulting CustomerID will represent a project-level analytical
entity. It will not be presented as the true customer identity provided
by IEEE-CIS.

The current transaction's `isFraud` value must not be used when
constructing CustomerID.

Before the CustomerID generation rule is approved, candidate grouping
definitions will be evaluated using the actual source data.

The evaluation will consider:

- number of resulting customer groups;
- number of transactions per group;
- proportion of groups with repeated transactions;
- missingness in candidate grouping attributes;
- concentration in unusually large groups;
- chronological usability for historical feature engineering.

The final CustomerID rule will be documented only after these empirical
checks have been completed.

Do we need CustomerID?
        │
       YES ✅
        │
        ▼
Do we have a real CustomerID?
        │
       NO
        │
        ▼
Should we randomly create it?
        │
       NO
        │
        ▼
Can IEEE-CIS attributes help
create source-informed groups?
        │
        ▼
     TEST NEXT

#### CustomerID Candidate Analysis

Five source-informed candidate grouping definitions were evaluated using
the full transaction dataset.

The analysis measured:

- grouping-field coverage;
- number of resulting groups;
- proportion of single-transaction groups;
- proportion of recurring groups;
- transactions represented by recurring groups;
- median transactions per group;
- upper group-size percentiles;
- maximum group size.

`card1` alone provided complete transaction coverage but produced highly
concentrated groups, including a maximum group size of 14,932
transactions. It was therefore not selected as the preferred customer
grouping candidate.

Adding `addr1` increased grouping specificity while retaining 88.8736%
coverage. However, the largest resulting group still contained 5,885
transactions.

The combination:

`card1 + addr1 + P_emaildomain`

produced:

- 73.2665% complete-field coverage;
- 73,407 candidate groups;
- 50.2745% recurring groups;
- 91.5635% of usable transactions belonging to recurring groups;
- median group size of 2 transactions;
- 95th-percentile group size of 19 transactions;
- 99th-percentile group size of 69 transactions;
- maximum group size of 2,242 transactions.

Adding `card2` to the tested combinations did not materially improve the
observed grouping characteristics and reduced available transaction
coverage.

Based on the current analysis, `card1 + addr1 + P_emaildomain` is the
leading source-informed candidate for constructing the project's
synthetic analytical CustomerID.

This combination is not interpreted as the true customer identity in
IEEE-CIS.

The CustomerID methodology is not yet finalized because 157,872
transactions do not contain complete values for all three candidate
grouping fields.

A documented fallback method for incomplete transactions must be
evaluated before the CustomerID generation rule is approved.
#### CustomerID Missingness and Fallback Analysis

The leading primary CustomerID grouping candidate requires:

`card1 + addr1 + P_emaildomain`

This combination is complete for 432,668 of the 590,540 source
transactions.

A total of 157,872 transactions do not contain all three fields.

The incomplete population consists of:

- 63,416 transactions missing only `addr1`;
- 92,166 transactions missing only `P_emaildomain`;
- 2,290 transactions missing both `addr1` and `P_emaildomain`;
- 0 transactions missing `card1`.

Three weaker fallback definitions were evaluated against the established
complete primary groups.

##### card1 + addr1

This fallback produced a unique match to an existing primary group for
5,790 transactions.

It produced ambiguous matches for 80,164 transactions.

Therefore, `card1 + addr1` will not be used as an unconditional
CustomerID fallback.

It may be used only when the combination maps to exactly one existing
primary customer group.


##### card1 + P_emaildomain

This fallback produced a unique match to an existing primary group for
4,864 transactions.

It produced ambiguous matches for 47,314 transactions.

Therefore, `card1 + P_emaildomain` will not be used as an unconditional
CustomerID fallback.

It may be used only when it maps to exactly one existing primary
customer group.


##### card1

Although `card1` is available for all transactions, using it alone
produced ambiguous matches for 146,181 of the 157,872 primary-incomplete
transactions.

Therefore, `card1` alone will not be used to merge incomplete
transactions with existing primary customer groups.


#### CustomerID Linking Principle

The CustomerID methodology will not force incomplete transactions into
existing customer groups.

A weaker source signature may link an incomplete transaction to an
existing primary customer group only when the mapping is unique.

Ambiguous mappings will not be resolved by random selection.

Transactions that cannot be uniquely associated with an existing
primary group will remain separate from those established groups until
a documented unresolved-grouping rule is applied.

The resulting CustomerID remains a project-level synthetic analytical
identifier and must not be interpreted as the true customer identity in
IEEE-CIS.

The `isFraud` outcome is not used in primary grouping, fallback matching,
or unresolved grouping.

### 7.2 AccountID

**Requirement:** Required

**Provenance:** Synthetic

The source files do not contain an explicit AccountID corresponding to
the account entity defined by the project schema.

A persistent synthetic AccountID is required to represent the
Customer-to-Account-to-Transaction relationship.

The existing masked card variables will remain source variables and will
not automatically be reinterpreted as the project's synthetic AccountID
without supporting evidence.

Every generated account must belong to a valid synthetic customer.

Every transaction assigned an AccountID must reference an existing
synthetic account.


### 7.3 MerchantID

**Requirement:** Required

**Provenance:** Synthetic

The source transaction data do not contain an explicit persistent
MerchantID field required by the project schema.

A synthetic persistent MerchantID is required to support merchant-level
transaction history and customer-to-merchant behavioral relationships.

This relationship will later support derived measures such as whether a
merchant has previously been observed for a customer.

MerchantID generation must not use the current transaction's fraud
outcome.


### 7.4 DeviceID

**Requirement:** Required

**Provenance:** Synthetic with source-informed context where appropriate

IEEE-CIS provides DeviceType and DeviceInfo through the identity data
where those fields are available.

These source fields will be preserved.

The project requires a separate persistent DeviceID so device usage can
be represented consistently across transaction histories and later used
to derive device-history features.

The input audit found that identity information is available for
144,233 of 590,540 transactions, representing 24.4239% transaction
coverage.

Because identity information is unavailable for many transactions,
DeviceID generation cannot rely exclusively on the identity table.

The method for creating persistent DeviceID relationships will therefore
be defined separately before generation.

DeviceID generation must not use the current transaction's fraud
outcome.


## 8. Variables Not Generated in the Initial Version

The initial generation version will not yet create additional synthetic
attributes such as:

- customer segment;
- customer risk level;
- merchant risk tier;
- authentication events;
- investigation costs;
- recovery rates;
- loss-given-fraud assumptions.

These variables may be considered later only if they are required for a
specific project decision or analytical use case and can be supported by
appropriate evidence, calibration, or clearly documented assumptions.


## 9. Initial Generation Boundary

The initial synthetic-generation scope is therefore limited to:

1. CustomerID;
2. AccountID;
3. MerchantID;
4. DeviceID.

The original IEEE-CIS transaction and identity variables will remain
source data.

Historical behavioral variables will be derived later from the resulting
transaction relationships rather than independently generated.