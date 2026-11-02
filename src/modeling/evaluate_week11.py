"""Week 11: model evaluation, error analysis and one improvement per KPI model.

Design (decided before looking at any results)
    Time is split three ways, oldest to newest:
        development (train)  earliest 60% of time
        validation           next 15%  -> every modeling choice is made here
        final test           latest 25% -> used once, after the choice is fixed

    Selection rules (pre-registered)
        Fraud model:  keep the candidate only if it raises validation fraud value captured at
                      50 reviews/day (expected-exposure ranking) by at least 0.5 percentage points;
                      otherwise keep the Week 10 specification (simpler model wins ties).
        Volume model: keep the candidate only if it lowers validation mean absolute error by at
                      least 2%; otherwise keep the Week 10 specification.

Run:
    python3 src/modeling/evaluate_week11.py --validation-only   (Step 4: choose models, no test data used)
    python3 src/modeling/evaluate_week11.py                     (Step 5: final test once, error analysis, save)
"""
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BEHAVIOR_FEATURES, FEATURE_SETS, FRAUD_FEATURE_LABELS, MODEL_DIR, ROOT,  # noqa: E402
                    VOLUME_FEATURE_LABELS, VOLUME_SETS, fraud_design, get_engine, linear_contributions,
                    raw_ranges, volume_design)

VALIDATION_ONLY = "--validation-only" in sys.argv
SEED = 42
DEV_END, VAL_END = 0.60, 0.75
CAPACITIES = [25, 50, 100, 200]
SELECT_CAPACITY = 50
N_BOOTSTRAP = 30
BOOT_SAMPLE = 200_000
VOLUME_CAPACITIES = [50, 100, 150]
INTERVAL = 0.90
OUT_DIR = os.path.join(ROOT, "reports", "week11")

FRAUD_QUERY = """
SELECT f.transaction_id, f.transaction_dt,
       f.transaction_amt::float8 AS transaction_amt,
       f.hours_since_previous_txn::float8 AS hours_since_previous_txn,
       f.txn_count_24h, f.customer_avg_amt_30d::float8 AS customer_avg_amt_30d,
       f.customer_std_amt_30d::float8 AS customer_std_amt_30d,
       f.customer_amount_zscore::float8 AS customer_amount_zscore,
       f.prior_txn_count, f.cold_start_flag,
       t.is_fraud::int AS is_fraud,
       t.product_cd, t.card4, t.card6, t.p_emaildomain,
       t.c1, t.c2, t.c3, t.c4, t.c5, t.c6, t.c7, t.c8, t.c9, t.c10, t.c11, t.c12, t.c13, t.c14,
       t.d1, t.d10, t.d11, t.d12, t.d13, t.d14, t.d15,
       COALESCE(a.risk_score, 0) AS risk_score
FROM transaction_features f
JOIN transaction t USING (transaction_id)
LEFT JOIN alert_queue a USING (transaction_id)
"""
CANDIDATE_LABELS = {"week10": "Week 10 model (behavior + IEEE attributes)",
                    "week11_extended": "Candidate: + more IEEE attributes (D10-D14, email, card network)"}
VOLUME_LABELS = {"week10": "Week 10 model (yesterday, 7-day average, weekday, trend)",
                 "week11_lags": "Candidate: + alerts two days ago and same weekday last week"}


def fit_logit(X, y):
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    m = LogisticRegression(C=1.0, max_iter=3000).fit(Z, y)
    return {"mu": mu, "sd": sd, "coef": m.coef_[0], "intercept": float(m.intercept_[0]), "z_mean": Z.mean(axis=0)}


def predict_logit(fit, X):
    Z = (X - fit["mu"]) / fit["sd"]
    return 1.0 / (1.0 + np.exp(-(fit["intercept"] + Z @ fit["coef"])))


