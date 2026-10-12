SELECT
    COUNT(*) AS total_transactions,

    COUNT(hours_since_previous_txn) AS populated_hours_since_previous_txn,

    COUNT(customer_avg_amt_30d) AS populated_customer_avg_amt_30d,

    COUNT(customer_amount_zscore) AS populated_customer_amount_zscore,

    AVG(txn_count_24h) AS avg_txn_count_24h,

    AVG(customer_avg_amt_30d) AS avg_customer_avg_amt_30d,

    AVG(customer_amount_zscore) AS avg_customer_amount_zscore

FROM customer_behavior_feature_view;