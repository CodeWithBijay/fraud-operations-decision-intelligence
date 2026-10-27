"""Shared helpers for the Week 10 predictive models.

Both models are linear in a transformed scale (log-odds for fraud, log-count for alert volume),
so each predictor's contribution to one prediction is exact and easy to explain:

    contribution_j = coef_j * (x_j - training_mean_j)
    prediction (link scale) = base value + sum of contributions

For linear models with independent features this equals the SHAP value of each predictor.
The base value is the model's prediction for an "average" training row.
"""
import os

import numpy as np
from sqlalchemy import create_engine

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(ROOT, "models")


def get_engine():
    user = os.environ.get("PGUSER", "fraud_app")
    pwd = os.environ.get("PGPASSWORD", "")
    host = os.environ.get("PGHOST", "localhost")
    db = os.environ.get("PGDATABASE", "fraud_risk_db")
    auth = f"{user}:{pwd}@" if pwd else f"{user}@"
    return create_engine(f"postgresql+psycopg2://{auth}{host}/{db}")


# ------------------------------------------------------------------
# Fraud probability model (KPI 1: fraud value captured at capacity)
# ------------------------------------------------------------------
# Behavioral features built in this project (Weeks 7-9): point-in-time, per customer.
BEHAVIOR_FEATURES = [
    "log_amount",
    "log_hours_since_prev",
    "log_txn_count_24h",
    "log_customer_avg_30d",
    "amount_zscore",
    "log_prior_txn_count",
    "cold_start",
]
# Source attributes from IEEE-CIS, recorded with the transaction (available at prediction time).
C_COLS = [f"c{i}" for i in range(1, 15)]
PRODUCTS = ["W", "C", "R", "H"]  # product S is the reference level
SOURCE_FEATURES = ([f"log_{c}" for c in C_COLS] + ["log_d1", "log_d15", "d15_missing"]
                   + [f"product_{p}" for p in PRODUCTS] + ["credit_card"])
FRAUD_FEATURES = BEHAVIOR_FEATURES + SOURCE_FEATURES
SOURCE_COLUMNS = C_COLS + ["d1", "d15", "product_cd", "card6"]

FRAUD_FEATURE_LABELS = {
    "log_amount": "Transaction amount",
    "log_hours_since_prev": "Hours since previous transaction",
    "log_txn_count_24h": "Transactions in prior 24h",
    "log_customer_avg_30d": "Customer avg amount (30 days)",
    "amount_zscore": "Amount vs. customer's usual (z-score)",
    "log_prior_txn_count": "Customer's prior transaction count",
    "cold_start": "New customer (no history)",
    **{f"log_{c}": f"IEEE count {c.upper()} (anonymized)" for c in C_COLS},
    "log_d1": "IEEE time delta D1 (anonymized)",
    "log_d15": "IEEE time delta D15 (anonymized)",
    "d15_missing": "D15 not recorded",
    **{f"product_{p}": f"Product code {p}" for p in PRODUCTS},
    "credit_card": "Credit card (vs. debit/other)",
}


def _log(df, col):
    return np.log1p(df[col].astype(float).clip(lower=0))


def fraud_design(df, fill=None):
    """Turn raw columns into the model's predictor matrix (columns in FRAUD_FEATURES order).

    Behavioral inputs: transaction_amt, hours_since_previous_txn, txn_count_24h, customer_avg_amt_30d,
    customer_amount_zscore, prior_txn_count, cold_start_flag.
    Source inputs: c1..c14, d1, d15, product_cd, card6.
    Missing numeric values are filled with training medians (z-score with 0); indicator
    predictors (cold_start, d15_missing) tell the model when a value was not available.
    """
    product = df["product_cd"].astype(str)
    X = np.column_stack(
        [
            _log(df, "transaction_amt"),
            _log(df, "hours_since_previous_txn"),
            _log(df, "txn_count_24h"),
            _log(df, "customer_avg_amt_30d"),
            df["customer_amount_zscore"].astype(float).clip(-5, 10),
            _log(df, "prior_txn_count"),
            df["cold_start_flag"].astype(float),
        ]
        + [_log(df, c) for c in C_COLS]
        + [_log(df, "d1"), _log(df, "d15"), df["d15"].isna().astype(float)]
        + [(product == p).astype(float) for p in PRODUCTS]
        + [(df["card6"].astype(str).str.lower() == "credit").astype(float)]
    )
    if fill is None:
        fill = np.nanmedian(X, axis=0)
        fill[FRAUD_FEATURES.index("amount_zscore")] = 0.0  # no history -> neutral
        fill = np.where(np.isnan(fill), 0.0, fill)
    X = np.where(np.isnan(X), fill, X)
    return X, fill


# ------------------------------------------------------------------
# Alert volume model (KPI 2: daily alert overflow)
# ------------------------------------------------------------------
DOW_LEVELS = list(range(1, 7))  # day-of-week 0 is the reference level
VOLUME_FEATURES = ["lag1", "lag7_mean", "trend"] + [f"dow_{d}" for d in DOW_LEVELS]
VOLUME_FEATURE_LABELS = {
    "lag1": "Alerts yesterday",
    "lag7_mean": "Average alerts, previous 7 days",
    "trend": "Day number (trend)",
    **{f"dow_{d}": f"Simulated weekday {d}" for d in DOW_LEVELS},
}


def volume_design(lag1, lag7_mean, day):
    """Predictor matrix for the daily alert-count model."""
    lag1 = np.asarray(lag1, dtype=float)
    lag7_mean = np.asarray(lag7_mean, dtype=float)
    day = np.asarray(day, dtype=float)
    dow = day.astype(int) % 7
    cols = [np.log1p(lag1), np.log1p(lag7_mean), day / 100.0]
    cols += [(dow == d).astype(float) for d in DOW_LEVELS]
    return np.column_stack(cols)


# ------------------------------------------------------------------
# Contributions (exact SHAP values for a linear model)
# ------------------------------------------------------------------
def linear_contributions(X, coef, intercept, mean):
    """Return (base value, contributions matrix) on the model's link scale."""
    X = np.atleast_2d(X)
    base = float(intercept + np.dot(coef, mean))
    contrib = (X - mean) * coef
    return base, contrib


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))
