# Train/Test Split

Source Dataset:

model_dataset_ml

Rows:

6907

Target:

is_fraud

Features:

- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

Split Strategy:

80% Training
20% Testing

Purpose:

Evaluate fraud prediction performance on unseen transactions.