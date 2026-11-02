"""Shared helpers for the predictive models (Weeks 10-11).

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

# Week 11 candidate improvement: more IEEE-CIS attributes recorded with the transaction.
EXTRA_D = ["d10", "d11", "d12", "d13", "d14"]
EMAIL_GROUPS = ["gmail.com", "yahoo.com", "hotmail.com", "anonymous.com", "outlook.com"]  # other = reference
CARD_NETWORKS = ["mastercard", "american express", "discover"]  # visa and other = reference
EXTENDED_FEATURES = ([f"log_{d}" for d in EXTRA_D] + [f"{d}_missing" for d in EXTRA_D]
                     + [f"email_{e.split('.')[0]}" for e in EMAIL_GROUPS] + ["email_missing"]
                     + [f"card_{n.replace(' ', '_')}" for n in CARD_NETWORKS])
FRAUD_FEATURE_LABELS.update({
    **{f"log_{d}": f"IEEE time delta {d.upper()} (anonymized)" for d in EXTRA_D},
    **{f"{d}_missing": f"{d.upper()} not recorded" for d in EXTRA_D},
    **{f"email_{e.split('.')[0]}": f"Purchaser email {e}" for e in EMAIL_GROUPS},
    "email_missing": "Purchaser email not recorded",
    **{f"card_{n.replace(' ', '_')}": f"Card network: {n.title()}" for n in CARD_NETWORKS},
})
FEATURE_SETS = {
    "week10": FRAUD_FEATURES,
    "week11_extended": FRAUD_FEATURES + EXTENDED_FEATURES,
}
# Every source column any feature set may need (the app always loads all of them).
SOURCE_COLUMNS_ALL = SOURCE_COLUMNS + EXTRA_D + ["p_emaildomain", "card4"]

# Raw inputs a user can edit in the what-if analysis (used for plausible-range checks).
RAW_INPUTS = ["transaction_amt", "hours_since_previous_txn", "txn_count_24h", "customer_avg_amt_30d",
              "prior_txn_count"]


def raw_ranges(df):
    """1st-99th percentile of each editable raw input: the range the model has seen often."""
    out = {}
    for c in RAW_INPUTS:
        v = df[c].astype(float).dropna()
        out[c] = {"p01": float(v.quantile(0.01)), "p99": float(v.quantile(0.99)),
                  "min": float(v.min()), "max": float(v.max())}
    return out


def _log(df, col):
    return np.log1p(df[col].astype(float).clip(lower=0))


def fraud_design(df, fill=None, feature_set="week10"):
    """Turn raw columns into the model's predictor matrix (columns in FEATURE_SETS[feature_set] order).

    Behavioral inputs: transaction_amt, hours_since_previous_txn, txn_count_24h, customer_avg_amt_30d,
    customer_amount_zscore, prior_txn_count, cold_start_flag.
    Source inputs: c1..c14, d1, d15, product_cd, card6 (plus d10-d14, p_emaildomain, card4 for
    the week11_extended set).
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
    if feature_set == "week11_extended":
        email = df["p_emaildomain"].astype(str).str.lower()
        network = df["card4"].astype(str).str.lower()
        extra = ([_log(df, d) for d in EXTRA_D] + [df[d].isna().astype(float) for d in EXTRA_D]
                 + [(email == e).astype(float) for e in EMAIL_GROUPS]
                 + [df["p_emaildomain"].isna().astype(float)]
                 + [(network == n).astype(float) for n in CARD_NETWORKS])
        X = np.column_stack([X] + extra)
    elif feature_set != "week10":
        raise ValueError(f"Unknown feature set: {feature_set}")
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
    "lag2": "Alerts two days ago",
    "lag7": "Alerts on the same weekday last week",
}
VOLUME_SETS = {
    "week10": VOLUME_FEATURES,
    "week11_lags": ["lag1", "lag7_mean", "lag2", "lag7", "trend"] + [f"dow_{d}" for d in DOW_LEVELS],
}


def volume_design(lag1, lag7_mean, day, lag2=None, lag7=None, feature_set="week10"):
    """Predictor matrix for the daily alert-count model."""
    lag1 = np.asarray(lag1, dtype=float)
    lag7_mean = np.asarray(lag7_mean, dtype=float)
    day = np.asarray(day, dtype=float)
    dow = day.astype(int) % 7
    cols = [np.log1p(lag1), np.log1p(lag7_mean)]
    if feature_set == "week11_lags":
        cols += [np.log1p(np.asarray(lag2, dtype=float)), np.log1p(np.asarray(lag7, dtype=float))]
    elif feature_set != "week10":
        raise ValueError(f"Unknown feature set: {feature_set}")
    cols += [day / 100.0] + [(dow == d).astype(float) for d in DOW_LEVELS]
    return np.column_stack(cols)


def volume_lags(history, day):
    """Inputs known the evening before `day`, from a {day: alert count} history."""
    prev = [history.get(d, np.nan) for d in range(day - 7, day)]
    return {"lag1": float(history.get(day - 1, np.nan)), "lag7_mean": float(np.nanmean(prev)),
            "lag2": float(history.get(day - 2, np.nan)), "lag7": float(history.get(day - 7, np.nan))}


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
