-- 1. Every transaction has exactly one feature row
SELECT
    (SELECT COUNT(*) FROM transaction)          AS transaction_rows,
    (SELECT COUNT(*) FROM transaction_features) AS feature_rows;

-- 2. Logical checks (all violation counts should be 0)
SELECT
    COUNT(*) FILTER (WHERE hours_since_previous_txn <= 0)                        AS nonpositive_gap,
    COUNT(*) FILTER (WHERE txn_count_24h < 0 OR txn_count_24h > prior_txn_count)  AS bad_24h_count,
    COUNT(*) FILTER (WHERE cold_start_flag AND hours_since_previous_txn IS NOT NULL) AS cold_start_mismatch,
    COUNT(*) FILTER (WHERE cold_start_flag)                                       AS cold_start_rows
FROM transaction_features;

-- 3. Agreement with the original validated feature view (10,000-row sample)
SELECT
    COUNT(*) AS compared_rows,
    COUNT(*) FILTER (WHERE f.txn_count_24h IS DISTINCT FROM s.txn_count_24h) AS txn_count_24h_diff,
    COUNT(*) FILTER (WHERE ABS(COALESCE(f.hours_since_previous_txn, -1) - COALESCE(s.hours_since_previous_txn, -1)) > 0.0001) AS hours_diff,
    COUNT(*) FILTER (WHERE ABS(COALESCE(f.customer_avg_amt_30d, -1) - COALESCE(s.customer_avg_amt_30d, -1)) > 0.0001) AS avg_30d_diff,
    COUNT(*) FILTER (WHERE ABS(COALESCE(f.customer_amount_zscore, -999) - COALESCE(s.customer_amount_zscore, -999)) > 0.0001) AS zscore_diff
FROM model_dataset_sample s
JOIN transaction_features f USING (transaction_id);