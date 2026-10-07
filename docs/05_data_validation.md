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