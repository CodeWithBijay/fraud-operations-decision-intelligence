# Model Readiness Assessment

## Purpose

This document evaluates whether the engineered fraud dataset is ready for machine learning model development.

The assessment covers:

- Dataset size
- Feature availability
- Class distribution
- Missing value analysis
- Modeling readiness decision

---

# Dataset Summary

Dataset Name:

model_dataset_sample

Source:

customer_behavior_feature_view

Total Rows:

10,000

Target Variable:

is_fraud

Features Included:

- hours_since_previous_txn
- txn_count_24h
- customer_avg_amt_30d
- amount_deviation_from_customer_avg
- customer_amount_zscore

---

# Class Distribution Analysis

## Query

```sql
SELECT
    is_fraud,
    COUNT(*) AS transaction_count
FROM model_dataset_sample
GROUP BY is_fraud
ORDER BY is_fraud;
```

## Results

| is_fraud | Transaction Count |
|-----------|------------------:|
| 0 | 9,678 |
| 1 | 322 |

Total Transactions:

10,000

Fraud Transactions:

322

Non-Fraud Transactions:

9,678

Fraud Rate:

3.22%

Non-Fraud Rate:

96.78%

## Observation

The dataset is highly imbalanced.

This behavior is expected in fraud detection because fraudulent transactions occur much less frequently than legitimate transactions.

---

# Feature Completeness Analysis

## Query

```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(hours_s*nce_previous_txn) AS hours_populat*d,
    COUNT(customer_avg_amt_30d)*AS avg_populated,
    COUNT(custom*r_amount_zscore) AS zscore_populat*d
FROM model_dataset_sample;
```

*# Results

| Metric | Count |
|---*------|-------:|
| Total Rows | 10*000 |
| hours_since_previous_txn P*pulated | 8,863 |
| customer_avg_a*t_30d Populated | 8,096 |
| custom*r_amount_zscore Populated | 6,907 *

---

# Missing Value Analysis

#* hours_since_previous_txn

Populat*d:

8,863

Missing:

1,137

Reason*

Customers with no prior transact*on history cannot have a previous *ransaction interval.

---

## cust*mer_avg_amt_30d

Populated:

8,096*
Missing:

1,904

Reason:

Some cu*tomers do not have enough historic*l transactions within the 30-day l*okback window.

---

## customer_a*ount_zscore

Populated:

6,907

Mi*sing:

3,093

Reason:

Z-score req*ires:

- historical transaction hi*tory
- a historical average
- a no*-zero historical standard deviatio*

When those requirements are not *atisfied, the feature is NULL.

--*

# Modeling Dataset Preparation

*o simplify baseline modeling, rows*containing NULL values in critical*behavioral features were removed.
*## Query

```sql
DROP TABLE IF EXI*TS model_dataset_ml;

CREATE TABLE*model_dataset_ml AS
SELECT *
FROM *odel_dataset_sample
WHERE
    hour*_since_previous_txn IS NOT NULL
  * AND customer_avg_amt_30d IS NOT N*LL
    AND customer_amount_zscore *S NOT NULL;
```

## Result

Rows R*tained:

6,907

Rows Removed:

3,0*3

Retention Rate:

69.07%

---

#*Feature Effectiveness Findings

##*TxnCount_24h

Observed Result:

| *s_fraud | Average TxnCount_24h |
|*----------|---------------------:|*| 0 | 2.4219 |
| 1 | 2.9882 |

Obs*rvation:

Fraudulent transactions *xhibit higher recent transaction a*tivity than non-fraudulent transac*ions.

Conclusion:

TxnCount_24h d*monstrates predictive signal and s*ould be retained for modeling.

--*

# Modeling Readiness Decision

#* Status

READY FOR BASELINE MODEL *EVELOPMENT

The dataset now contai*s:

- Target variable
- Validated *ehavioral features
- Reduced missi*g values
- Fraud observations avai*able for training and testing
- Su*ficient sample size for baseline e*perimentation

---

# Risks and Co*siderations

## Class Imbalance

F*aud represents only 3.22% of obser*ations.

Future modeling work may *equire:

- class weighting
- overs*mpling
- undersampling
- threshold*tuning

## Feature Quality

Custom*rAmountZScore showed evidence of e*treme values during exploratory an*lysis.

Additional feature review *ay be required before production u*e.

---

# Next Steps

1. Create T*ain/Test Split
2. Build Baseline Fraud Model
3. Evaluate Model Performance
4. Analyze Feature Importance
5. Improve Feature Engineering
6. Build Production Modeling Dataset

---

# Project Status

✅ Data Validation

✅ Feature Engineering

✅ Feature Validation

✅ Feature Effectiveness Analysis

✅ Feature Dataset Construction

✅ Model Readiness Assessment

NEXT:

➡ Train/Test Split

➡ Baseline Fraud Model

➡ Model Evaluation