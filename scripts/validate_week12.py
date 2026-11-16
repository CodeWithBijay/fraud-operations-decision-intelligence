"""Week 12 validation checks: reproduces the data, report and model reconciliation evidence in the matrix.

Run from the project folder:  python3 scripts/validate_week12.py
Reads the database settings from .streamlit/secrets.toml (PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGSSLMODE) or the
same environment variables. Read-only: every statement is a SELECT. Writes evidence/validation_results.json and
prints a summary. Model checks use models/*_metrics.json produced by src/modeling/evaluate_week11.py."""
import json
import os
import tomllib
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = {}
sec = os.path.join(ROOT, ".streamlit", "secrets.toml")
if os.path.exists(sec):
    cfg = tomllib.load(open(sec, "rb"))
get = lambda k, d=None: str(cfg.get(k) or os.environ.get(k) or d or "")
engine = create_engine(URL.create("postgresql+psycopg2", username=get("PGUSER", "fraud_app"), password=get("PGPASSWORD") or None,
                                  host=get("PGHOST", "localhost"), port=int(get("PGPORT", "5432")),
                                  database=get("PGDATABASE", "fraud_risk_db")),
                       connect_args={"sslmode": get("PGSSLMODE", "prefer")})

RULES = """(device_id IS NOT NULL AND NOT cold_start_flag AND row_number() OVER (PARTITION BY customer_id, device_id
            ORDER BY transaction_dt, transaction_id) = 1) AS e6,
           coalesce(txn_count_24h >= 8, false) AS e1, coalesce(customer_amount_zscore >= 3, false) AS e2,
           coalesce(hours_since_previous_txn <= 0.0438888888888889, false) AS e3, cold_start_flag AS e4,
           (transaction_amt >= 445) AS e5"""
