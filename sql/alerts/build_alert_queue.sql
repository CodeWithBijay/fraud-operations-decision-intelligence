-- Week 9 alert queue: transparent, label-free rule score.
-- Thresholds are percentiles of the feature distributions; isFraud is NOT used.

DROP TABLE IF EXISTS alert_queue;
DROP TABLE IF EXISTS alert_rule_config;

CREATE TABLE alert_rule_config AS
SELECT 'R1' AS rule_code, 'High 24h velocity' AS rule_name,
       'txn_count_24h >= 95th percentile' AS rule_text,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY txn_count_24h)::numeric AS threshold,
       'Data-driven percentile (label-free)' AS basis
FROM transaction_features
UNION ALL
SELECT 'R2', 'Amount spike', 'customer_amount_zscore >= 3', 3,
       'Statistical convention (explicit assumption)'
UNION ALL
SELECT 'R3', 'Rapid repeat', 'hours_since_previous_txn <= 5th percentile',
       PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY hours_since_previous_txn)::numeric,
       'Data-driven percentile (label-free)'
FROM transaction_features WHERE hours_since_previous_txn IS NOT NULL
UNION ALL
SELECT 'R4', 'New customer', 'cold_start_flag = TRUE', NULL, 'No prior history'
UNION ALL
SELECT 'R5', 'Large amount', 'transaction_amt >= 95th percentile',
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY transaction_amt)::numeric,
       'Data-driven percentile (label-free)'
FROM transaction_features
UNION ALL
SELECT 'R6', 'New device', 'first use of device by an existing customer', NULL, 'Device history';

CREATE TABLE alert_queue AS
WITH th AS (
    SELECT
        MAX(threshold) FILTER (WHERE rule_code = 'R1') AS t_velocity,
        MAX(threshold) FILTER (WHERE rule_code = 'R3') AS t_gap,
        MAX(threshold) FILTER (WHERE rule_code = 'R5') AS t_amount
    FROM alert_rule_config
),
dev AS (
    SELECT transaction_id,
           (device_id IS NOT NULL
            AND prior_txn_count > 0
            AND transaction_dt = MIN(transaction_dt) OVER (PARTITION BY customer_id, device_id)
           ) AS is_new_device
    FROM transaction_features
),
scored AS (
    SELECT f.*,
           (f.txn_count_24h >= th.t_velocity)                                AS r1_velocity,
           (COALESCE(f.customer_amount_zscore, 0) >= 3)                      AS r2_amount_spike,
           (COALESCE(f.hours_since_previous_txn, 1e9) <= th.t_gap)          AS r3_rapid_repeat,
           f.cold_start_flag                                                 AS r4_new_customer,
           (f.transaction_amt >= th.t_amount)                                AS r5_large_amount,
           COALESCE(d.is_new_device, FALSE)                                  AS r6_new_device
    FROM transaction_features f
    JOIN dev d USING (transaction_id)
    CROSS JOIN th
)
SELECT
    transaction_id, customer_id, device_id, transaction_dt,
    (transaction_dt / 86400)::int AS sim_day,
    transaction_amt,
    hours_since_previous_txn, txn_count_24h, customer_avg_amt_30d, customer_amount_zscore,
    r1_velocity, r2_amount_spike, r3_rapid_repeat, r4_new_customer, r5_large_amount, r6_new_device,
    (r1_velocity::int + r2_amount_spike::int + r3_rapid_repeat::int
     + r4_new_customer::int + r5_large_amount::int + r6_new_device::int) AS risk_score,
    CONCAT_WS(', ',
        CASE WHEN r1_velocity     THEN 'High 24h velocity' END,
        CASE WHEN r2_amount_spike THEN 'Amount spike' END,
        CASE WHEN r3_rapid_repeat THEN 'Rapid repeat' END,
        CASE WHEN r4_new_customer THEN 'New customer' END,
        CASE WHEN r5_large_amount THEN 'Large amount' END,
        CASE WHEN r6_new_device   THEN 'New device' END) AS reasons
FROM scored
WHERE (r1_velocity::int + r2_amount_spike::int + r3_rapid_repeat::int
       + r4_new_customer::int + r5_large_amount::int + r6_new_device::int) >= 2;

ALTER TABLE alert_queue ADD PRIMARY KEY (transaction_id);
CREATE INDEX idx_aq_day ON alert_queue (sim_day);