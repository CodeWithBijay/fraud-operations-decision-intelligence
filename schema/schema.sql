-- ============================================================
-- Drift-Aware Fraud-Risk Decision-Support System
-- PostgreSQL Version 1 Schema
-- ============================================================
--
-- Database:
--   fraud_risk_db
--
-- Application role:
--   fraud_app
--
-- This schema represents the internally validated Version 1
-- relational data layer.
--
-- Synthetic analytical entities:
--   customer
--   account
--   device
--
-- Empirical IEEE-CIS entities:
--   transaction
--   transaction_identity
--
-- Provenance:
--   transaction_entity_lineage
--
-- MerchantID is deferred from Version 1.
-- LocationID is not implemented in Version 1.
--
-- DeviceID is intentionally nullable on transaction because
-- sufficient source device evidence is not available for every
-- transaction.
-- ============================================================


-- ============================================================
-- 1. CUSTOMER
-- ============================================================

CREATE TABLE IF NOT EXISTS customer (
    customer_id VARCHAR(32) PRIMARY KEY
);


-- ============================================================
-- 2. ACCOUNT
-- ============================================================

CREATE TABLE IF NOT EXISTS account (
    account_id VARCHAR(32) PRIMARY KEY,

    customer_id VARCHAR(32) NOT NULL,

    CONSTRAINT fk_account_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
);


-- ============================================================
-- 3. DEVICE
-- ============================================================

CREATE TABLE IF NOT EXISTS device (
    device_id VARCHAR(32) PRIMARY KEY,

    customer_id VARCHAR(32) NOT NULL,

    CONSTRAINT fk_device_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
);


-- ============================================================
-- 4. TRANSACTION
-- ============================================================
--
-- IMPORTANT:
--
-- This table initially defines the relational and core audited
-- source columns.
--
-- The complete IEEE-CIS source-column definition will be
-- finalized from the validated transaction.csv schema before
-- data loading.
--
-- We do not manually invent PostgreSQL types for the hundreds
-- of masked IEEE-CIS fields.
--
-- ============================================================

CREATE TABLE IF NOT EXISTS transaction (
    transaction_id BIGINT PRIMARY KEY,

    customer_id VARCHAR(32) NOT NULL,

    account_id VARCHAR(32) NOT NULL,

    device_id VARCHAR(32),

    transaction_dt BIGINT NOT NULL,

    transaction_amt DOUBLE PRECISION NOT NULL,

    is_fraud SMALLINT NOT NULL,

    product_cd TEXT,

    card1 DOUBLE PRECISION,

    card2 DOUBLE PRECISION,

    card3 DOUBLE PRECISION,

    card4 TEXT,

    card5 DOUBLE PRECISION,

    card6 TEXT,

    addr1 DOUBLE PRECISION,

    addr2 DOUBLE PRECISION,

    dist1 DOUBLE PRECISION,

    dist2 DOUBLE PRECISION,

    p_emaildomain TEXT,

    r_emaildomain TEXT,

    CONSTRAINT chk_transaction_is_fraud
        CHECK (is_fraud IN (0, 1)),

    CONSTRAINT fk_transaction_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_transaction_account
        FOREIGN KEY (account_id)
        REFERENCES account (account_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_transaction_device
        FOREIGN KEY (device_id)
        REFERENCES device (device_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
);


-- ============================================================
-- 5. TRANSACTION IDENTITY
-- ============================================================
--
-- Transaction identity is optional.
--
-- A transaction may have zero or one identity record.
--
-- The complete id_01 through id_38 column definitions will be
-- finalized from the validated transaction_identity.csv schema
-- before data loading.
--
-- ============================================================

CREATE TABLE IF NOT EXISTS transaction_identity (
    transaction_id BIGINT PRIMARY KEY,

    device_type TEXT,

    device_info TEXT,

    CONSTRAINT fk_identity_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transaction (transaction_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
);


-- ============================================================
-- 6. TRANSACTION ENTITY LINEAGE
-- ============================================================
--
-- Records how each analytical entity relationship was assigned.
--
-- This provides transaction-level provenance for CustomerID,
-- AccountID, and DeviceID.
--
-- ============================================================

CREATE TABLE IF NOT EXISTS transaction_entity_lineage (
    transaction_id BIGINT PRIMARY KEY,

    customer_id VARCHAR(32) NOT NULL,

    customer_id_method TEXT NOT NULL,

    account_id VARCHAR(32) NOT NULL,

    account_id_method TEXT NOT NULL,

    device_id VARCHAR(32),

    device_id_method TEXT NOT NULL,

    CONSTRAINT fk_lineage_transaction
        FOREIGN KEY (transaction_id)
        REFERENCES transaction (transaction_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_lineage_customer
        FOREIGN KEY (customer_id)
        REFERENCES customer (customer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_lineage_account
        FOREIGN KEY (account_id)
        REFERENCES account (account_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_lineage_device
        FOREIGN KEY (device_id)
        REFERENCES device (device_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_lineage_device_method
        CHECK (
            device_id_method IN (
                'CUSTOMER_NESTED_DEVICE_SIGNATURE',
                'INSUFFICIENT_DEVICE_EVIDENCE'
            )
        ),

    CONSTRAINT chk_lineage_device_consistency
        CHECK (
            (
                device_id IS NOT NULL
                AND device_id_method =
                    'CUSTOMER_NESTED_DEVICE_SIGNATURE'
            )
            OR
            (
                device_id IS NULL
                AND device_id_method =
                    'INSUFFICIENT_DEVICE_EVIDENCE'
            )
        )
);


-- ============================================================
-- 7. INDEXES
-- ============================================================
--
-- PostgreSQL automatically creates indexes for primary keys.
--
-- These additional indexes support common foreign-key joins
-- and future fraud-analytics queries.
--
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_account_customer_id
    ON account (customer_id);


CREATE INDEX IF NOT EXISTS idx_device_customer_id
    ON device (customer_id);


CREATE INDEX IF NOT EXISTS idx_transaction_customer_id
    ON transaction (customer_id);


CREATE INDEX IF NOT EXISTS idx_transaction_account_id
    ON transaction (account_id);


CREATE INDEX IF NOT EXISTS idx_transaction_device_id
    ON transaction (device_id);


CREATE INDEX IF NOT EXISTS idx_transaction_dt
    ON transaction (transaction_dt);


CREATE INDEX IF NOT EXISTS idx_lineage_customer_id
    ON transaction_entity_lineage (customer_id);


CREATE INDEX IF NOT EXISTS idx_lineage_account_id
    ON transaction_entity_lineage (account_id);


CREATE INDEX IF NOT EXISTS idx_lineage_device_id
    ON transaction_entity_lineage (device_id);


-- ============================================================
-- END OF VERSION 1 CORE SCHEMA
-- ============================================================