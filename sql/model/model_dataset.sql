DROP TABLE IF EXISTS model_dataset;

CREATE TABLE model_dataset AS
SELECT
    transaction_id,
    customer_id,
    transaction_dt,
    transaction_amt,
    is_fraud,
    hours_since_previous_txn,
    txn_count_24h,
    customer_avg_amt_30d,
    amount_deviation_from_customer_avg,
    customer_amount_zscore
FROM customer_behavior_feature_view;