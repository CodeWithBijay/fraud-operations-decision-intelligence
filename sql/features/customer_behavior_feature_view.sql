SELECT
    t.transaction_id,
    t.customer_id,
    t.transaction_dt,
    t.transaction_amt,
    t.is_fraud,

    (
        t.transaction_dt -
        (
            SELECT MAX(h.transaction_dt)
            FROM transaction h
            WHERE h.customer_id = t.customer_id
              AND h.transaction_dt < t.transaction_dt
        )
    ) / 3600.0 AS hours_since_previous_txn,

    (
        SELECT COUNT(*)
        FROM transaction h
        WHERE h.customer_id = t.customer_id
          AND h.transaction_dt < t.transaction_dt
          AND h.transaction_dt >= t.transaction_dt - 86400
    ) AS txn_count_24h,

    (
        SELECT AVG(h.transaction_amt)
        FROM transaction h
        WHERE h.customer_id = t.customer_id
          AND h.transaction_dt < t.transaction_dt
          AND h.transaction_dt >= t.transaction_dt - 2592000
    ) AS customer_avg_amt_30d,

    t.transaction_amt -
    (
        SELECT AVG(h.transaction_amt)
        FROM transaction h
        WHERE h.customer_id = t.customer_id
          AND h.transaction_dt < t.transaction_dt
          AND h.transaction_dt >= t.transaction_dt - 2592000
    ) AS amount_deviation_from_customer_avg,

    (
        t.transaction_amt -
        (
            SELECT AVG(h.transaction_amt)
            FROM transaction h
            WHERE h.customer_id = t.customer_id
              AND h.transaction_dt < t.transaction_dt
              AND h.transaction_dt >= t.transaction_dt - 2592000
        )
    )
    /
    NULLIF(
        (
            SELECT STDDEV_SAMP(h.transaction_amt)
            FROM transaction h
            WHERE h.customer_id = t.customer_id
              AND h.transaction_dt < t.transaction_dt
              AND h.transaction_dt >= t.transaction_dt - 2592000
        ),
        0
    ) AS customer_amount_zscore

FROM transaction t

LIMIT 20;