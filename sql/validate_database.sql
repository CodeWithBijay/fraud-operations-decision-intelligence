-- ============================================================
-- PostgreSQL Version 1 Database Validation
-- ============================================================
--
-- Purpose:
--
-- Validate that the Version 1 relational dataset was loaded
-- into PostgreSQL correctly.
--
-- This script does not modify project data.
--
-- Expected validated populations:
--
-- customer                    89,522
-- account                     93,424
-- device                      58,521
-- transaction                590,540
-- transaction_identity       144,233
-- transaction_entity_lineage 590,540
--
-- ============================================================


-- ============================================================
-- 1. TABLE ROW COUNTS
-- ============================================================

SELECT
    'customer' AS table_name,
    COUNT(*) AS row_count
FROM customer

UNION ALL

SELECT
    'account',
    COUNT(*)
FROM account

UNION ALL

SELECT
    'device',
    COUNT(*)
FROM device

UNION ALL

SELECT
    'transaction',
    COUNT(*)
FROM transaction

UNION ALL

SELECT
    'transaction_identity',
    COUNT(*)
FROM transaction_identity

UNION ALL

SELECT
    'transaction_entity_lineage',
    COUNT(*)
FROM transaction_entity_lineage;


-- ============================================================
-- 2. PRIMARY-KEY UNIQUENESS
-- ============================================================

SELECT
    'customer' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT customer_id) AS distinct_primary_keys
FROM customer

UNION ALL

SELECT
    'account',
    COUNT(*),
    COUNT(DISTINCT account_id)
FROM account

UNION ALL

SELECT
    'device',
    COUNT(*),
    COUNT(DISTINCT device_id)
FROM device

UNION ALL

SELECT
    'transaction',
    COUNT(*),
    COUNT(DISTINCT transaction_id)
FROM transaction

UNION ALL

SELECT
    'transaction_identity',
    COUNT(*),
    COUNT(DISTINCT transaction_id)
FROM transaction_identity

UNION ALL

SELECT
    'transaction_entity_lineage',
    COUNT(*),
    COUNT(DISTINCT transaction_id)
FROM transaction_entity_lineage;


-- ============================================================
-- 3. REQUIRED TRANSACTION RELATIONSHIPS
-- ============================================================

SELECT
    COUNT(*) AS transactions_missing_customer
FROM transaction
WHERE customer_id IS NULL;


SELECT
    COUNT(*) AS transactions_missing_account
FROM transaction
WHERE account_id IS NULL;


SELECT
    COUNT(*) AS transactions_missing_device
FROM transaction
WHERE device_id IS NULL;


-- ============================================================
-- 4. ACCOUNT -> CUSTOMER FOREIGN-KEY INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_accounts
FROM account AS a
LEFT JOIN customer AS c
    ON a.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- ============================================================
-- 5. DEVICE -> CUSTOMER FOREIGN-KEY INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_devices
FROM device AS d
LEFT JOIN customer AS c
    ON d.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- ============================================================
-- 6. TRANSACTION -> CUSTOMER INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_transaction_customers
FROM transaction AS t
LEFT JOIN customer AS c
    ON t.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- ============================================================
-- 7. TRANSACTION -> ACCOUNT INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_transaction_accounts
FROM transaction AS t
LEFT JOIN account AS a
    ON t.account_id = a.account_id
WHERE a.account_id IS NULL;


-- ============================================================
-- 8. TRANSACTION -> DEVICE INTEGRITY
-- ============================================================
--
-- DeviceID is nullable.
--
-- Therefore this check examines only transactions where a
-- DeviceID actually exists.
-- ============================================================

SELECT
    COUNT(*) AS orphan_transaction_devices
FROM transaction AS t
LEFT JOIN device AS d
    ON t.device_id = d.device_id
WHERE
    t.device_id IS NOT NULL
    AND d.device_id IS NULL;


-- ============================================================
-- 9. ACCOUNT OWNERSHIP CONSISTENCY
-- ============================================================
--
-- Transaction.CustomerID must match the customer who owns
-- Transaction.AccountID.
-- ============================================================

