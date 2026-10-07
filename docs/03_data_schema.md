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