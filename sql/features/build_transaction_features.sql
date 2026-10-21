-- Builds point-in-time behavioral features for ALL transactions using window functions.
-- Point-in-time rule: only the same customer's transactions with a strictly earlier
-- transaction_dt are used. Same-timestamp transactions are excluded from each other's history.
-- The fraud label is intentionally NOT stored here (kept in the transaction table only).

DROP TABLE IF EXISTS transaction_features;

CREATE TABLE transaction_features AS
WITH w AS (
    SELECT
        t.transaction_id,
        t.customer_id,
        t.account_id,
        t.device_id,
        t.transaction_dt,
        t.transaction_amt,
        MAX(t.transaction_dt)          OVER prior_all AS previous_transaction_dt,
        COUNT(*)                       OVER prior_all AS prior_txn_count,
        COUNT(*)                       OVER prior_24h AS txn_count_24h,
        AVG(t.transaction_amt)         OVER prior_30d AS customer_avg_amt_30d,
        STDDEV_SAMP(t.transaction_amt) OVER prior_30d AS customer_std_amt_30d
    FROM transaction t
    WINDOW
        prior_all AS (PARTITION BY t.customer_id ORDER BY t.transaction_dt
                      RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
        prior_24h AS (PARTITION BY t.customer_id ORDER BY t.transaction_dt
                      RANGE BETWEEN 86400 PRECEDING AND 1 PRECEDING),
        prior_30d AS (PARTITION BY t.customer_id ORDER BY t.transaction_dt
                      RANGE BETWEEN 2592000 PRECEDING AND 1 PRECEDING)
)
SELECT
    transaction_id,
    customer_id,
    account_id,
    device_id,
    transaction_dt,
    transaction_amt,
    prior_txn_count,
    (prior_txn_count = 0) AS cold_start_flag,
    (transaction_dt - previous_transaction_dt) / 3600.0 AS hours_since_previous_txn,
    txn_count_24h,
    customer_avg_amt_30d,
    customer_std_amt_30d,
    transaction_amt - customer_avg_amt_30d AS amount_deviation_from_customer_avg,
    CASE WHEN customer_std_amt_30d > 0
         THEN (transaction_amt - customer_avg_amt_30d) / customer_std_amt_30d
    END AS customer_amount_zscore
FROM w;

ALTER TABLE transaction_features ADD PRIMARY KEY (transaction_id);
CREATE INDEX idx_tf_customer_dt ON transaction_features (customer_id, transaction_dt);