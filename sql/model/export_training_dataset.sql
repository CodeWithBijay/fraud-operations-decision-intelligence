SELECT
    transaction_id,
    is_fraud,

    hours_since_previous_txn,
    txn_count_24h,
    customer_avg_amt_30d,
    amount_deviation_from_customer_avg,
    customer_amount_zscore

FROM model_dataset_sample;