CHECKS = {
    # E01 structural and logical validity of the generated data (TEST-01, TEST-02)
    "integrity": """SELECT count(*) AS rows, count(DISTINCT transaction_id) AS unique_ids,
        count(*) FILTER (WHERE customer_id IS NULL OR account_id IS NULL OR transaction_dt IS NULL
                         OR transaction_amt IS NULL) AS null_required,
        count(*) FILTER (WHERE device_id IS NULL) AS null_device,
        count(*) FILTER (WHERE transaction_amt <= 0) AS nonpositive_amount,
        count(*) FILTER (WHERE prior_txn_count < 0 OR txn_count_24h < 0 OR hours_since_previous_txn < 0
                         OR customer_std_amt_30d < 0) AS negative_values,
        count(*) FILTER (WHERE cold_start_flag <> (prior_txn_count = 0)) AS cold_flag_mismatch,
        count(*) FILTER (WHERE cold_start_flag AND (hours_since_previous_txn IS NOT NULL
                         OR customer_avg_amt_30d IS NOT NULL)) AS new_customer_with_history,
        count(*) FILTER (WHERE NOT cold_start_flag AND hours_since_previous_txn IS NULL) AS existing_missing_gap,
        count(*) FILTER (WHERE txn_count_24h > prior_txn_count) AS count24_above_prior,
        (SELECT count(*) FROM (SELECT customer_id FROM transaction_features WHERE cold_start_flag
                               GROUP BY customer_id HAVING count(*) > 1) x) AS customers_with_two_first_txns,
        min(transaction_amt) AS min_amt, max(transaction_amt) AS max_amt
        FROM transaction_features""",
    "orphans": """SELECT (SELECT count(*) FROM alert_queue a LEFT JOIN transaction_features f USING (transaction_id)
                          WHERE f.transaction_id IS NULL) AS alerts_without_features,
                         (SELECT count(*) - count(DISTINCT transaction_id) FROM alert_queue) AS duplicate_alerts,
                         (SELECT count(*) FROM alert_queue a LEFT JOIN transaction t USING (transaction_id)
                          WHERE t.transaction_id IS NULL) AS alerts_without_model_inputs""",
    # E01 alert rules recomputed independently from the features (TEST-03)
    "rules": f"""WITH f AS (SELECT transaction_id, {RULES} FROM transaction_features),
        k AS (SELECT f.*, e1::int + e2::int + e3::int + e4::int + e5::int + e6::int AS n_rules FROM f),
        j AS (SELECT k.*, a.transaction_id IS NOT NULL AS in_queue, a.r1_velocity, a.r2_amount_spike,
                     a.r3_rapid_repeat, a.r4_new_customer, a.r5_large_amount, a.r6_new_device, a.risk_score
              FROM k LEFT JOIN alert_queue a USING (transaction_id))
        SELECT count(*) FILTER (WHERE in_queue) AS alerts,
               count(*) FILTER (WHERE n_rules >= 2) AS meet_two_or_more_rules,
               count(*) FILTER (WHERE in_queue AND n_rules < 2) AS alert_with_fewer_than_two_rules,
               count(*) FILTER (WHERE NOT in_queue AND n_rules >= 2) AS two_rules_but_not_alerted,
               count(*) FILTER (WHERE in_queue AND (r1_velocity <> e1 OR r2_amount_spike <> e2 OR r3_rapid_repeat <> e3
                     OR r4_new_customer <> e4 OR r5_large_amount <> e5 OR r6_new_device <> e6)) AS flag_mismatches,
               count(*) FILTER (WHERE in_queue AND risk_score <> n_rules) AS score_mismatches,
               count(*) FILTER (WHERE n_rules = 1) AS exactly_one_rule FROM j""",
    # E01 plausibility and coverage (TEST-04, TEST-05)
    "plausibility": """SELECT round(avg(transaction_amt)::numeric, 4) AS mean_amt,
        round(percentile_cont(0.5) WITHIN GROUP (ORDER BY transaction_amt)::numeric, 3) AS median_amt,
        (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY c) FROM (SELECT count(*) c FROM transaction_features
                                                                    GROUP BY customer_id) y) AS median_txn_per_customer,
        (SELECT max(c) FROM (SELECT count(*) c FROM transaction_features GROUP BY customer_id) y) AS max_txn_per_customer,
        (SELECT count(*) FROM (SELECT customer_id FROM transaction_features GROUP BY customer_id
                               HAVING count(*) > 1000) y) AS customers_over_1000_txns
        FROM transaction_features""",
    "coverage": """SELECT (SELECT json_object_agg(product_cd, n) FROM (SELECT product_cd, count(*) n FROM transaction JOIN alert_queue USING (transaction_id)
                                                                   GROUP BY 1) x) AS alerts_by_product,
        (SELECT json_object_agg(coalesce(card6, 'missing'), n) FROM (SELECT card6, count(*) n FROM transaction JOIN alert_queue USING (transaction_id)
                                                                     GROUP BY 1) x) AS alerts_by_card_type,
        (SELECT count(*) FROM alert_queue WHERE transaction_amt >= 5000) AS alerts_5000_plus""",
    # E02 daily alert volume (KPI 2 input) and a report recalculation (TEST-07, TEST-08)
    "daily": "SELECT sim_day, count(*) AS alerts, sum(transaction_amt) AS amount FROM alert_queue GROUP BY 1 ORDER BY 1",
    "report_day171": """SELECT count(*) AS alerts, round(sum(transaction_amt)::numeric, 2) AS total_amount,
        (SELECT round(sum(transaction_amt)::numeric, 2) FROM (SELECT transaction_amt FROM alert_queue WHERE sim_day = 171
                                                              ORDER BY transaction_amt DESC LIMIT 50) x) AS p1_top50_amount
        FROM alert_queue WHERE sim_day = 171""",
    # E01 sensitivity of alert volume to the generation thresholds (TEST-06)
    "sensitivity": f"""WITH f AS (SELECT {RULES}, txn_count_24h, transaction_amt, customer_amount_zscore
                                  FROM transaction_features),
        b AS (SELECT e3::int + e4::int + e6::int AS base, txn_count_24h, transaction_amt, customer_amount_zscore FROM f)
        SELECT count(*) FILTER (WHERE base + (txn_count_24h >= 8)::int + coalesce(customer_amount_zscore >= 3, false)::int
                                + (transaction_amt >= 445)::int >= 2) AS baseline,
        count(*) FILTER (WHERE base + (txn_count_24h >= 7)::int + coalesce(customer_amount_zscore >= 3, false)::int
                         + (transaction_amt >= 445)::int >= 2) AS r1_threshold_7,
        count(*) FILTER (WHERE base + (txn_count_24h >= 9)::int + coalesce(customer_amount_zscore >= 3, false)::int
                         + (transaction_amt >= 445)::int >= 2) AS r1_threshold_9,
        count(*) FILTER (WHERE base + (txn_count_24h >= 8)::int + coalesce(customer_amount_zscore >= 2.5, false)::int
                         + (transaction_amt >= 445)::int >= 2) AS r2_threshold_2_5,
        count(*) FILTER (WHERE base + (txn_count_24h >= 8)::int + coalesce(customer_amount_zscore >= 3, false)::int
                         + (transaction_amt >= 400)::int >= 2) AS r5_threshold_400,
        count(*) FILTER (WHERE base + (txn_count_24h >= 8)::int + coalesce(customer_amount_zscore >= 3, false)::int
                         + (transaction_amt >= 500)::int >= 2) AS r5_threshold_500 FROM b""",
}

out = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
with engine.connect() as con:
    con.execute(text("SET TRANSACTION READ ONLY"))
    for name, sql in CHECKS.items():
        rows = [dict(r._mapping) for r in con.execute(text(sql))]
        out[name] = rows if name == "daily" else rows[0]

# E02 reconcile the volume model's test results with the database and recompute its metrics
vol = json.load(open(os.path.join(ROOT, "models", "alert_volume_metrics.json")))
fraud = json.load(open(os.path.join(ROOT, "models", "fraud_model_metrics.json")))
daily = {r["sim_day"]: r["alerts"] for r in out["daily"]}
tp = vol["test_predictions"]
out["volume_reconciliation"] = {
    "test_days": len(tp), "days_where_saved_actual_differs_from_database": sum(int(r["actual"]) != daily[r["day"]] for r in tp),
    "mae_recomputed": sum(abs(r["actual"] - r["predicted"]) for r in tp) / len(tp),
    "mae_reported": vol["comparison"]["Poisson regression (selected)"]["mae"],
    "same_as_yesterday_mae_recomputed": sum(abs(r["actual"] - daily[r["day"] - 1]) for r in tp) / len(tp),
    "interval_coverage_recomputed": sum(r["lower"] <= r["actual"] <= r["upper"] for r in tp) / len(tp),
    "overflow_days_all_182": {c: sum(v > c for v in daily.values()) for c in (50, 100, 150)},
}
cal = fraud["calibration"]
out["fraud_model_summary"] = {
    "pr_auc": fraud["comparison"]["Logistic regression (selected)"]["pr_auc"],
    "expected_calibration_error": sum(b["n"] * abs(b["mean_predicted"] - b["observed_rate"]) for b in cal)
                                  / sum(b["n"] for b in cal),
    "capture_at_50": {r["policy"][:2]: r["fraud_value_captured"] for r in fraud["capture_at_capacity"]
                      if r["capacity"] == 50},
}
os.makedirs(os.path.join(ROOT, "evidence"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "evidence", "validation_results.json"), "w"), indent=2, default=str)
for k, v in out.items():
    if k != "daily":
        print(f"{k}: {json.dumps(v, default=str)[:400]}")
print("Saved evidence/validation_results.json")
