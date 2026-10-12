SELECT
    is_fraud,

    COUNT(*) AS transaction_count,

    AVG(txn_count_24h) AS avg_txn_count_24h,

    AVG(hours_since_previous_txn) AS avg_hours_since_previous_txn,

    AVG(customer_avg_amt_30d) AS avg_customer_avg_amt_30d,

    AVG(amount_deviation_from_customer_avg) AS avg_amount_deviation,

    AVG(customer_amount_zscore) AS avg_customer_amount_zscore

FROM customer_behavior_feature_view

GROUP BY is_fraud

ORDER BY is_fraud;                                                                                                                                            