-- ============================================================
-- Feature: CustomerAvgAmt_30d
-- ============================================================

SELECT
    current_txn.transaction_id,
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_amt,

    (
        SELECT AVG(history_txn.transaction_amt)
        FROM transaction AS history_txn
        WHERE
            history_txn.customer_id =
                current_txn.customer_id

            AND history_txn.transaction_dt <
                current_txn.transaction_dt

            AND history_txn.transaction_dt >=
                current_txn.transaction_dt - 2592000
    ) AS customer_avg_amt_30d

FROM transaction AS current_txn

ORDER BY
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_id

LIMIT 100;