-- ============================================================
-- Feature: TxnCount_24h
-- ============================================================

SELECT
    current_txn.transaction_id,
    current_txn.customer_id,
    current_txn.transaction_dt,

    (
        SELECT COUNT(*)
        FROM transaction AS history_txn
        WHERE
            history_txn.customer_id =
                current_txn.customer_id

            AND history_txn.transaction_dt <
                current_txn.transaction_dt

            AND history_txn.transaction_dt >=
                current_txn.transaction_dt - 86400
    ) AS txn_count_24h

FROM transaction AS current_txn

ORDER BY
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_id

LIMIT 100;