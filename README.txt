Fraud Operations Decision Intelligence
Week 7-8 Submission

Author:
Bijay Paudel

Project Purpose:
Develop a fraud operations decision-support system that helps fraud analysts identify potentially fraudulent transactions using engineered behavioral features.

Contents:

1. report.docx
   Main assignment report.

2. sql/
   SQL scripts used for feature engineering, validation, analysis, and dataset preparation.

3. docs/
   Project documentation including:
   - Model Readiness Assessment
   - Train/Test Split Plan
   - Baseline Model Plan

4. data/
   Dataset files and database exports used during the project.

5. src/
   Project source code and future modeling scripts.

Required Software:

- PostgreSQL 17+
- VS Code
- Git

Reproduction Steps:

1. Create and load the fraud_risk_db database.

2. Execute feature engineering SQL scripts.

3. Create customer_behavior_feature_view.

4. Create model_dataset_sample.

5. Create model_dataset_ml.

6. Run validation and analysis queries.

Key Datasets:

- transaction
- customer
- account
- device
- model_dataset_sample
- model_dataset_ml

Modeling Dataset:

Rows: 6,907

Target Variable:
is_fraud

Features:
- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

Notes:

This project uses engineered behavioral features derived from transaction history to support fraud detection analysis.