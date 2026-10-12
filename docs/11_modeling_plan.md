# Fraud Modeling Plan

Dataset:

model_dataset_sample

Rows:

10,000

Target:

is_fraud

Features:

- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

Split:

80% Train
20% Test

Goal:

Predict fraudulent transactions.