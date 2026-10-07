# 05 - Data Validation

## 1. Purpose

Data validation is used to verify that synthetic entities and
relationships produced by the project follow the documented generation
rules.

Validation is performed programmatically.

A generated dataset must not be considered internally validated until
the required checks pass.


## 2. CustomerID Validation

CustomerID validation was performed after the CustomerID generation
process.

The purpose of the validation was to confirm that the generated
analytical customer identifiers follow the documented CustomerID
methodology.


### 2.1 Validation Scope

The CustomerID validation checks include:

- source and generated mapping row-count consistency;
- TransactionID uniqueness;
- CustomerID completeness;
- CustomerID assignment-method completeness;
- source TransactionID preservation;
- TransactionDT preservation;
- permitted CustomerID assignment methods;
- primary grouping consistency;
- primary CustomerID collision checks;
- weak-information isolation;
- incompatible CustomerID-method collision checks.


### 2.2 Validation Results

Source transaction rows:

590,540

Generated transaction-to-customer mapping rows:

590,540

Distinct analytical CustomerIDs:

89,522

Validation tests executed:

11

Validation tests passed:

11

Validation tests failed:

0

Overall validation status:

**PASS**


### 2.3 Interpretation

The CustomerID generation process passed all currently defined
CustomerID integrity tests.

Every source transaction is represented in the generated mapping, and
the validation process identified no failures among the 11 implemented
CustomerID checks.

This result establishes internal consistency between the documented
CustomerID generation methodology and its generated output.

The validation result does not establish that the generated analytical
CustomerIDs correspond to true customer identities in IEEE-CIS.

CustomerID remains a synthetic analytical identifier created for the
purposes of relational and historical analysis within this project.

External realism of the generated customer population is a separate
validation question and is not established by these integrity tests.
## 3. AccountID Validation

AccountID validation was performed after completion of the AccountID
generation process.

The purpose of the validation was to verify that the generated
analytical account identifiers follow the documented AccountID
generation methodology and preserve the required
Customer-to-Account-to-Transaction relationships.


### 3.1 Validation Scope

The AccountID validation checks include:

- source and generated mapping row-count consistency;
- TransactionID uniqueness;
- CustomerID completeness;
- AccountID completeness;
- AccountID assignment-method completeness;
- source TransactionID preservation;
- TransactionDT preservation;
- permitted AccountID assignment methods;
- AccountID-to-CustomerID ownership consistency;
- primary account-signature completeness;
- primary account-signature consistency;
- primary AccountID collision checks;
- fallback CustomerID-boundary integrity;
- unresolved AccountID ownership integrity;
- incompatible AccountID-method collision checks.


### 3.2 Validation Results

Source transaction rows:

590,540

Generated transaction-to-account mapping rows:

590,540

Distinct analytical CustomerIDs:

89,522

Distinct analytical AccountIDs:

93,424

Validation tests executed:

15

Validation tests passed:

15

Validation tests failed:

0

Overall validation status:

**PASS**


### 3.3 Interpretation

The AccountID generation process passed all 15 currently defined
AccountID integrity tests.

The generated mapping contains the same number of records as the
original transaction population, and no AccountID validation failures
were identified.

The validation confirms internal consistency between the documented
AccountID generation methodology and the generated analytical
customer-account relationships.

This result establishes structural and methodological validity for the
current AccountID generation implementation.

It does not establish that the generated analytical AccountIDs
correspond to verified real-world bank accounts in IEEE-CIS.

AccountID remains a project-level synthetic analytical identifier.

External realism of the generated account population remains a separate
validation question and is not established by these integrity tests.

## 4. MerchantID Assessment

MerchantID was evaluated as a candidate synthetic entity before
generation.

The purpose of the assessment was to determine whether the available
IEEE-CIS source variables could support a defensible persistent
merchant-level analytical identity.

Six source-informed candidate merchant signatures were evaluated.

The analysis considered:

- source-field missingness;
- candidate-field coverage;
- number of resulting merchant-like groups;
- repeated-group behavior;
- transactions represented by recurring groups;
- transaction counts per candidate group;
- unusually large candidate groups.

The analysis did not identify a source-field combination that provided
sufficient evidence for a defensible persistent MerchantID.

As a result:

**MerchantID generation status: DEFERRED**

No transaction-to-merchant synthetic mapping was generated.

Therefore, generated-data integrity validation for MerchantID is not
applicable in the current project version.

This decision prevents unsupported merchant relationships from being
introduced solely to satisfy the original conceptual schema.

Features requiring persistent merchant identity, including
`IsFirstTimeMerchant`, are also deferred in the current version.

MerchantID may be reconsidered if stronger merchant-level source
information becomes available.

## DeviceID Validation

DeviceID validation was performed after completion of the DeviceID
generation process.

The validation independently tested whether the generated analytical
DeviceIDs followed the documented customer-nested device methodology.


### Validation Scope

The DeviceID validation included checks for:

- source and generated mapping row-count consistency;
- TransactionID uniqueness;
- CustomerID completeness;
- DeviceID assignment-method completeness;
- source TransactionID preservation;
- TransactionDT preservation;
- DeviceType preservation;
- DeviceInfo preservation;
- permitted DeviceID assignment methods;
- DeviceID eligibility based on source evidence;
- prevention of DeviceID generation when source evidence is incomplete;
- assignment-method consistency;
- NULL DeviceID policy;
- CustomerID boundary integrity;
- customer-device signature consistency;
- DeviceID signature collision checks;
- deterministic DeviceID reproduction;
- generated DeviceID count reconciliation;
- NULL DeviceID count reconciliation.


