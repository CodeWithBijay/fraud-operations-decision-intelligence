# Baseline Model Implementation

## Objective

Implement the first fraud prediction model using engineered behavioral features.

---

# Modeling Dataset

Dataset:

model_dataset_ml

Rows:

6,907

Training Rows:

5,525

Testing Rows:

1,382

Target Variable:

is_fraud

Fraud Rate:

3.22%

---

# Features Used

Behavioral Features:

- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

Target:

- is_fraud

---

# Baseline Algorithm

Logistic Regression

Reason:

- Simple
- Interpretable
- Industry-standard baseline
- Fast training
- Easy feature coefficient analysis

---

# Modeling Workflow

1. Extract modeling dataset
2. Create train/test split
3. Train logistic regression model
4. Generate predictions
5. Evaluate performance
6. Review feature importance

---

# Evaluation Metrics

Primary Metrics:

- Precision
- Recall
- F1 Score

Secondary Metrics:

- ROC-AUC
- Accuracy

---

# Modeling Risks

## Class Imbalance

Fraud Rate:

3.22%

Potential Mitigation:

- Class weighting
- Oversampling
- Threshold tuning

---

# Expected Deliverables

- Trained baseline model
- Confusion matrix
- Precision score
- Recall score
- F1 score
- ROC-AUC score
- Feature importance review

---

# Success Criteria

The baseline model should outperform random guessing and establish an initial fraud detection benchmark.

---

# Next Phase

Model Evaluation

Feature Importance Analysis

Advanced Modeling