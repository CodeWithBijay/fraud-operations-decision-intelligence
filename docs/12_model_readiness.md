# Baseline Fraud Model Plan

## Objective

Build the first fraud prediction model using engineered behavioral features.

---

# Dataset

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

---

# Features

Behavioral Features:

- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

Target:

- is_fraud

---

# Modeling Strategy

## Baseline Model

Logistic Regression

Purpose:

Provide an interpretable baseline model that establishes initial fraud detection performance.

---

# Alternative Models

Future candidates:

1. Decision Tree
2. Random Forest
3. XGBoost
4. LightGBM

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

# Expected Outcomes

Determine:

- Whether engineered features contain predictive signal
- Which features contribute most to fraud detection
- Whether additional feature engineering is required

---

# Deliverables

1. Baseline Logistic Regression
2. Performance Metrics
3. Confusion Matrix
4. Feature Importance Analysis
5. Recommendations

---

# Next Phase

Current Status:

✅ Feature Engineering

✅ Feature Validation

✅ Feature Effectiveness

✅ Model Readiness

NEXT:

➡ Train/Test Split Implementation

➡ Baseline Logistic Regression

➡ Model Evaluation