def daily_capture(df, score, capacities):
    """Average fraud value captured@K and precision@K across days, for one ranking."""
    d = pd.DataFrame({"day": (df["transaction_dt"] // 86400).to_numpy(), "amt": df["transaction_amt"].to_numpy(),
                      "fraud": df["is_fraud"].to_numpy(), "score": score})
    d["fraud_amt"] = d["amt"] * d["fraud"]
    d["fraud_day"] = d.groupby("day")["fraud_amt"].transform("sum")
    d = d.sort_values(["day", "score"], ascending=[True, False])
    d["rank"] = d.groupby("day").cumcount()
    rows, per_day = {}, {}
    for k in capacities:
        top = d[d["rank"] < k].groupby("day").agg(fraud_amt=("fraud_amt", "sum"), hits=("fraud", "sum"),
                                                  n=("fraud", "size"), fraud_day=("fraud_day", "first"))
        top = top[top["fraud_day"] > 0]
        cap = top["fraud_amt"] / top["fraud_day"]
        rows[k] = {"fraud_value_captured": float(cap.mean()), "precision": float((top["hits"] / top["n"]).mean())}
        per_day[k] = cap
    return rows, per_day


def fraud_scores(df, p):
    amt = df["transaction_amt"].to_numpy()
    return {"P4 · Expected exposure (p × amount)": p * amt,
            "P3 · Model probability": p,
            "P2 · Rule risk score": df["risk_score"].to_numpy() + amt / 1e6,
            "P1 · Largest amount": amt,
            "P0 · Random": np.random.default_rng(SEED).random(len(df))}


def classification_metrics(y, p):
    return {"pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p)),
            "brier": float(brier_score_loss(y, p))}


def count_dist(mu, phi):
    if phi <= 1.0001:
        return poisson(mu)
    r = mu / (phi - 1.0)
    return nbinom(r, r / (r + mu))


def section(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# ----------------------------------------------------------------------------
# Fraud model (KPI 1)
# ----------------------------------------------------------------------------
def evaluate_fraud(df):
    out = {}
    df = df.sort_values("transaction_dt").reset_index(drop=True)
    q_dev, q_val = df["transaction_dt"].quantile([DEV_END, VAL_END])
    dev = df[df.transaction_dt < q_dev]
    val = df[(df.transaction_dt >= q_dev) & (df.transaction_dt < q_val)]
    test = df[df.transaction_dt >= q_val]
    out["split"] = {name: {"rows": int(len(x)), "first_day": int(x.transaction_dt.min() // 86400),
                           "last_day": int(x.transaction_dt.max() // 86400), "fraud_rate": float(x.is_fraud.mean())}
                    for name, x in [("development", dev), ("validation", val), ("final_test", test)]}
    with open(os.path.join(OUT_DIR, "split_and_leakage.json")) as f:
        sl = json.load(f)
    out["leakage_checks"] = [{"check": c["check"], "result": c["pass"], "detail": c["detail"]} for c in sl["checks"]]
    out["leakage_caveats"] = [
        "Alert-rule thresholds (Week 9) were percentiles of the full period, so the rule-score baseline "
        "carries slight look-ahead; the fraud model does not use the rule score.",
        "C and D variables are anonymized by the data provider; their timing cannot be verified "
        "independently. They are treated as recorded at transaction time, as documented by the provider.",
    ]

    section("FRAUD MODEL — development (trained on development, scored on validation)")
    y_dev, y_val = dev["is_fraud"].to_numpy(), val["is_fraud"].to_numpy()
    dev_rows = []
    for fs in ["week10", "week11_extended"]:
        Xd, fill = fraud_design(dev, feature_set=fs)
        Xv, _ = fraud_design(val, fill, feature_set=fs)
        p = predict_logit(fit_logit(Xd, y_dev), Xv)
        cap, _ = daily_capture(val, p * val["transaction_amt"].to_numpy(), [SELECT_CAPACITY])
        dev_rows.append({"model": CANDIDATE_LABELS[fs], "feature_set": fs, "predictors": len(FEATURE_SETS[fs]),
                         **classification_metrics(y_val, p),
                         "captured_at_50": cap[SELECT_CAPACITY]["fraud_value_captured"]})
    Xd, fill = fraud_design(dev)
    Xv, _ = fraud_design(val, fill)
    nA = len(BEHAVIOR_FEATURES)
    pa = predict_logit(fit_logit(Xd[:, :nA], y_dev), Xv[:, :nA])
    amt_val = val["transaction_amt"].to_numpy()
    for name, s, rank in [("Behavior features only", pa, pa * amt_val),
                          ("Baseline: largest amount", amt_val, amt_val),
                          ("Baseline: Week 9 rule score", val["risk_score"].to_numpy() + amt_val / 1e6,
                           val["risk_score"].to_numpy() + amt_val / 1e6)]:
        cap, _ = daily_capture(val, rank, [SELECT_CAPACITY])
        dev_rows.append({"model": name, "feature_set": "-", "predictors": nA if name.startswith("Behavior") else 1,
                         "pr_auc": float(average_precision_score(y_val, s)), "roc_auc": float(roc_auc_score(y_val, s)),
                         "brier": float(brier_score_loss(y_val, s)) if name.startswith("Behavior") else None,
                         "captured_at_50": cap[SELECT_CAPACITY]["fraud_value_captured"]})
    dev_table = pd.DataFrame(dev_rows)
    print(dev_table.drop(columns=["feature_set"]).round(4).to_string(index=False))
    base_cap, cand_cap = dev_rows[0]["captured_at_50"], dev_rows[1]["captured_at_50"]
    gain = (cand_cap - base_cap) * 100
    selected = "week11_extended" if gain >= 0.5 else "week10"
    decision = (f"Validation capture at 50 reviews/day: Week 10 {base_cap:.1%}, candidate {cand_cap:.1%} "
                f"({gain:+.1f} points). Rule: keep the candidate only if the gain is at least 0.5 points. "
                f"Selected: {CANDIDATE_LABELS[selected]}.")
    print("\n  DECISION:", decision)
    out["development"] = dev_rows
    out["selection"] = {"rule": "Keep candidate if validation capture@50 (expected exposure) improves by >= 0.5 "
                                "points; otherwise keep the Week 10 specification.",
                        "decision": decision, "selected_feature_set": selected,
                        "candidate_retained": selected != "week10"}
    dev_table.to_csv(os.path.join(OUT_DIR, "fraud_validation_comparison.csv"), index=False)
    if VALIDATION_ONLY:
        return out

    section("FRAUD MODEL — final test (refit on development + validation, evaluated once)")
    trv = pd.concat([dev, val])
    y_trv, y_test = trv["is_fraud"].to_numpy(), test["is_fraud"].to_numpy()
    final_rows, test_probs = [], {}
    for fs in ["week10", "week11_extended"]:
        Xt, fill_fs = fraud_design(trv, feature_set=fs)
        Xs, _ = fraud_design(test, fill_fs, feature_set=fs)
        fit = fit_logit(Xt, y_trv)
        p = predict_logit(fit, Xs)
        test_probs[fs] = p
        if fs == selected:
            final_fit, final_fill, X_test_sel = fit, fill_fs, Xs
        cap, _ = daily_capture(test, p * test["transaction_amt"].to_numpy(), [SELECT_CAPACITY])
        final_rows.append({"model": CANDIDATE_LABELS[fs] + (" — SELECTED" if fs == selected else ""),
                           **classification_metrics(y_test, p),
                           "captured_at_50": cap[SELECT_CAPACITY]["fraud_value_captured"]})
    p_sel = test_probs[selected]
    amt_t = test["transaction_amt"].to_numpy()
    for name, s in [("Baseline: largest amount", amt_t),
                    ("Baseline: Week 9 rule score", test["risk_score"].to_numpy() + amt_t / 1e6),
                    ("Baseline: random", np.random.default_rng(SEED).random(len(test)))]:
        cap, _ = daily_capture(test, s, [SELECT_CAPACITY])
        final_rows.append({"model": name, "pr_auc": float(average_precision_score(y_test, s)),
                           "roc_auc": float(roc_auc_score(y_test, s)), "brier": None,
                           "captured_at_50": cap[SELECT_CAPACITY]["fraud_value_captured"]})
    final_table = pd.DataFrame(final_rows)
    print(final_table.round(4).to_string(index=False))
    print(f"  (test fraud rate {y_test.mean():.4f} = PR-AUC of a random ranking)")

    capture_rows, per_day_sel = [], None
    for name, s in fraud_scores(test, p_sel).items():
        res, per_day = daily_capture(test, s, CAPACITIES)
        if name.startswith("P4"):
            per_day_sel = per_day[SELECT_CAPACITY]
        for k, v in res.items():
            capture_rows.append({"policy": name, "capacity": k, "fraud_value_captured": v["fraud_value_captured"],
                                 "precision": v["precision"]})
    cap_df = pd.DataFrame(capture_rows)
    print("\n  KPI 1 — fraud value captured, final test days:")
    print(cap_df.pivot(index="policy", columns="capacity", values="fraud_value_captured").round(3).to_string())

    section("FRAUD MODEL — where the model performs poorly (final test)")
    e = test.assign(p=p_sel)
    thr = np.quantile(p_sel, 0.95)
    e["flagged"] = e["p"] >= thr
    e["amount_band"] = pd.cut(e["transaction_amt"], [0, 50, 200, 1000, np.inf],
                              labels=["under $50", "$50-200", "$200-1,000", "over $1,000"], right=False)
    e["history"] = pd.cut(e["prior_txn_count"], [-1, 0, 4, 19, np.inf],
                          labels=["new customer", "1-4 prior", "5-19 prior", "20+ prior"])
    e["card_type"] = e["card6"].fillna("missing").astype(str).str.lower()
    e["product"] = e["product_cd"].fillna("missing").astype(str)
    seg_rows = []
    for seg in ["product", "card_type", "amount_band", "history"]:
        for level, g in e.groupby(seg, observed=True):
            if len(g) < 200:
                continue
            fr = g[g.is_fraud == 1]
            seg_rows.append({
                "segment": seg, "level": str(level), "transactions": int(len(g)),
                "fraud_rate": float(g.is_fraud.mean()), "avg_predicted": float(g.p.mean()),
                "pr_auc": float(average_precision_score(g.is_fraud, g.p)) if 0 < g.is_fraud.sum() < len(g) else None,
                "fraud_caught_in_top5pct": float(fr.flagged.mean()) if len(fr) else None,
                "fraud_dollars_caught_in_top5pct": float((fr.transaction_amt * fr.flagged).sum() / fr.transaction_amt.sum())
                if len(fr) else None,
            })
    seg_df = pd.DataFrame(seg_rows)
    print(seg_df.round(3).to_string(index=False))
    overall_recall = float(e[e.is_fraud == 1].flagged.mean())
    weak = seg_df.dropna(subset=["fraud_caught_in_top5pct"])
    weak = weak[(weak["fraud_caught_in_top5pct"] < overall_recall * 0.6) & (weak["fraud_rate"] > 0)]
    calib_gap = seg_df.assign(gap=(seg_df.avg_predicted - seg_df.fraud_rate).abs()).sort_values("gap", ascending=False)
    worst_days = per_day_sel.sort_values().head(5)
    print(f"\n  Overall: {overall_recall:.1%} of fraud cases fall in the top 5% of probabilities.")
    print("  Weakest segments (fraud caught < 60% of overall):",
          ", ".join(f"{r.segment}={r.level}" for r in weak.itertuples()) or "none")
    print("  Largest calibration gaps:", ", ".join(f"{r.segment}={r.level} (predicted {r.avg_predicted:.1%}, "
                                                 f"actual {r.fraud_rate:.1%})" for r in calib_gap.head(3).itertuples()))
    print("  Worst test days for KPI 1 at 50 reviews:",
          ", ".join(f"day {int(d)} ({v:.0%})" for d, v in worst_days.items()))
    out["error_analysis"] = {
        "top5pct_threshold": float(thr), "overall_fraud_caught_in_top5pct": overall_recall, "segments": seg_rows,
        "weak_segments": [f"{r.segment}={r.level}" for r in weak.itertuples()],
        "largest_calibration_gaps": calib_gap.head(3)[["segment", "level", "avg_predicted", "fraud_rate"]]
        .to_dict(orient="records"),
        "worst_days_capture_at_50": {str(int(d)): float(v) for d, v in worst_days.items()},
        "days_with_zero_capture_at_50": int((per_day_sel == 0).sum()), "test_days": int(len(per_day_sel)),
    }

    rng = np.random.default_rng(SEED)
    Xt, _ = fraud_design(trv, final_fill, feature_set=selected)
    Zt = (Xt - final_fit["mu"]) / final_fit["sd"]
    boot_coef, boot_int = [], []
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, len(Zt), min(BOOT_SAMPLE, len(Zt)))
        if y_trv[idx].min() == y_trv[idx].max():
            continue
        m = LogisticRegression(C=1.0, max_iter=3000).fit(Zt[idx], y_trv[idx])
        boot_coef.append(m.coef_[0])
        boot_int.append(m.intercept_[0])
    feats = FEATURE_SETS[selected]
    Zs = (X_test_sel - final_fit["mu"]) / final_fit["sd"]
    base, contrib = linear_contributions(Zs, final_fit["coef"], final_fit["intercept"], final_fit["z_mean"])
    importance = sorted([{"feature": f, "label": FRAUD_FEATURE_LABELS[f], "mean_abs_contribution": float(v),
                          "coef_per_sd": float(c), "odds_ratio_per_sd": float(np.exp(c))}
                         for f, v, c in zip(feats, np.abs(contrib).mean(axis=0), final_fit["coef"])],
                        key=lambda r: -r["mean_abs_contribution"])
    bins = pd.qcut(p_sel, 10, labels=False, duplicates="drop")
    calib = (pd.DataFrame({"bin": bins, "p": p_sel, "y": y_test}).groupby("bin")
             .agg(mean_predicted=("p", "mean"), observed_rate=("y", "mean"), n=("y", "size"))
             .reset_index().to_dict(orient="records"))
    metrics = {
        "model": "Logistic regression (fraud probability)", "week": 11,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": SEED,
        "feature_set": selected,
        "split": {"train_rows": int(len(trv)), "test_rows": int(len(test)), "validation_rows": int(len(val)),
                  "train_fraud_rate": float(y_trv.mean()), "test_fraud_rate": float(y_test.mean()),
                  "design": "60% development / 15% validation / 25% test"},
        "comparison": {"Logistic regression (selected)": classification_metrics(y_test, p_sel),
                       **{r["model"]: {k: r[k] for k in ("pr_auc", "roc_auc", "brier") if r.get(k) is not None}
                          for r in final_rows if "SELECTED" not in r["model"]}},
        "calibration": calib, "capture_at_capacity": capture_rows, "global_importance": importance,
        "base_log_odds": base, "bootstrap_refits": len(boot_coef), "error_analysis": out["error_analysis"],
    }
    joblib.dump({"features": feats, "feature_set": selected, "labels": FRAUD_FEATURE_LABELS, "fill": final_fill,
                 "scaler_mean": final_fit["mu"], "scaler_sd": final_fit["sd"], "coef": final_fit["coef"],
                 "intercept": final_fit["intercept"], "train_mean": final_fit["z_mean"],
                 "boot_coef": np.array(boot_coef), "boot_intercept": np.array(boot_int),
                 "ranges": raw_ranges(trv), "metrics": metrics},
                os.path.join(MODEL_DIR, "fraud_model.joblib"))
    with open(os.path.join(MODEL_DIR, "fraud_model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    final_table.to_csv(os.path.join(OUT_DIR, "fraud_final_test.csv"), index=False)
    cap_df.to_csv(os.path.join(OUT_DIR, "fraud_kpi1_capture.csv"), index=False)
    seg_df.to_csv(os.path.join(OUT_DIR, "fraud_error_segments.csv"), index=False)
    out["final_test"] = final_rows
    out["kpi1_capture"] = capture_rows
    return out


# ----------------------------------------------------------------------------
# Alert volume model (KPI 2)
# ----------------------------------------------------------------------------
def evaluate_volume(daily):
    out = {}
    days = np.arange(int(daily.sim_day.min()), int(daily.sim_day.max()) + 1)
    s = daily.set_index("sim_day")["alerts"].reindex(days, fill_value=0).astype(float)
    fr = pd.DataFrame({"day": days, "alerts": s.to_numpy(), "lag1": s.shift(1).to_numpy(),
                       "lag2": s.shift(2).to_numpy(), "lag7": s.shift(7).to_numpy(),
                       "lag7_mean": s.shift(1).rolling(7).mean().to_numpy()}).dropna().reset_index(drop=True)
    n = len(fr)
    dev, val, test = fr.iloc[:int(n * DEV_END)], fr.iloc[int(n * DEV_END):int(n * VAL_END)], fr.iloc[int(n * VAL_END):]
    out["split"] = {k: [int(x.day.min()), int(x.day.max())] for k, x in
                    [("development_days", dev), ("validation_days", val), ("test_days", test)]}

    def design(x, fs):
        return volume_design(x.lag1, x.lag7_mean, x.day, x.lag2, x.lag7, feature_set=fs)

    def fit(x, fs):
        X = design(x, fs)
        m = PoissonRegressor(alpha=1e-6, max_iter=2000).fit(X, x.alerts)
        mu = m.predict(X)
        phi = float(max(np.sum((x.alerts - mu) ** 2 / mu) / max(len(x) - X.shape[1] - 1, 1), 1.0))
        return m, phi, X.mean(axis=0)

    def interval(mu, phi):
        d = [count_dist(v, phi) for v in mu]
        q = (1 - INTERVAL) / 2
        return np.array([x.ppf(q) for x in d]), np.array([x.ppf(1 - q) for x in d]), d

    out["leakage_checks"] = [
        {"check": "Time order: development < validation < final test days",
         "result": bool(dev.day.max() < val.day.min() <= val.day.max() < test.day.min()), "detail": str(out["split"])},
        {"check": "Predictors are known the evening before (lagged counts only)", "result": True,
         "detail": "yesterday, two days ago, same weekday last week, previous 7-day average, weekday, trend"}]
    out["leakage_caveats"] = ["Alert counts come from rules whose thresholds were set on the full period; "
                              "this is a slight look-ahead in the target series itself."]

    section("VOLUME MODEL — development (trained on development days, scored on validation days)")
    print(f"  Days: development {out['split']['development_days']}, validation {out['split']['validation_days']}")
    rows = []
    for fs in ["week10", "week11_lags"]:
        m, phi, _ = fit(dev, fs)
        mu = m.predict(design(val, fs))
        lo, hi, _ = interval(mu, phi)
        rows.append({"model": VOLUME_LABELS[fs], "feature_set": fs, "mae": float(np.mean(np.abs(val.alerts - mu))),
                     "mape": float(np.mean(np.abs(val.alerts - mu) / np.maximum(val.alerts, 1))),
                     "coverage_90": float(np.mean((val.alerts >= lo) & (val.alerts <= hi)))})
    for name, pred in [("Baseline: same as yesterday", val.lag1), ("Baseline: previous 7-day average", val.lag7_mean),
                       ("Baseline: same weekday last week", val.lag7)]:
        rows.append({"model": name, "feature_set": "-", "mae": float(np.mean(np.abs(val.alerts - pred))),
                     "mape": float(np.mean(np.abs(val.alerts - pred) / np.maximum(val.alerts, 1))), "coverage_90": None})
    dev_table = pd.DataFrame(rows)
    print(dev_table.drop(columns=["feature_set"]).round(3).to_string(index=False))
    improvement = 1 - rows[1]["mae"] / rows[0]["mae"]
    selected = "week11_lags" if improvement >= 0.02 else "week10"
    change = (f"a {improvement:.1%} reduction" if improvement >= 0 else f"{-improvement:.1%} higher")
    decision = (f"Validation MAE: Week 10 {rows[0]['mae']:.1f}, candidate {rows[1]['mae']:.1f} ({change}). "
                f"Rule: keep the candidate only if MAE falls by at least 2%. Selected: {VOLUME_LABELS[selected]}.")
    print("\n  DECISION:", decision)
    out["development"] = rows
    out["selection"] = {"rule": "Keep candidate if validation MAE falls by >= 2%; otherwise keep Week 10.",
                        "decision": decision, "selected_feature_set": selected,
                        "candidate_retained": selected != "week10"}
    dev_table.to_csv(os.path.join(OUT_DIR, "volume_validation_comparison.csv"), index=False)
    if VALIDATION_ONLY:
        return out

    section("VOLUME MODEL — final test (refit on development + validation days, evaluated once)")
    trv = pd.concat([dev, val])
    final_rows = []
    for fs in ["week10", "week11_lags"]:
        m, phi, mean_ = fit(trv, fs)
        mu = m.predict(design(test, fs))
        lo, hi, dists = interval(mu, phi)
        final_rows.append({"model": VOLUME_LABELS[fs] + (" — SELECTED" if fs == selected else ""),
                           "mae": float(np.mean(np.abs(test.alerts - mu))),
                           "mape": float(np.mean(np.abs(test.alerts - mu) / np.maximum(test.alerts, 1))),
                           "coverage_90": float(np.mean((test.alerts >= lo) & (test.alerts <= hi)))})
        if fs == selected:
            sel = {"model": m, "phi": phi, "mean": mean_, "mu": mu, "lo": lo, "hi": hi, "dists": dists}
    for name, pred in [("Baseline: same as yesterday", test.lag1), ("Baseline: previous 7-day average", test.lag7_mean),
                       ("Baseline: same weekday last week", test.lag7)]:
        final_rows.append({"model": name, "mae": float(np.mean(np.abs(test.alerts - pred))),
                           "mape": float(np.mean(np.abs(test.alerts - pred) / np.maximum(test.alerts, 1))),
                           "coverage_90": None})
    final_table = pd.DataFrame(final_rows)
    print(final_table.round(3).to_string(index=False))

    overflow = []
    for c in VOLUME_CAPACITIES:
        p_over = np.array([1 - d.cdf(c) for d in sel["dists"]])
        actual, pred = test.alerts.to_numpy() > c, p_over > 0.5
        overflow.append({"capacity": c, "actual_overflow_days": int(actual.sum()),
                         "predicted_overflow_days_p_over_50pct": int(pred.sum()),
                         "overflow_day_accuracy": float(np.mean(pred == actual)),
                         "missed_overflow_days": int((actual & ~pred).sum()),
                         "false_alarm_days": int((~actual & pred).sum()),
                         "avg_actual_overflow_alerts": float(np.mean(np.maximum(test.alerts - c, 0))),
                         "avg_predicted_overflow_alerts": float(np.mean(
                             [np.sum((np.arange(c + 1, int(d.ppf(0.9999)) + 2) - c)
                                     * d.pmf(np.arange(c + 1, int(d.ppf(0.9999)) + 2))) for d in sel["dists"]]))})
    print("\n  KPI 2 — overflow on final test days:")
    print(pd.DataFrame(overflow).round(3).to_string(index=False))

    section("VOLUME MODEL — where the forecast performs poorly (final test)")
    err = test.assign(pred=sel["mu"], lo=sel["lo"], hi=sel["hi"])
    err["abs_err"] = (err.alerts - err.pred).abs()
    err["inside"] = (err.alerts >= err.lo) & (err.alerts <= err.hi)
    err["weekday"] = err.day.astype(int) % 7
    err["level"] = pd.qcut(err.alerts, 3, labels=["quiet days", "typical days", "busy days"], duplicates="drop")
    seg_rows = []
    for seg in ["level", "weekday"]:
        for lvl, g in err.groupby(seg, observed=True):
            seg_rows.append({"segment": seg, "level": str(lvl), "days": int(len(g)),
                             "avg_alerts": float(g.alerts.mean()), "mae": float(g.abs_err.mean()),
                             "bias_actual_minus_forecast": float((g.alerts - g.pred).mean()),
                             "coverage_90": float(g.inside.mean())})
    seg_df = pd.DataFrame(seg_rows)
    print(seg_df.round(2).to_string(index=False))
    worst = err.sort_values("abs_err", ascending=False).head(5)
    print("  Largest misses:", ", ".join(f"day {int(r.day)}: actual {r.alerts:.0f} vs forecast {r.pred:.0f}"
                                       for r in worst.itertuples()))
    out["error_analysis"] = {"segments": seg_rows,
                             "largest_misses": [{"day": int(r.day), "actual": float(r.alerts), "forecast": float(r.pred)}
                                                for r in worst.itertuples()]}

    feats = VOLUME_SETS[selected]
    _, contrib = linear_contributions(design(test, selected), sel["model"].coef_, float(sel["model"].intercept_),
                                      sel["mean"])
    importance = sorted([{"feature": f, "label": VOLUME_FEATURE_LABELS[f], "mean_abs_contribution": float(v),
                          "coef": float(c), "multiplier": float(np.exp(c))}
                         for f, v, c in zip(feats, np.abs(contrib).mean(axis=0), sel["model"].coef_)],
                        key=lambda r: -r["mean_abs_contribution"])
    sel_row = next(r for r in final_rows if "SELECTED" in r["model"])
    metrics = {
        "model": "Poisson regression (daily alert volume)", "week": 11, "feature_set": selected,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "split": {"train_days": [int(trv.day.min()), int(trv.day.max())],
                  "test_days": [int(test.day.min()), int(test.day.max())],
                  "validation_days": out["split"]["validation_days"],
                  "design": "60% development / 15% validation / 25% test (days)"},
        "dispersion_phi": sel["phi"], "interval": INTERVAL, "interval_coverage_test": sel_row["coverage_90"],
        "comparison": {"Poisson regression (selected)": {"mae": sel_row["mae"], "mape": sel_row["mape"]},
                       **{r["model"]: {"mae": r["mae"], "mape": r["mape"]} for r in final_rows
                          if "SELECTED" not in r["model"]}},
        "overflow_kpi": overflow, "global_importance": importance,
        "test_predictions": pd.DataFrame({"day": test.day.astype(int), "actual": test.alerts, "predicted": sel["mu"],
                                          "lower": sel["lo"], "upper": sel["hi"]}).to_dict(orient="records"),
        "error_analysis": out["error_analysis"],
    }
    ranges = {c: {"p01": float(fr[c].quantile(0.01)), "p99": float(fr[c].quantile(0.99)),
                  "min": float(fr[c].min()), "max": float(fr[c].max())} for c in ["lag1", "lag7_mean", "lag2", "lag7"]}
    joblib.dump({"features": feats, "feature_set": selected, "labels": VOLUME_FEATURE_LABELS,
                 "coef": sel["model"].coef_, "intercept": float(sel["model"].intercept_), "train_mean": sel["mean"],
                 "phi": sel["phi"], "interval": INTERVAL, "history": s.to_dict(), "ranges": ranges,
                 "metrics": metrics}, os.path.join(MODEL_DIR, "alert_volume_model.joblib"))
    with open(os.path.join(MODEL_DIR, "alert_volume_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    final_table.to_csv(os.path.join(OUT_DIR, "volume_final_test.csv"), index=False)
    pd.DataFrame(overflow).to_csv(os.path.join(OUT_DIR, "volume_kpi2_overflow.csv"), index=False)
    seg_df.to_csv(os.path.join(OUT_DIR, "volume_error_segments.csv"), index=False)
    out["final_test"] = final_rows
    out["kpi2_overflow"] = overflow
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with get_engine().connect() as conn:
        fraud_df = pd.read_sql(FRAUD_QUERY, conn)
        daily = pd.read_sql("SELECT sim_day, COUNT(*) AS alerts FROM alert_queue GROUP BY sim_day", conn)
    print(f"Loaded {len(fraud_df):,} transactions and {len(daily)} alert days."
          + ("  [VALIDATION ONLY: the final test is not used]" if VALIDATION_ONLY else ""))
    results = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "design": {"split": "60% development / 15% validation / 25% final test, by time",
                          "note": "All Week 11 choices were made on validation data; the final test was run once."},
               "fraud": evaluate_fraud(fraud_df), "volume": evaluate_volume(daily)}
    name = "validation_results.json" if VALIDATION_ONLY else "evaluation_results.json"
    with open(os.path.join(OUT_DIR, name), "w") as f:
        json.dump(results, f, indent=2, default=str)
    section("DONE")
    print("  Fraud model selected:", results["fraud"]["selection"]["selected_feature_set"])
    print("  Volume model selected:", results["volume"]["selection"]["selected_feature_set"])
    print(f"  Saved reports/week11/{name}" + ("" if VALIDATION_ONLY else " and the final models in models/"))


if __name__ == "__main__":
    main()
