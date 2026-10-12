-- ============================================================
-- Feature: AmountDeviationFromCustomerAvg
-- ============================================================

SELECT
    current_txn.transaction_id,
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_amt,

    (
        SELECT AVG(history_txn.transaction_amt)
        FROM transaction history_txn
        WHERE
            history_txn.customer_id =
                current_txn.customer_id
            AND history_txn.transaction_dt <
                current_txn.transaction_dt
            AND history_txn.transaction_dt >=
                current_txn.transaction_dt - 2592000
    ) AS customer_avg_amt_30d,

    current_txn.transaction_amt
    -
    (
        SELECT AVG(history_txn.transaction_amt)
        FROM transaction history_txn
        WHERE
            history_txn.customer_id =
                current_txn.customer_id
            AND history_txn.transaction_dt <
                current_txn.transaction_dt
            AND history_txn.transaction_dt >=
                current_txn.transaction_dt - 2592000
    ) AS amount_deviation_from_customer_avg

FROM transaction current_txn

ORDER BY
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_id

LIMIT 100;