SELECT
    COUNT(*) AS account_customer_mismatches
FROM transaction AS t
JOIN account AS a
    ON t.account_id = a.account_id
WHERE t.customer_id <> a.customer_id;


-- ============================================================
-- 10. DEVICE OWNERSHIP CONSISTENCY
-- ============================================================

SELECT
    COUNT(*) AS device_customer_mismatches
FROM transaction AS t
JOIN device AS d
    ON t.device_id = d.device_id
WHERE t.customer_id <> d.customer_id;


-- ============================================================
-- 11. IDENTITY -> TRANSACTION INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_identity_records
FROM transaction_identity AS i
LEFT JOIN transaction AS t
    ON i.transaction_id = t.transaction_id
WHERE t.transaction_id IS NULL;


-- ============================================================
-- 12. LINEAGE -> TRANSACTION INTEGRITY
-- ============================================================

SELECT
    COUNT(*) AS orphan_lineage_records
FROM transaction_entity_lineage AS l
LEFT JOIN transaction AS t
    ON l.transaction_id = t.transaction_id
WHERE t.transaction_id IS NULL;


-- ============================================================
-- 13. TRANSACTION <-> LINEAGE CUSTOMERID CONSISTENCY
-- ============================================================

SELECT
    COUNT(*) AS lineage_customer_mismatches
FROM transaction AS t
JOIN transaction_entity_lineage AS l
    ON t.transaction_id = l.transaction_id
WHERE t.customer_id <> l.customer_id;


-- ============================================================
-- 14. TRANSACTION <-> LINEAGE ACCOUNTID CONSISTENCY
-- ============================================================

SELECT
    COUNT(*) AS lineage_account_mismatches
FROM transaction AS t
JOIN transaction_entity_lineage AS l
    ON t.transaction_id = l.transaction_id
WHERE t.account_id <> l.account_id;


-- ============================================================
-- 15. TRANSACTION <-> LINEAGE DEVICEID CONSISTENCY
-- ============================================================
--
-- IS DISTINCT FROM is NULL-safe.
--
-- NULL and NULL are treated as equal for this comparison.
-- ============================================================

SELECT
    COUNT(*) AS lineage_device_mismatches
FROM transaction AS t
JOIN transaction_entity_lineage AS l
    ON t.transaction_id = l.transaction_id
WHERE t.device_id IS DISTINCT FROM l.device_id;


-- ============================================================
-- 16. LINEAGE METHOD COMPLETENESS
-- ============================================================

SELECT
    COUNT(*) AS missing_customer_methods
FROM transaction_entity_lineage
WHERE customer_id_method IS NULL;


SELECT
    COUNT(*) AS missing_account_methods
FROM transaction_entity_lineage
WHERE account_id_method IS NULL;


SELECT
    COUNT(*) AS missing_device_methods
FROM transaction_entity_lineage
WHERE device_id_method IS NULL;


-- ============================================================
-- 17. DEVICEID NULL POLICY
-- ============================================================
--
-- If DeviceID exists:
-- CUSTOMER_NESTED_DEVICE_SIGNATURE
--
-- If DeviceID is NULL:
-- INSUFFICIENT_DEVICE_EVIDENCE
-- ============================================================

SELECT
    COUNT(*) AS invalid_device_method_relationships
FROM transaction_entity_lineage
WHERE
    (
        device_id IS NOT NULL
        AND device_id_method
            <> 'CUSTOMER_NESTED_DEVICE_SIGNATURE'
    )
    OR
    (
        device_id IS NULL
        AND device_id_method
            <> 'INSUFFICIENT_DEVICE_EVIDENCE'
    );


-- ============================================================
-- 18. FRAUD LABEL CHECK
-- ============================================================

SELECT
    COUNT(*) AS invalid_fraud_labels
FROM transaction
WHERE
    is_fraud IS NULL
    OR is_fraud NOT IN (0, 1);


-- ============================================================
-- END OF POSTGRESQL VERSION 1 VALIDATION
-- ============================================================