# 03 - Data Schema

## 1. Purpose

This document defines the implemented data structure for the
Drift-Aware Fraud-Risk Decision-Support System.

The schema is based on the original IEEE-CIS source data together with
the synthetic analytical relationships that were supported by the
data-generation and validation process.

Entities that could not be supported by sufficient source evidence are
not implemented merely to satisfy the original conceptual design.


## 2. Implemented Relational Structure

The current Version 1 analytical structure is:

Customer
   |
   +-- Account
   |     |
   |     +-- Transaction
   |
   +-- Device

Transactions remain the central empirical records from IEEE-CIS.

Customer, Account, and Device identifiers are project-level analytical
identifiers created through the documented generation methodology.


## 3. Entity Implementation Status

### Customer

**Status:** Implemented

The project contains a synthetic analytical CustomerID that provides a
persistent customer-level grouping for historical analysis.

CustomerID does not represent a verified real customer identity from
IEEE-CIS.


### Account

**Status:** Implemented

AccountID is a synthetic analytical identifier nested within CustomerID.

It supports the relationship:

Customer -> Account -> Transaction

AccountID does not represent a verified real-world bank account
identifier from IEEE-CIS.


### Transaction

**Status:** Implemented from source data

Transactions originate from the IEEE-CIS transaction dataset.

Important source attributes include:

- TransactionID
- TransactionDT
- TransactionAmt
- isFraud
- ProductCD
- card-related variables
- address-related variables
- distance variables
- C variables
- D variables
- M variables
- V variables

Original transaction observations are preserved as source data.


### Transaction Identity

**Status:** Implemented from source data where available

IEEE-CIS identity information is joined to transactions using
TransactionID.

Identity information is optional because not every transaction has a
corresponding identity record.


### Device

**Status:** Partially implemented

DeviceID is generated only when sufficient source device evidence is
available.

The analytical DeviceID is based on:

CustomerID + DeviceType + DeviceInfo

Transactions without sufficient device evidence retain a NULL DeviceID.

A NULL DeviceID means that device identity could not be established from
the available source information.

It must not be interpreted as a new device.


### Merchant

**Status:** Deferred from Version 1

MerchantID candidate analysis did not identify sufficient source
evidence for a defensible persistent merchant-level analytical entity.

MerchantID is therefore not generated in Version 1.

Source fields such as ProductCD and email-domain variables remain
available as transaction attributes but are not interpreted as verified
merchant identities.


### Location

**Status:** No separate entity in Version 1

A synthetic LocationID is not generated.

Existing IEEE-CIS location-related source variables such as addr1,
addr2, dist1, and 


## 4. Version 1 Physical Table Design

The initial generated relational layer consists of six logical tables.

### customer

Fields:

- CustomerID

Primary key:

- CustomerID


### account

Fields:

- AccountID
- CustomerID

Primary key:

- AccountID

Foreign key:

- CustomerID -> customer.CustomerID


### device

Fields:

- DeviceID
- CustomerID

Primary key:

- DeviceID

Foreign key:

- CustomerID -> customer.CustomerID

Only transactions for which sufficient device evidence exists contribute
to the device entity population.


### transaction

Fields include:

- TransactionID
- CustomerID
- AccountID
- DeviceID
- TransactionDT
- TransactionAmt
- ProductCD
- card1-card6
- addr1-addr2
- dist1-dist2
- P_emaildomain
- R_emaildomain
- C1-C14
- D1-D15
- M1-M9
- V1-V339
- isFraud

Primary key:

- TransactionID

Foreign keys:

- CustomerID -> customer.CustomerID
- AccountID -> account.AccountID
- DeviceID -> device.DeviceID

DeviceID is nullable because sufficient source device evidence is not
available for every transaction.


### transaction_identity

Fields include:

- TransactionID
- id_01-id_38
- DeviceType
- DeviceInfo

Primary key:

- TransactionID

Foreign key:

- TransactionID -> transaction.TransactionID

A transaction may have zero or one corresponding identity record.


### transaction_entity_lineage

Fields:

- TransactionID
- CustomerID
- CustomerID_method
- AccountID
- AccountID_method
- DeviceID
- DeviceID_method

This table records the provenance of synthetic analytical relationship
assignment for each transaction.

It supports traceability between source transactions and generated
CustomerID, AccountID, and DeviceID relationships.