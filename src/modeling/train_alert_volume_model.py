"""KPI 2 model: number of fraud alerts expected tomorrow.

KPI supported: daily alert overflow
    = alerts that exceed the team's review capacity on a day (max(alerts - capacity, 0)).

Algorithm: Poisson regression (a count model) with a negative-binomial prediction interval.
    - Alert volume is a count, never negative, and its spread grows with its level: Poisson fits that.
    - Predictors: yesterday's alerts, the previous 7-day average, the simulated weekday and a trend term.
      These are all known the evening before, so the forecast can be used to plan staffing.
    - Linear on the log scale, so each predictor's contribution is exact and multiplies the forecast.
    - Day-to-day counts vary more than a pure Poisson allows (overdispersion); the interval uses a
      negative binomial with the dispersion measured on training days, so the band is honest.

Split: chronological, first 70% of days train, last 30% test (one-day-ahead forecasts).
Compared against two simple baselines: "same as yesterday" and "previous 7-day average".

Output: models/alert_volume_model.joblib and models/alert_volume_metrics.json
Run:    python3 src/modeling/train_alert_volume_model.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson
from sklearn.linear_model import PoissonRegressor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (MODEL_DIR, VOLUME_FEATURE_LABELS, VOLUME_FEATURES, get_engine,  # noqa: E402
                    linear_contributions, volume_design)

TRAIN_SHARE = 0.70
CAPACITIES = [50, 100, 150]
INTERVAL = 0.90


def load_daily():
    with get_engine().connect() as conn:
        return pd.read_sql("SELECT sim_day, COUNT(*) AS alerts FROM alert_queue GROUP BY sim_day", conn)


def count_dist(mu, phi):
    """Predictive distribution for a count with mean mu and dispersion phi (variance = phi * mu)."""
    if phi <= 1.0001:
        return poisson(mu)
    r = mu / (phi - 1.0)
    return nbinom(r, r / (r + mu))


def expected_overflow(dist, capacity):
    k = np.arange(capacity + 1, int(dist.ppf(0.9999)) + 2)
    return float(np.sum((k - capacity) * dist.pmf(k)))


def main():
    daily = load_daily()
    days = np.arange(int(daily["sim_day"].min()), int(daily["sim_day"].max()) + 1)
    s = daily.set_index("sim_day")["alerts"].reindex(days, fill_value=0).astype(float)
    frame = pd.DataFrame({"day": days, "alerts": s.to_numpy(),
                          "lag1": s.shift(1).to_numpy(),
                          "lag7_mean": s.shift(1).rolling(7).mean().to_numpy()}).dropna().reset_index(drop=True)

    n_train = int(len(frame) * TRAIN_SHARE)
    train, test = frame.iloc[:n_train], frame.iloc[n_train:]
    X_train = volume_design(train["lag1"], train["lag7_mean"], train["day"])
    X_test = volume_design(test["lag1"], test["lag7_mean"], test["day"])
    y_train, y_test = train["alerts"].to_numpy(), test["alerts"].to_numpy()

    model = PoissonRegressor(alpha=1e-6, max_iter=1000).fit(X_train, y_train)
    mu_train = model.predict(X_train)
    phi = float(max(np.sum((y_train - mu_train) ** 2 / mu_train) / (len(y_train) - X_train.shape[1] - 1), 1.0))

    mu_test = model.predict(X_test)
    lo_q, hi_q = (1 - INTERVAL) / 2, 1 - (1 - INTERVAL) / 2
    dists = [count_dist(m, phi) for m in mu_test]
    lo = np.array([d.ppf(lo_q) for d in dists])
    hi = np.array([d.ppf(hi_q) for d in dists])

    def mae(p):
        return float(np.mean(np.abs(y_test - p)))

    def mape(p):
        return float(np.mean(np.abs(y_test - p) / np.maximum(y_test, 1)))

    comparison = {
        "Poisson regression (selected)": {"mae": mae(mu_test), "mape": mape(mu_test)},
        "Baseline: same as yesterday": {"mae": mae(test["lag1"].to_numpy()), "mape": mape(test["lag1"].to_numpy())},
        "Baseline: previous 7-day average": {"mae": mae(test["lag7_mean"].to_numpy()),
                                             "mape": mape(test["lag7_mean"].to_numpy())},
    }
    coverage = float(np.mean((y_test >= lo) & (y_test <= hi)))

    overflow = []
    for c in CAPACITIES:
        p_over = np.array([1 - d.cdf(c) for d in dists])
        actual_over = y_test > c
        overflow.append({
            "capacity": c,
            "actual_overflow_days": int(actual_over.sum()),
            "predicted_overflow_days_p_over_50pct": int((p_over > 0.5).sum()),
            "overflow_day_accuracy": float(np.mean((p_over > 0.5) == actual_over)),
            "avg_actual_overflow_alerts": float(np.mean(np.maximum(y_test - c, 0))),
            "avg_predicted_overflow_alerts": float(np.mean([expected_overflow(d, c) for d in dists])),
        })

    coef, intercept = model.coef_, float(model.intercept_)
    train_mean = X_train.mean(axis=0)
    _, contrib = linear_contributions(X_test, coef, intercept, train_mean)
    importance = sorted(
        [{"feature": f, "label": VOLUME_FEATURE_LABELS[f], "mean_abs_contribution": float(v),
          "coef": float(c), "multiplier": float(np.exp(c))}
         for f, v, c in zip(VOLUME_FEATURES, np.abs(contrib).mean(axis=0), coef)],
        key=lambda r: -r["mean_abs_contribution"])

    test_table = pd.DataFrame({"day": test["day"].astype(int), "actual": y_test, "predicted": mu_test,
                               "lower": lo, "upper": hi})
    metrics = {
        "model": "Poisson regression (daily alert volume)",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split": {"train_days": [int(train["day"].min()), int(train["day"].max())],
                  "test_days": [int(test["day"].min()), int(test["day"].max())]},
        "dispersion_phi": phi,
        "interval": INTERVAL,
        "interval_coverage_test": coverage,
        "comparison": comparison,
        "overflow_kpi": overflow,
        "global_importance": importance,
        "test_predictions": test_table.to_dict(orient="records"),
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump({
        "features": VOLUME_FEATURES, "labels": VOLUME_FEATURE_LABELS, "coef": coef, "intercept": intercept,
        "train_mean": train_mean, "phi": phi, "interval": INTERVAL,
        "history": s.to_dict(), "metrics": metrics,
    }, os.path.join(MODEL_DIR, "alert_volume_model.joblib"))
    with open(os.path.join(MODEL_DIR, "alert_volume_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Days: train {metrics['split']['train_days']}, test {metrics['split']['test_days']}")
    print(f"Dispersion (variance / mean): {phi:.2f}  -> {'negative binomial' if phi > 1 else 'Poisson'} interval")
    print("\n=== One-day-ahead forecast accuracy on test days ===")
    for k, v in comparison.items():
        print(f"  {k:34s} MAE {v['mae']:6.1f} alerts   MAPE {v['mape']:.1%}")
    print(f"  {int(INTERVAL * 100)}% prediction interval contained the actual count on {coverage:.0%} of test days")
    print("\n=== KPI 2: daily alert overflow on test days ===")
    print(pd.DataFrame(overflow).round(3).to_string(index=False))
    print("\n=== Global predictor importance (mean |contribution| on log scale) ===")
    for r in importance:
        print(f"  {r['label']:34s} {r['mean_abs_contribution']:.3f}   multiplier per unit: {r['multiplier']:.2f}")
    print("\nSaved models/alert_volume_model.joblib and models/alert_volume_metrics.json")


if __name__ == "__main__":
    main()