### Validation Results

Source transaction rows:

590,540

Generated device-mapping rows:

590,540

Transactions with DeviceID:

118,621

Transactions without DeviceID:

471,919

Distinct analytical DeviceIDs:

58,521

Validation tests executed:

21

Validation tests passed:

21

Validation tests failed:

0

Overall validation status:

**PASS**


### Interpretation

The DeviceID generation implementation passed all 21 currently defined
integrity and methodology tests.

The validation confirms that analytical DeviceIDs are generated only
when sufficient source device evidence exists.

Transactions without sufficient source device evidence retain a NULL
DeviceID rather than receiving an invented device relationship.

Generated DeviceIDs remain nested within CustomerID and follow the
documented deterministic customer-device signature methodology.

The validation result establishes internal implementation consistency.
It does not establish that generated DeviceIDs correspond to verified
physical devices.


### High-Device Customer Review

The validation also examined unusually large analytical device counts
per customer.

The observed maximum was 448 analytical DeviceIDs for a single
CustomerID.

The high-device analysis found:

- 197 customers with more than 10 DeviceIDs;
- 71 customers with more than 25 DeviceIDs;
- 39 customers with more than 50 DeviceIDs;
- 21 customers with more than 100 DeviceIDs.

The analytical customer with the maximum device count had:

- 448 distinct DeviceIDs;
- 2,703 transactions with device evidence;
- 2 distinct DeviceType values;
- 418 distinct DeviceInfo values.

The large analytical DeviceID count is therefore associated with
substantial variation in the underlying source DeviceInfo values.

This observation is recorded as a statistical-realism and
source-fragmentation consideration rather than an integrity-validation
failure.

Additional external calibration would be required before interpreting
these analytical DeviceIDs as realistic physical-device counts.
``

## Final Relational Dataset Validation

Following entity-level generation and validation, the Version 1
relational dataset was assembled and validated as a complete system.

The final relational layer contains:

- 89,522 analytical customers;
- 93,424 analytical accounts;
- 58,521 analytical devices;
- 590,540 transactions;
- 144,233 transaction-identity records;
- 590,540 transaction-entity lineage records.

CustomerID is present for every transaction.

AccountID is present for every transaction.

DeviceID is intentionally nullable because the documented DeviceID
methodology generates an analytical device relationship only when
sufficient source device evidence exists.

A total of 471,919 transactions therefore retain a NULL DeviceID.


### Relational Validation Scope

The final relational validation tests covered:

- primary-key integrity;
- foreign-key integrity;
- customer-account ownership consistency;
- customer-device ownership consistency;
- source transaction preservation;
- source identity preservation;
- transaction-to-lineage consistency;
- entity-population consistency;
- synthetic relationship provenance completeness.


### Relational Validation Results

Validation tests executed:

32

Validation tests passed:

32

Validation tests failed:

0

Overall validation status:

**PASS**


### Primary-Key Integrity

The validation identified no missing or duplicate primary-key values in:

- Customer.CustomerID;
- Account.AccountID;
- Device.DeviceID;
- Transaction.TransactionID;
- TransactionIdentity.TransactionID;
- TransactionEntityLineage.TransactionID.


### Foreign-Key Integrity

The validation identified zero orphan records across the implemented
relationships:

- Account.CustomerID -> Customer.CustomerID;
- Device.CustomerID -> Customer.CustomerID;
- Transaction.CustomerID -> Customer.CustomerID;
- Transaction.AccountID -> Account.AccountID;
- non-null Transaction.DeviceID -> Device.DeviceID;
- TransactionIdentity.TransactionID -> Transaction.TransactionID;
- TransactionEntityLineage.TransactionID -> Transaction.TransactionID.


### Relationship Ownership

The validation identified:

- 0 transaction-to-account customer ownership mismatches;
- 0 transaction-to-device customer ownership mismatches.

The analytical account and device relationships therefore remain nested
within the appropriate CustomerID boundaries.


### Source Transaction Preservation

The final relational dataset preserved the original source transaction
population.

The validation identified:

- 0 unmatched TransactionID values;
- 0 changed TransactionDT values;
- 0 changed TransactionAmt values;
- 0 changed isFraud values.

The synthetic relational augmentation therefore did not modify these
audited empirical transaction fields.


### Identity Preservation

The original IEEE-CIS identity population contained 144,233 records.

The final transaction_identity table also contains 144,233 records.

The validation identified:

- 0 missing identity TransactionID values relative to the source;
- 0 additional identity TransactionID values;
- 0 changed identity source cells.


### Lineage Integrity

Every transaction has exactly one corresponding
transaction_entity_lineage record.

The validation identified:

- 0 CustomerID mismatches between transaction and lineage;
- 0 AccountID mismatches between transaction and lineage;
- 0 DeviceID mismatches between transaction and lineage, including NULL
  device relationships.

Every lineage record also contains CustomerID_method, AccountID_method,
and DeviceID_method provenance.


## Version 1 Validation Conclusion

The Version 1 generated relational dataset passed all 32 implemented
system-level validation tests.

The dataset is therefore considered internally validated against the
documented structural, relational, ownership, provenance, and
source-preservation rules.

This internal validation does not establish that synthetic CustomerID,
AccountID, or DeviceID values correspond to verified real-world
identities.

It also does not establish external statistical realism for a specific
financial institution.

The validated identifiers are project-level analytical entities created
to support the fraud-risk decision-support workflow while preserving
the limitations and observed values of the IEEE-CIS source data.