SELECT
    current_txn.transaction_id,
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_amt,

    (
        SELECT AVG(h.transaction_amt)
        FROM transaction h
        WHERE
            h.customer_id = current_txn.customer_id
            AND h.transaction_dt < current_txn.transaction_dt
            AND h.transaction_dt >= current_txn.transaction_dt - 2592000
    ) AS customer_avg_amt_30d,

    (
        SELECT STDDEV_SAMP(h.transaction_amt)
        FROM transaction h
        WHERE
            h.customer_id = current_txn.customer_id
            AND h.transaction_dt < current_txn.transaction_dt
            AND h.transaction_dt >= current_txn.transaction_dt - 2592000
    ) AS customer_stddev_amt_30d,

    (
        current_txn.transaction_amt
        -
        (
            SELECT AVG(h.transaction_amt)
            FROM transaction h
            WHERE
                h.customer_id = current_txn.customer_id
                AND h.transaction_dt < current_txn.transaction_dt
                AND h.transaction_dt >= current_txn.transaction_dt - 2592000
        )
    )
    /
    NULLIF(
        (
            SELECT STDDEV_SAMP(h.transaction_amt)
            FROM transaction h
            WHERE
                h.customer_id = current_txn.customer_id
                AND h.transaction_dt < current_txn.transaction_dt
                AND h.transaction_dt >= current_txn.transaction_dt - 2592000
        ),
        0
    ) AS customer_amount_zscore

FROM transaction current_txn

ORDER BY
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_id

LIMIT 100;