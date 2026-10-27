"""KPI 1 model: probability that a transaction is fraudulent.

KPI supported: fraud value captured at capacity
    = fraud dollars inside the top-K reviewed transactions / all fraud dollars that day.

Algorithm: logistic regression on two groups of predictors known when the transaction happens:
    - 7 point-in-time behavioral features built in this project (amount, velocity, customer history), and
    - IEEE-CIS source attributes: counts C1-C14, time deltas D1 and D15, product code, credit vs. debit.
Why logistic regression:
    - Gives probabilities that can be checked for calibration (needed for expected exposure = p x amount).
    - Linear on the log-odds scale, so every predictor's contribution to a single prediction is exact
      (equal to its SHAP value), which the Fraud Ops Lead can read and challenge.
    - Fast enough to refit many times (bootstrap) to show uncertainty in what-if predictions.
Comparisons (not used by the app):
    - Model A: the same algorithm with behavioral features only (Phase 1 Experiment A vs. B).
    - Gradient boosting on all predictors, to show how much accuracy the explainable model gives up.

Split: chronological. The earliest 70% of time trains the model, the latest 30% tests it,
so the model is always evaluated on transactions that happen after the ones it learned from.

Output: models/fraud_model.joblib and models/fraud_model_metrics.json
Run:    python3 src/modeling/train_fraud_model.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BEHAVIOR_FEATURES, FRAUD_FEATURE_LABELS, FRAUD_FEATURES, MODEL_DIR,  # noqa: E402
                    fraud_design, get_engine, linear_contributions)

SEED = 42
TRAIN_SHARE = 0.70
N_BOOTSTRAP = 30
BOOT_SAMPLE = 200_000
CAPACITIES = [25, 50, 100, 200]

QUERY = """
SELECT f.transaction_id,
       f.transaction_dt,
       f.transaction_amt::float8            AS transaction_amt,
       f.hours_since_previous_txn::float8   AS hours_since_previous_txn,
       f.txn_count_24h,
       f.customer_avg_amt_30d::float8       AS customer_avg_amt_30d,
       f.customer_std_amt_30d::float8       AS customer_std_amt_30d,
       f.customer_amount_zscore::float8     AS customer_amount_zscore,
       f.prior_txn_count,
       f.cold_start_flag,
       t.is_fraud::int                      AS is_fraud,
       t.product_cd, t.card6,
       t.c1, t.c2, t.c3, t.c4, t.c5, t.c6, t.c7, t.c8, t.c9, t.c10, t.c11, t.c12, t.c13, t.c14,
       t.d1, t.d15,
       COALESCE(a.risk_score, 0)            AS risk_score
