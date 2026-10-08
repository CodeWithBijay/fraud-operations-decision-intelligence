SELECT
    current_txn.transaction_id,
    current_txn.customer_id,
    current_txn.transaction_dt,

    (
        SELECT MAX(previous_txn.transaction_dt)
        FROM transaction AS previous_txn
        WHERE
            previous_txn.customer_id =
                current_txn.customer_id
            AND previous_txn.transaction_dt <
                current_txn.transaction_dt
    ) AS previous_transaction_dt,

    (
        current_txn.transaction_dt
        -
        (
            SELECT MAX(previous_txn.transaction_dt)
            FROM transaction AS previous_txn
            WHERE
                previous_txn.customer_id =
                    current_txn.customer_id
                AND previous_txn.transaction_dt <
                    current_txn.transaction_dt
        )
    ) / 3600.0 AS hours_since_previous_txn

FROM transaction AS current_txn

ORDER BY
    current_txn.customer_id,
    current_txn.transaction_dt,
    current_txn.transaction_id

LIMIT 100;