FROM transaction_features f
JOIN transaction t USING (transaction_id)
LEFT JOIN alert_queue a USING (transaction_id)
"""


def load_data():
    with get_engine().connect() as conn:
        return pd.read_sql(QUERY, conn)


def daily_capture(test, scores, capacities, seed=SEED):
    """Average fraud value captured@K and precision@K across test days, per policy."""
    rng = np.random.default_rng(seed)
    base = pd.DataFrame({
        "day": (test["transaction_dt"] // 86400).to_numpy(),
        "amt": test["transaction_amt"].to_numpy(),
        "fraud": test["is_fraud"].to_numpy(),
    })
    base["fraud_amt"] = base["amt"] * base["fraud"]
    day_fraud = base.groupby("day")["fraud_amt"].transform("sum")
    rows = []
    for name, score in {**scores, "P0 · Random": rng.random(len(base))}.items():
        d = base.assign(score=score, fraud_day=day_fraud)
        d = d.sort_values(["day", "score"], ascending=[True, False])
        d["rank"] = d.groupby("day").cumcount()
        for k in capacities:
            top = d[d["rank"] < k]
            per_day = top.groupby("day").agg(fraud_amt=("fraud_amt", "sum"), hits=("fraud", "sum"),
                                            n=("fraud", "size"), fraud_day=("fraud_day", "first"))
            per_day = per_day[per_day["fraud_day"] > 0]
            rows.append({
                "policy": name, "capacity": k,
                "fraud_value_captured": float((per_day["fraud_amt"] / per_day["fraud_day"]).mean()),
                "precision": float((per_day["hits"] / per_day["n"]).mean()),
                "fraud_dollars_per_day": float(per_day["fraud_amt"].mean()),
            })
    return rows


def main():
    t0 = time.time()
    print("Loading features from PostgreSQL ...")
    df = load_data().sort_values("transaction_dt").reset_index(drop=True)
    print(f"  {len(df):,} transactions, fraud rate {df['is_fraud'].mean():.4f}")

    cutoff = float(df["transaction_dt"].quantile(TRAIN_SHARE))
    train, test = df[df["transaction_dt"] < cutoff], df[df["transaction_dt"] >= cutoff]
    print(f"  train {len(train):,} (days {int(train.transaction_dt.min()//86400)}-"
          f"{int(train.transaction_dt.max()//86400)}), test {len(test):,} (days "
          f"{int(test.transaction_dt.min()//86400)}-{int(test.transaction_dt.max()//86400)})")

    X_train, fill = fraud_design(train)
    X_test, _ = fraud_design(test, fill)
    mu, sd = X_train.mean(axis=0), X_train.std(axis=0)
    sd[sd == 0] = 1.0
    Z_train, Z_test = (X_train - mu) / sd, (X_test - mu) / sd
    y_train, y_test = train["is_fraud"].to_numpy(), test["is_fraud"].to_numpy()

    print("Fitting logistic regression ...")
    lr = LogisticRegression(C=1.0, max_iter=2000)
    lr.fit(Z_train, y_train)
    p_test = lr.predict_proba(Z_test)[:, 1]

    print("Fitting Model A (behavioral features only, for comparison) ...")
    nA = len(BEHAVIOR_FEATURES)
    lr_a = LogisticRegression(C=1.0, max_iter=2000).fit(Z_train[:, :nA], y_train)
    p_a = lr_a.predict_proba(Z_test[:, :nA])[:, 1]

    print(f"Bootstrapping {N_BOOTSTRAP} refits for prediction uncertainty ...")
    rng = np.random.default_rng(SEED)
    boot_coef, boot_int = [], []
    n_boot = min(BOOT_SAMPLE, len(Z_train))
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, len(Z_train), n_boot)
        if y_train[idx].min() == y_train[idx].max():
            continue
        m = LogisticRegression(C=1.0, max_iter=2000).fit(Z_train[idx], y_train[idx])
        boot_coef.append(m.coef_[0])
        boot_int.append(m.intercept_[0])

    print("Fitting gradient boosting (comparison only) ...")
    gb = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1, random_state=SEED)
    gb.fit(X_train, y_train)
    p_gb = gb.predict_proba(X_test)[:, 1]

    rule = test["risk_score"].to_numpy() + test["transaction_amt"].to_numpy() / 1e6  # amount breaks ties
    comparison = {}
    for name, s in {"Logistic regression (selected)": p_test,
                    "Model A: behavior features only": p_a,
                    "Gradient boosting (comparison)": p_gb,
                    "Week 9 rule score": rule, "Transaction amount": test["transaction_amt"].to_numpy()}.items():
        comparison[name] = {"pr_auc": float(average_precision_score(y_test, s)),
                            "roc_auc": float(roc_auc_score(y_test, s))}
    comparison["Logistic regression (selected)"]["brier"] = float(brier_score_loss(y_test, p_test))
    comparison["Gradient boosting (comparison)"]["brier"] = float(brier_score_loss(y_test, p_gb))
    comparison["Model A: behavior features only"]["brier"] = float(brier_score_loss(y_test, p_a))

    bins = pd.qcut(p_test, 10, labels=False, duplicates="drop")
    calib = (pd.DataFrame({"bin": bins, "p": p_test, "y": y_test}).groupby("bin")
             .agg(mean_predicted=("p", "mean"), observed_rate=("y", "mean"), n=("y", "size"))
             .reset_index().to_dict(orient="records"))

    capture = daily_capture(test, {
        "P4 · Expected exposure (p × amount)": p_test * test["transaction_amt"].to_numpy(),
        "P3 · Model probability": p_test,
        "P2 · Rule risk score": rule,
        "P1 · Largest amount": test["transaction_amt"].to_numpy(),
        "Model A exposure (behavior only)": p_a * test["transaction_amt"].to_numpy(),
    }, CAPACITIES)

    coef, intercept = lr.coef_[0], float(lr.intercept_[0])
    base, contrib = linear_contributions(Z_test, coef, intercept, Z_train.mean(axis=0))
    importance = sorted(
        [{"feature": f, "label": FRAUD_FEATURE_LABELS[f], "mean_abs_contribution": float(v),
          "coef_per_sd": float(c), "odds_ratio_per_sd": float(np.exp(c))}
         for f, v, c in zip(FRAUD_FEATURES, np.abs(contrib).mean(axis=0), coef)],
        key=lambda r: -r["mean_abs_contribution"])

    metrics = {
        "model": "Logistic regression (fraud probability)",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": SEED,
        "split": {"cutoff_transaction_dt": cutoff, "train_rows": int(len(train)), "test_rows": int(len(test)),
                  "train_fraud_rate": float(y_train.mean()), "test_fraud_rate": float(y_test.mean())},
        "comparison": comparison,
        "calibration": calib,
        "capture_at_capacity": capture,
        "global_importance": importance,
        "base_log_odds": base,
        "bootstrap_refits": len(boot_coef),
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({
        "features": FRAUD_FEATURES, "labels": FRAUD_FEATURE_LABELS, "fill": fill,
        "scaler_mean": mu, "scaler_sd": sd, "coef": coef, "intercept": intercept,
        "train_mean": Z_train.mean(axis=0), "boot_coef": np.array(boot_coef),
        "boot_intercept": np.array(boot_int), "metrics": metrics,
    }, os.path.join(MODEL_DIR, "fraud_model.joblib"))
    with open(os.path.join(MODEL_DIR, "fraud_model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n=== Test-period performance (later 30% of time) ===")
    for k, v in comparison.items():
        extra = f"  Brier {v['brier']:.4f}" if "brier" in v else ""
        print(f"  {k:34s} PR-AUC {v['pr_auc']:.4f}  ROC-AUC {v['roc_auc']:.4f}{extra}")
    print(f"  (fraud base rate in test: {y_test.mean():.4f} = PR-AUC of a random ranking)")
    print("\n=== KPI 1: fraud value captured at capacity (average per test day) ===")
    cap = pd.DataFrame(capture)
    print(cap.pivot(index="policy", columns="capacity", values="fraud_value_captured").round(3).to_string())
    print("\n=== Global predictor importance, top 15 (mean |contribution| on log-odds scale) ===")
    for r in importance[:15]:
        print(f"  {r['label']:40s} {r['mean_abs_contribution']:.3f}   odds ratio per 1 SD: "
              f"{r['odds_ratio_per_sd']:.2f}")
    print(f"\nSaved models/fraud_model.joblib and models/fraud_model_metrics.json "
          f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
