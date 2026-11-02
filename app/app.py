"""Fraud Operations Decision Intelligence — Week 11 application.

Decision-maker: Fraud Operations Lead.
Decisions supported: which of today's fraud alerts the team reviews first (limited capacity),
and how much review capacity to plan for tomorrow.

Pages
    Alert queue            ranked alerts, filters, policy comparison, volume, trends, team performance
    Alert investigation    rules fired, customer history, model explanation, what-if + summary, decisions
    Fraud risk model       KPI 1, model performance, overall predictor importance
    Alert volume forecast  KPI 2, forecast with range, overall importance, what-if + summary

Data (PostgreSQL, database fraud_risk_db)
    transaction, transaction_features, alert_queue, alert_rule_config, ops_decision_log
Models (folder models/, built by src/modeling/evaluate_week11.py)
    fraud_model.joblib, alert_volume_model.joblib

Run:  streamlit run app/app.py
"""
import html
import json
import os
import sys

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st
from scipy.stats import nbinom, poisson
from sqlalchemy import create_engine, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "modeling"))
from common import (MODEL_DIR, SOURCE_COLUMNS_ALL, fraud_design, linear_contributions,  # noqa: E402
                    sigmoid, volume_design, volume_lags)

st.set_page_config(page_title="FraudOps · Decision Intelligence", page_icon=":material/shield:",
                   layout="wide", initial_sidebar_state="expanded")

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select { font-family: 'Inter', sans-serif; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 2.5rem 2rem 2.5rem !important; max-width: 1480px; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
h1, h2, h3, h4 { letter-spacing: -0.01em; color: #0F172A; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: 0.4rem; }

/* Top navigation bar */
.st-key-topnav { position: sticky; top: 0; z-index: 999; background: rgba(255, 255, 255, .96);
                 backdrop-filter: blur(8px); border-bottom: 1px solid #E2E8F0; box-sizing: border-box;
                 width: 100vw !important; max-width: 100vw !important; min-width: 100vw;
                 margin-left: calc(50% - 50vw); margin-top: -1rem; padding: 10px 2.5rem; }
.st-key-topnav [data-testid="stHorizontalBlock"] { align-items: center; }
.brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center;
              justify-content: center; background: linear-gradient(135deg, #2563EB, #0EA5E9); flex-shrink: 0; }
.brand-name { font-weight: 700; font-size: 1.05rem; color: #0F172A; line-height: 1.1; }
.brand-sub { font-size: 0.66rem; color: #64748B; letter-spacing: 0.06em; text-transform: uppercase; }
.st-key-topnav div[role="radiogroup"] { gap: 4px; flex-wrap: nowrap; justify-content: center; }
.st-key-topnav label[data-testid="stRadioOption"] { padding: 8px 14px; border-radius: 8px; margin: 0;
                                                    transition: background .15s; white-space: nowrap; }
.st-key-topnav label[data-testid="stRadioOption"]:hover { background: #F1F5F9; }
.st-key-topnav label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none; }
.st-key-topnav label[data-testid="stRadioOption"] p { font-size: 0.9rem; font-weight: 500; color: #475569; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] { background: #EFF6FF; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] p { color: #1D4ED8; font-weight: 600; }
.user-pill { display: flex; align-items: center; gap: 10px; justify-content: flex-end; }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: #1E3A8A; display: flex; align-items: center;
          justify-content: center; font-weight: 600; color: #DBEAFE; font-size: 0.78rem; flex-shrink: 0; }
.user-name { font-size: 0.84rem; font-weight: 600; color: #0F172A; line-height: 1.2; }
.user-sub { font-size: 0.7rem; color: #64748B; }

/* Hero banner */
.hero { margin: 22px 0 18px 0; padding: 28px 32px; border-radius: 16px; color: #FFFFFF;
        background: radial-gradient(circle at 85% 20%, rgba(14, 165, 233, .35), transparent 45%),
                    linear-gradient(120deg, #0B1424 0%, #13254A 55%, #1E3A8A 100%);
        display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; }
.hero .eyebrow { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #7DD3FC; }
.hero h1 { color: #FFFFFF !important; font-size: 2rem; font-weight: 700; margin: 4px 0 6px 0; padding: 0; }
.hero p { color: #CBD5E1; margin: 0; font-size: 0.97rem; max-width: 680px; }
.hero .chip, .hero .chip.neutral { background: rgba(255, 255, 255, .1); color: #E2E8F0;
                                   border-color: rgba(255, 255, 255, .2); }
.hero .chip.warn { background: rgba(248, 113, 113, .18); color: #FECACA; border-color: rgba(248, 113, 113, .4); }
.hero .chip.ok { background: rgba(52, 211, 153, .16); color: #A7F3D0; border-color: rgba(52, 211, 153, .4); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { font-size: 0.78rem; font-weight: 500; padding: 5px 11px; border-radius: 999px; background: #EFF6FF;
        color: #1D4ED8; border: 1px solid #DBEAFE; white-space: nowrap; }
.chip.warn { background: #FEF2F2; color: #B91C1C; border-color: #FECACA; }
.chip.ok { background: #ECFDF5; color: #047857; border-color: #A7F3D0; }
.chip.neutral { background: #F1F5F9; color: #334155; border-color: #E2E8F0; }

/* Settings toolbar */
.st-key-toolbar { background: #FFFFFF; border: 1px solid #E5E9F2; border-radius: 14px; padding: 14px 18px 4px 18px;
                  box-shadow: 0 1px 2px rgba(16, 24, 40, .04); margin-bottom: 18px; }
.toolbar-title { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
                 color: #64748B; margin-bottom: 2px; }

/* Footer */
.site-footer { margin-top: 48px; padding: 22px 0 6px 0; border-top: 1px solid #E2E8F0; display: flex;
               justify-content: space-between; gap: 16px; flex-wrap: wrap; font-size: 0.8rem; color: #64748B; }
.site-footer b { color: #0F172A; }

/* Cards */
[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E5E9F2; border-radius: 12px;
                           padding: 14px 16px; box-shadow: 0 1px 2px rgba(16, 24, 40, .05); }
[data-testid="stMetricLabel"] p { font-size: 0.78rem !important; color: #64748B !important; font-weight: 500; }
[data-testid="stMetricValue"] { font-size: 1.55rem !important; font-weight: 700; color: #0F172A; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 10px; overflow: hidden; }
[data-testid="stExpander"] details { border-radius: 10px; border-color: #E5E9F2; background: #FFFFFF; }

/* Tabs as a segmented control */
.stTabs [role="tablist"] { gap: 4px; background: #E9EEF5; padding: 4px; border-radius: 10px; border: none;
                           width: fit-content; max-width: 100%; overflow-x: auto; margin-bottom: 6px; }
.stTabs [data-testid="stTab"] { height: 36px; padding: 0 16px; border-radius: 8px; background: transparent;
                                display: flex; align-items: center; }
.stTabs [data-testid="stTab"] p { font-size: 0.88rem; font-weight: 500; color: #475569; margin: 0; }
.stTabs [data-testid="stTab"]:hover p { color: #0F172A; }
.stTabs [data-testid="stTab"][aria-selected="true"] { background: #FFFFFF; box-shadow: 0 1px 3px rgba(16, 24, 40, .14); }
.stTabs [data-testid="stTab"][aria-selected="true"] p { color: #0F172A !important; font-weight: 600; }
.stTabs .react-aria-SelectionIndicator { display: none; }
.stTabs [role="tablist"]::after, .stTabs [role="tablist"]::before { display: none; }

/* Buttons and alerts */
.stButton > button, .stFormSubmitButton > button { border-radius: 8px; font-weight: 600; }
[data-testid="stAlert"] { border-radius: 10px; }
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

PAGE_ICONS = {
    "Alert queue": ":material/inbox:",
    "Alert investigation": ":material/manage_search:",
    "Fraud risk model": ":material/psychology:",
    "Alert volume forecast": ":material/insights:",
}
SHIELD_SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v6c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6z"/>'
              '<path d="M9 12l2 2 4-4"/></svg>')


def page_header(eyebrow, title, subtitle, chips=()):
    """Product-style page header: eyebrow, title, one-line purpose and status chips."""
    target = globals().get("HERO", st)
    chip_html = "".join(f'<span class="chip {kind}">{html.escape(text)}</span>' for text, kind in chips)
    target.markdown(
        f'<div class="hero"><div><div class="eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>'
        f'<div class="chips">{chip_html}</div></div>', unsafe_allow_html=True)

# ============================================================
# 1. SETTINGS
# ============================================================
PAGES = ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast"]
BASE_POLICIES = {
    "P2 · Rule risk score": "P2",
    "P1 · Largest amount": "P1",
    "P0 · Random baseline": "P0",
}
MODEL_POLICIES = {
    "P4 · Expected exposure": "P4",
    "P3 · Fraud probability": "P3",
}
ACTIONS = {
    "ASSIGN_REVIEW": "Assigned for review",
    "CONFIRM_FRAUD": "Confirmed fraud",
    "CLEAR_LEGITIMATE": "Cleared as legitimate",
    "ESCALATE": "Escalated",
    "DEFER": "Deferred",
}
DISPOSITIONS = ["CONFIRM_FRAUD", "CLEAR_LEGITIMATE"]
REASONS = ["High 24h velocity", "Amount spike", "Rapid repeat", "New customer", "Large amount", "New device"]
RULE_FLAGS = {"R1": "r1_velocity", "R2": "r2_amount_spike", "R3": "r3_rapid_repeat",
              "R4": "r4_new_customer", "R5": "r5_large_amount", "R6": "r6_new_device"}
RULE_NAMES = {"r1": "High 24h velocity", "r2": "Amount spike", "r3": "Rapid repeat",
              "r4": "New customer", "r5": "Large amount", "r6": "New device"}
SOURCE_COLS = SOURCE_COLUMNS_ALL
TEXT_COLS = {"product_cd", "card6", "card4", "p_emaildomain"}
EVAL_PATH = os.path.join(ROOT, "reports", "week11", "evaluation_results.json")
RAISES, LOWERS = "#C0392B", "#2E86C1"
NOT_CAUSAL = ("These are associations the model learned from historical data. They show what the model "
              "relies on, not what causes fraud.")


# ============================================================
# 2. DATABASE AND MODELS
# ============================================================
@st.cache_resource
def get_engine():
    """Connect to PostgreSQL and make sure the decision-log table exists."""
    user = os.environ.get("PGUSER", "fraud_app")
    pwd = os.environ.get("PGPASSWORD", "")
    host = os.environ.get("PGHOST", "localhost")
    db = os.environ.get("PGDATABASE", "fraud_risk_db")
    auth = f"{user}:{pwd}@" if pwd else f"{user}@"
    engine = create_engine(f"postgresql+psycopg2://{auth}{host}/{db}")
    with open(os.path.join(ROOT, "sql", "ops", "create_decision_log.sql")) as f:
        ddl = f.read()
    with engine.begin() as conn:
        conn.exec_driver_sql(ddl)
    return engine


@st.cache_resource
def load_models():
    out = {}
    for key, name in [("fraud", "fraud_model.joblib"), ("volume", "alert_volume_model.joblib")]:
        path = os.path.join(MODEL_DIR, name)
        out[key] = joblib.load(path) if os.path.exists(path) else None
    return out


@st.cache_data
def query(sql, params=None):
    """Cached read for data that does not change while the app runs."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def query_live(sql, params=None):
    """Uncached read for the decision log, which changes as decisions are recorded."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def record_decision(row, day, policy, capacity, action, analyst, note):
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO ops_decision_log
                    (transaction_id, sim_day, policy_code, queue_rank, capacity, action, analyst_name, note)
                VALUES (:tid, :day, :policy, :rank, :cap, :action, :analyst, :note)
            """),
            {"tid": int(row["transaction_id"]), "day": int(day), "policy": policy,
             "rank": int(row["rank"]), "cap": int(capacity), "action": action,
             "analyst": analyst.strip(), "note": note.strip() or None},
        )


# ============================================================
# 3. DATA LOADERS
# ============================================================
def load_days():
    return query("SELECT sim_day, COUNT(*) AS n FROM alert_queue GROUP BY sim_day ORDER BY sim_day")


def load_day(day):
    src = ", ".join(f"t.{c}" + ("::float8" if c not in TEXT_COLS else "") + f" AS {c}" for c in SOURCE_COLS)
    return query(
        f"""
        SELECT a.transaction_id, a.customer_id, a.device_id, a.transaction_dt,
               a.transaction_amt::float8            AS transaction_amt,
               a.hours_since_previous_txn::float8   AS hours_since_previous_txn,
               a.txn_count_24h,
               a.customer_avg_amt_30d::float8       AS customer_avg_amt_30d,
               a.customer_amount_zscore::float8     AS customer_amount_zscore,
               f.customer_std_amt_30d::float8       AS customer_std_amt_30d,
               f.prior_txn_count, f.cold_start_flag,
               a.risk_score, a.reasons,
               a.r1_velocity, a.r2_amount_spike, a.r3_rapid_repeat,
               a.r4_new_customer, a.r5_large_amount, a.r6_new_device,
               {src}
        FROM alert_queue a
        JOIN transaction_features f USING (transaction_id)
        JOIN transaction t USING (transaction_id)
        WHERE a.sim_day = :day
        ORDER BY a.transaction_id
        """,
        {"day": int(day)},
    )


def load_rules():
    return query(
        "SELECT rule_code, rule_name, rule_text, ROUND(threshold, 4)::float8 AS threshold, basis "
        "FROM alert_rule_config ORDER BY rule_code"
    )


def load_history(customer_id, dt):
    """Customer's transactions in the 30 days up to and including this one (point-in-time)."""
    return query(
        """
        SELECT transaction_id, transaction_dt, transaction_amt::float8 AS transaction_amt, device_id
        FROM transaction_features
        WHERE customer_id = :c AND transaction_dt <= :dt AND transaction_dt >= :dt - 2592000
        ORDER BY transaction_dt
        """,
        {"c": customer_id, "dt": int(dt)},
    )


def daily_stats():
    return query(
        """
        SELECT sim_day, COUNT(*) AS alerts,
               SUM(r1_velocity::int)     AS r1, SUM(r2_amount_spike::int) AS r2,
               SUM(r3_rapid_repeat::int) AS r3, SUM(r4_new_customer::int) AS r4,
               SUM(r5_large_amount::int) AS r5, SUM(r6_new_device::int)   AS r6
        FROM alert_queue GROUP BY sim_day ORDER BY sim_day
        """
    )


def score_distribution(day):
    return query(
        """
        SELECT risk_score, COUNT(*) FILTER (WHERE sim_day = :day) AS today, COUNT(*) AS all_days
        FROM alert_queue GROUP BY risk_score ORDER BY risk_score
        """,
        {"day": int(day)},
    )


def latest_status(day):
    return query_live(
        """
        SELECT DISTINCT ON (transaction_id) transaction_id, action AS last_action, analyst_name, decided_at
        FROM ops_decision_log WHERE sim_day = :day
        ORDER BY transaction_id, decided_at DESC
        """,
        {"day": int(day)},
    )


def decision_history(tid):
    return query_live(
        """
        SELECT decided_at, action, analyst_name, policy_code, queue_rank, note
        FROM ops_decision_log WHERE transaction_id = :tid ORDER BY decided_at DESC
        """,
        {"tid": int(tid)},
    )


def team_metrics():
    log = query_live(
        "SELECT decision_id, transaction_id, sim_day, action, analyst_name, decided_at "
        "FROM ops_decision_log ORDER BY decided_at"
    )
    handled = query_live(
        """
        WITH a AS (
            SELECT transaction_id, MIN(decided_at) AS assigned_at
            FROM ops_decision_log WHERE action = 'ASSIGN_REVIEW' GROUP BY transaction_id
        ),
        d AS (
            SELECT DISTINCT ON (l.transaction_id) l.transaction_id, l.analyst_name, l.action, l.decided_at
            FROM ops_decision_log l JOIN a USING (transaction_id)
            WHERE l.action IN ('CONFIRM_FRAUD', 'CLEAR_LEGITIMATE') AND l.decided_at >= a.assigned_at
            ORDER BY l.transaction_id, l.decided_at
        )
        SELECT d.transaction_id, d.analyst_name, d.action,
               (EXTRACT(EPOCH FROM d.decided_at - a.assigned_at) / 60.0)::float8 AS handle_minutes
        FROM d JOIN a USING (transaction_id)
        """
    )
    return log, handled


# ============================================================
# 4. MODEL FUNCTIONS
# ============================================================
def fraud_scores(df, fm):
    """Probability, 90% range (bootstrap refits) and contributions for each row."""
    X, _ = fraud_design(df, fm["fill"], fm.get("feature_set", "week10"))
    Z = (X - fm["scaler_mean"]) / fm["scaler_sd"]
    logit = fm["intercept"] + Z @ fm["coef"]
    boot = fm["boot_intercept"][None, :] + Z @ fm["boot_coef"].T
    base, contrib = linear_contributions(Z, fm["coef"], fm["intercept"], fm["train_mean"])
    return {"p": sigmoid(logit), "lo": sigmoid(np.percentile(boot, 5, axis=1)),
            "hi": sigmoid(np.percentile(boot, 95, axis=1)), "base": base, "contrib": contrib}


def count_dist(mu, phi):
    """Predictive distribution for a daily count (negative binomial when overdispersed)."""
    if phi <= 1.0001:
        return poisson(mu)
    r = mu / (phi - 1.0)
    return nbinom(r, r / (r + mu))


def volume_forecast(vm, inp, day, capacity):
    """Forecast for `day` from the inputs known the evening before (dict with lag1, lag7_mean, lag2, lag7)."""
    X = volume_design([inp["lag1"]], [inp["lag7_mean"]], [day], [inp.get("lag2", np.nan)],
                      [inp.get("lag7", np.nan)], feature_set=vm.get("feature_set", "week10"))
    base, contrib = linear_contributions(X, vm["coef"], vm["intercept"], vm["train_mean"])
    mu = float(np.exp(vm["intercept"] + X[0] @ vm["coef"]))
    dist = count_dist(mu, vm["phi"])
    q = (1 - vm["interval"]) / 2
    k = np.arange(capacity + 1, int(dist.ppf(0.9999)) + 2)
    return {"mu": mu, "lo": float(dist.ppf(q)), "hi": float(dist.ppf(1 - q)),
            "p_over": float(1 - dist.cdf(capacity)),
            "exp_over": float(np.sum((k - capacity) * dist.pmf(k))),
            "base": base, "contrib": contrib[0]}


@st.cache_data
def load_evaluation():
    """Week 11 evaluation results written by src/modeling/evaluate_week11.py (if it has been run)."""
    if os.path.exists(EVAL_PATH):
        with open(EVAL_PATH) as f:
            return json.load(f)
    return None


def similar_case_rate(metrics, p):
    """Observed fraud rate on test days among transactions scored at a similar level (calibration tenth)."""
    cal = pd.DataFrame(metrics.get("calibration", []))
    if cal.empty:
        return None
    row = cal.iloc[(cal["mean_predicted"] - p).abs().argmin()]
    return float(row["observed_rate"]), int(row["n"])


def out_of_range(value, rng, label, fmt_):
    if rng is None or pd.isna(value):
        return None
    if value < rng["p01"] or value > rng["p99"]:
        return (f"{label} ({fmt_.format(value)}) is outside the range the model saw in 98% of training cases "
                f"({fmt_.format(rng['p01'])}–{fmt_.format(rng['p99'])}). Treat the prediction as an extrapolation.")
    return None


def check_fraud_inputs(inp, ranges, baseline=None):
    """Hard constraints (block the scenario) and plausibility warnings (allow, but flag)."""
    errors, warnings = [], []
    new, amt, cnt, hrs, avg, prior = (inp["new_customer"], inp["amount"], inp["count_24h"], inp["hours_prev"],
                                      inp["avg_30d"], inp["prior"])
    if amt <= 0:
        errors.append("Amount must be greater than $0.")
    if new:
        if prior > 0 or avg > 0 or cnt > 0:
            errors.append("A new customer has no history. Set prior transactions, 30-day average and transactions "
                          "in prior 24h to 0, or untick 'New customer'.")
    else:
        if prior < 1:
            errors.append("An existing customer needs at least 1 prior transaction (or tick 'New customer').")
        if hrs <= 0:
            errors.append("Hours since the previous transaction must be greater than 0.")
        if cnt > prior:
            errors.append("Transactions in the prior 24h cannot exceed the customer's prior transaction count.")
        if cnt >= 1 and hrs > 24:
            errors.append("There were transactions in the prior 24h, so hours since the previous transaction must "
                          "be 24 or less.")
        if cnt == 0 and 0 < hrs <= 24:
            errors.append("The previous transaction was within 24 hours, so transactions in the prior 24h must be "
                          "at least 1.")
        if hrs <= 720 and avg <= 0:
            errors.append("The previous transaction was within 30 days, so the customer's 30-day average must be "
                          "above $0.")
        if hrs > 720 and avg > 0:
            errors.append("The previous transaction was more than 30 days ago, so there is no 30-day average; "
                          "set it to 0.")
    if ranges:
        for key, col, label, f_ in [("amount", "transaction_amt", "Amount", "${:,.2f}"),
                                    ("count_24h", "txn_count_24h", "Transactions in prior 24h", "{:.0f}"),
                                    ("hours_prev", "hours_since_previous_txn", "Hours since previous", "{:,.1f}"),
                                    ("avg_30d", "customer_avg_amt_30d", "Customer 30-day average", "${:,.2f}"),
                                    ("prior", "prior_txn_count", "Prior transactions", "{:,.0f}")]:
            if new and key != "amount":
                continue
            if key == "avg_30d" and inp[key] == 0:
                continue
            if baseline is not None and abs(float(inp[key]) - float(baseline.get(key, np.nan))) < 1e-6:
                continue  # unchanged from the recorded case: no scenario warning
            w = out_of_range(inp[key], ranges.get(col), label, f_)
            if w:
                warnings.append(w)
    z = inp.get("zscore")
    if z is not None and not pd.isna(z) and abs(z) > 10:
        warnings.append(f"The amount is {z:.0f} standard deviations from this customer's usual spend; the model "
                        f"caps this signal at 10, so larger differences do not raise the prediction further.")
    return errors, warnings


def check_volume_inputs(inp, capacity, ranges, uses_lags, baseline=None):
    errors, warnings = [], []
    for k, label in [("lag1", "Alerts yesterday"), ("lag7_mean", "7-day average"), ("lag2", "Alerts two days ago"),
                     ("lag7", "Alerts same weekday last week")]:
        if k in inp and inp[k] < 0:
            errors.append(f"{label} cannot be negative.")
    if capacity < 1:
        errors.append("Review capacity must be at least 1.")
    in_window = inp["lag1"] + (inp["lag2"] + inp["lag7"] if uses_lags else 0)
    if inp["lag7_mean"] * 7 + 1e-9 < in_window:
        errors.append("The 7-day average includes yesterday" + (", two days ago and the same weekday last week"
                                                                if uses_lags else "") +
                      f", so it must be at least {in_window / 7:.1f} (their total ÷ 7).")
    if ranges:
        for k, label in [("lag1", "Alerts yesterday"), ("lag7_mean", "7-day average"), ("lag2", "Alerts two days ago"),
                         ("lag7", "Alerts same weekday last week")]:
            if baseline is not None and abs(inp[k] - baseline.get(k, np.nan)) < 1e-6:
                continue  # unchanged from the actual history: no scenario warning
            if k in ranges and (uses_lags or k in ("lag1", "lag7_mean")):
                w = out_of_range(inp[k], ranges[k], label, "{:,.0f}")
                if w:
                    warnings.append(w)
    return errors, warnings


def volume_ranges_from_history(history):
    s = pd.Series(history).sort_index()
    cols = {"lag1": s.shift(1), "lag2": s.shift(2), "lag7": s.shift(7), "lag7_mean": s.shift(1).rolling(7).mean()}
    return {k: {"p01": float(v.quantile(0.01)), "p99": float(v.quantile(0.99))} for k, v in cols.items()}


def contribution_chart(labels, values, value_title):
    df = pd.DataFrame({"Predictor": labels, "Contribution": values})
    df["Direction"] = np.where(df["Contribution"] >= 0, "Raises prediction", "Lowers prediction")
    return (alt.Chart(df).mark_bar()
            .encode(x=alt.X("Contribution:Q", title=value_title),
                    y=alt.Y("Predictor:N", sort=alt.EncodingSortField("Contribution", op="sum", order="descending"),
                            title=None, axis=alt.Axis(labelLimit=340)),
                    color=alt.Color("Direction:N", scale=alt.Scale(domain=["Raises prediction", "Lowers prediction"],
                                                                   range=[RAISES, LOWERS]),
                                    legend=alt.Legend(orient="bottom", title=None)),
                    tooltip=["Predictor", alt.Tooltip("Contribution:Q", format=".3f")])
            .properties(height=max(160, 26 * len(df))))


# ============================================================
# 5. QUEUE LOGIC AND HELPERS
# ============================================================
def sim_time(dt):
    dt = int(dt)
    return f"Day {dt // 86400}  {(dt % 86400) // 3600:02d}:{(dt % 3600) // 60:02d}"


def rank_queue(df, policy, day):
    df = df.copy()
    if policy == "P0":
        df["priority"] = np.random.default_rng(1000 + int(day)).random(len(df))
    elif policy == "P1":
        df["priority"] = df["transaction_amt"]
    elif policy == "P3":
        df["priority"] = df["fraud_prob"]
    elif policy == "P4":
        df["priority"] = df["exposure"]
    else:
        df["priority"] = df["risk_score"] + df["transaction_amt"] / (df["transaction_amt"].max() + 1)
    df = df.sort_values("priority", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    return df


def policy_comparison(raw, day, k, policies):
    total = raw["transaction_amt"].sum()
    steps = sorted(set(np.linspace(1, len(raw), num=min(40, len(raw))).astype(int)))
    rows, curves = [], {}
    for label, code in policies.items():
        ranked = rank_queue(raw, code, day)
        top = ranked.head(k)
        row = {"Policy": label, "Alerts reviewed": len(top),
               "Amount reviewed": top["transaction_amt"].sum(),
               "Share of alert amount": top["transaction_amt"].sum() / total,
               "Avg rule score": top["risk_score"].mean()}
        if "exposure" in ranked:
            row["Model-estimated fraud $ reviewed"] = top["exposure"].sum()
        rows.append(row)
        cum = ranked["transaction_amt"].cumsum().to_numpy()
        curves[label] = [cum[s - 1] / total * 100 for s in steps]
    curve = pd.DataFrame(curves, index=steps)
    curve.index.name = "Capacity (alerts reviewed)"
    return pd.DataFrame(rows), curve


def go_to_detail(tid):
    st.session_state["page"] = "Alert investigation"
    st.session_state["detail_txn"] = int(tid)


def set_detail(tid):
    st.session_state["detail_txn"] = int(tid)


def fmt(value, pattern):
    return "n/a (no history)" if pd.isna(value) else pattern.format(value)


def pct(x):
    return f"{x * 100:.1f}%"


# ============================================================
# 6. AUTOMATIC WHAT-IF SUMMARIES
# ============================================================
def fraud_summary(changes, b, s, queue_info, capacity, metrics, warnings, caution):
    """Five-part summary of a fraud what-if comparison."""
    lead = ("No inputs were changed, so the scenario equals the baseline." if not changes else
            "Changed: " + "; ".join(f"{k} {a} → {c}" for k, a, c in changes) + ".")
    diff = (s["p"] - b["p"]) * 100
    direction = "no change" if abs(diff) < 0.05 else (f"{abs(diff):.1f} points higher" if diff > 0
                                                      else f"{abs(diff):.1f} points lower")
    pos_b, pos_s, displaced, cutoff = (queue_info["pos_base"], queue_info["pos_scen"], queue_info["displaced"],
                                       queue_info["cutoff"])
    if pos_s <= capacity and pos_b > capacity:
        trade = (f"The scenario moves this case inside today's capacity (rank #{pos_b} → #{pos_s}). Reviewing it "
                 f"would push out the alert now at rank #{capacity}, whose expected exposure is ${displaced:,.2f}.")
    elif pos_s > capacity and pos_b <= capacity:
        trade = (f"The scenario moves this case outside today's capacity (rank #{pos_b} → #{pos_s}), freeing a "
                 f"review slot for the next alert in the queue.")
    elif pos_s <= capacity:
        trade = (f"The case stays inside today's capacity (rank #{pos_b} → #{pos_s}); no other alert is displaced.")
    else:
        trade = (f"The case stays outside today's capacity (rank #{pos_b} → #{pos_s}). Reviewing it anyway means "
                 f"skipping an alert with expected exposure of at least ${cutoff:,.2f}.")
    pr = metrics["comparison"]["Logistic regression (selected)"]["pr_auc"]
    lines = [
        f"**Inputs.** {lead} IEEE-CIS source attributes were held at their recorded values.",
        f"**Comparison.** Fraud probability {pct(b['p'])} → {pct(s['p'])} ({direction}); 90% model range "
        f"{pct(s['lo'])}–{pct(s['hi'])}. Expected exposure ${b['exp']:,.2f} → ${s['exp']:,.2f}."
        + (f" Largest drivers of the change: {queue_info['moves']}." if queue_info["moves"] else ""),
        f"**Trade-off.** {trade}",
        "**Implication.** " + ("Under the expected-exposure policy this scenario would be reviewed today."
                               if pos_s <= capacity else
                               "Under the expected-exposure policy this scenario would wait or expire unless "
                               "capacity rises or the Lead overrides the ranking."),
        f"**Limitations.** A model-based scenario: it shows how the model's estimate responds, not what would happen "
        f"if the transaction or customer were different, and not proof of fraud or of cause. On later test days the "
        f"model reached PR-AUC {pr:.2f}, so many high-probability alerts are still legitimate. The range covers "
        f"uncertainty in the model's coefficients only."
        + (" " + " ".join(warnings) if warnings else "") + (f" {caution}" if caution else ""),
    ]
    return "\n\n".join(lines)


def volume_summary(changes, base, new, base_cap, new_cap, metrics, warnings, busy_bias):
    lead = ("No inputs were changed, so the scenario equals the baseline." if not changes else
            "Changed: " + "; ".join(f"{k} {a} → {c}" for k, a, c in changes) + ".")
    diff = new["mu"] - base["mu"]
    if new_cap != base_cap:
        saved = base["exp_over_newcap_base"] - new["exp_over"]
        per_slot = saved / (new_cap - base_cap) if new_cap != base_cap else 0
        trade = (f"Changing capacity from {base_cap} to {new_cap} reviews changes expected overflow from "
                 f"{base['exp_over_newcap_base']:.0f} to {new['exp_over']:.0f} alerts under the scenario inputs "
                 f"(about {abs(per_slot):.2f} fewer unreviewed alerts per extra review slot), at the cost of "
                 f"{abs(new_cap - base_cap)} {'more' if new_cap > base_cap else 'fewer'} reviews of analyst time.")
    else:
        trade = ("Capacity was unchanged; the comparison shows how the forecast responds to different alert "
                 "conditions, not to a staffing decision.")
    lines = [
        f"**Inputs.** {lead}",
        f"**Comparison.** Forecast {base['mu']:.0f} → {new['mu']:.0f} alerts ({diff:+.0f}); 90% range "
        f"{new['lo']:.0f}–{new['hi']:.0f}. Chance of overflow {pct(base['p_over'])} → {pct(new['p_over'])}; "
        f"expected alerts beyond capacity {base['exp_over']:.0f} → {new['exp_over']:.0f}.",
        f"**Trade-off.** {trade}",
        "**Implication.** "
        + ("Overflow is more likely than not: consider adding review capacity or deferring low-exposure alerts."
           if new["p_over"] > 0.5 else
           "Capacity is likely sufficient; the remaining risk is a busy day in the upper part of the range."),
        f"**Limitations.** A model-based scenario, not a guarantee. The forecast assumes the alerting rules and "
        f"transaction mix stay as they were in training. Its 90% range contained the actual count on "
        f"{metrics['interval_coverage_test']:.0%} of test days."
        + (f" On the busiest test days it under-forecast by about {busy_bias:.0f} alerts on average, so plan for "
           f"the upper part of the range." if busy_bias and busy_bias > 1 else "")
        + " Changing yesterday's count shows how the model responds; it does not cause tomorrow's volume."
        + (" " + " ".join(warnings) if warnings else ""),
    ]
    return "\n\n".join(lines)


# ============================================================
# 7. TOP NAVIGATION AND SETTINGS TOOLBAR
# ============================================================
models = load_models()
fm, vm = models["fraud"], models["volume"]
policies = {**(MODEL_POLICIES if fm else {}), **BASE_POLICIES}

with st.container(key="topnav"):
    n1, n2, n3 = st.columns([2.2, 6, 2.2])
    n1.markdown(f'<div class="brand"><div class="brand-logo">{SHIELD_SVG}</div><div><div class="brand-name">'
                f'FraudOps</div><div class="brand-sub">Decision Intelligence</div></div></div>',
                unsafe_allow_html=True)
    with n2:
        page = st.radio("Navigation", PAGES, key="page", horizontal=True, label_visibility="collapsed",
                        format_func=lambda p: f"{PAGE_ICONS[p]}&nbsp;{p}")
    n3.markdown('<div class="user-pill"><div><div class="user-name">Fraud Operations Lead</div>'
                '<div class="user-sub">Demo workspace · simulated data</div></div><div class="avatar">FL</div></div>',
                unsafe_allow_html=True)

days = load_days()
HERO = st.container()  # the page banner is drawn here, above the settings toolbar
with st.container(key="toolbar"):
    st.markdown('<div class="toolbar-title">Decision settings · what-if controls used by every page</div>',
                unsafe_allow_html=True)
    t1, t2, t3 = st.columns([1.2, 1.4, 1.6])
    day = t1.selectbox(
        "Simulated day", days["sim_day"].tolist(),
        format_func=lambda d: f"Day {d}  ({int(days.loc[days.sim_day == d, 'n'].iloc[0])} alerts)")
    policy_label = t2.selectbox("Queue policy", list(policies.keys()))
    capacity = t3.slider("Review capacity (alerts per day)", 5, 300, 50, 5,
                         help="Assumption: how many alerts the analyst team can review today.")
policy = policies[policy_label]
if not fm or not vm:
    st.warning("Model files not found. Run the scripts in src/modeling/ to enable the model pages.")
POLICY_SHORT = {v: k.split(" · ")[1] for k, v in policies.items()}

raw = load_day(day)
if fm:
    sc = fraud_scores(raw, fm)
    raw = raw.assign(fraud_prob=sc["p"], prob_lo=sc["lo"], prob_hi=sc["hi"],
                     exposure=sc["p"] * raw["transaction_amt"])
queue = rank_queue(raw, policy, day)
queue["action"] = np.where(queue["rank"] <= capacity, "Review today", "Wait / expire")
queue = queue.merge(latest_status(day), on="transaction_id", how="left")
queue["status"] = queue["last_action"].map(ACTIONS).fillna("Open")

# ============================================================
# 8. PAGE — ALERT QUEUE
# ============================================================
if page == "Alert queue":
    over = len(queue) - capacity
    page_header(f"Operations · Day {day}", "Alert queue",
                "Today's alerts ranked by the selected policy, with what fits inside review capacity.",
                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"Capacity {capacity}", "neutral"),
                 (f"{over} over capacity", "warn") if over > 0 else ("Within capacity", "ok")])

    selected = queue[queue["action"] == "Review today"]
    waiting = queue[queue["action"] != "Review today"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Alerts today", len(queue))
    c2.metric("Selected for review", len(selected))
    c3.metric("Amount under review", f"${selected['transaction_amt'].sum():,.0f}")
    c4.metric("Not reviewed today", len(waiting), help="At risk of missing the 24-hour deadline.")
    if fm:
        c5.metric("Est. fraud $ in review", f"${selected['exposure'].sum():,.0f}",
                  help="Sum of probability × amount for the selected alerts (a model estimate).")
    else:
        c5.metric("Decisions recorded", int((queue["status"] != "Open").sum()))
    if len(queue) > capacity:
        st.warning(f"{len(queue) - capacity} alerts exceed today's capacity — "
                   f"${waiting['transaction_amt'].sum():,.0f} in transactions will not be reviewed.")

    tab_queue, tab_compare, tab_volume, tab_trends, tab_team = st.tabs(
        ["Queue", "Compare policies", "Alert volume", "Trends and rules", "Team performance"])

    with tab_queue:
        f1, f2, f3, f4 = st.columns([1, 2, 1, 1])
        min_score = f1.slider("Min rule score", 2, 6, 2)
        reasons = f2.multiselect("Reason contains any of", REASONS)
        action_filter = f3.selectbox("Action", ["All", "Review today", "Wait / expire"])
        search = f4.text_input("Search transaction or customer")

        view = queue[queue["risk_score"] >= min_score]
        if reasons:
            view = view[view["reasons"].apply(lambda r: any(x in r for x in reasons))]
        if action_filter != "All":
            view = view[view["action"] == action_filter]
        if search.strip():
            s = search.strip()
            view = view[view["transaction_id"].astype(str).str.contains(s)
                        | view["customer_id"].astype(str).str.contains(s, case=False)]
        view = view.reset_index(drop=True)

        st.caption(f"Showing {len(view)} of {len(queue)} alerts. Click a row to open it.")
        cols = ["rank", "action", "status", "transaction_id", "time", "transaction_amt"]
        cols += ["fraud_pct", "exposure"] if fm else []
        cols += ["risk_score", "reasons", "customer_id"]
        table = view.assign(time=view["transaction_dt"].map(sim_time))
        if fm:
            table = table.assign(fraud_pct=table["fraud_prob"] * 100)
        event = st.dataframe(
            table[cols], hide_index=True, width="stretch",
            on_select="rerun", selection_mode="single-row", key="queue_table",
            column_config={
                "rank": "Rank", "action": "Action", "status": "Status", "time": "Time",
                "customer_id": "Customer", "reasons": "Rules fired",
                "transaction_amt": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "fraud_pct": st.column_config.NumberColumn("Fraud probability", format="%.1f%%"),
                "exposure": st.column_config.NumberColumn("Expected exposure", format="$%.2f",
                                                          help="Fraud probability × amount"),
                "risk_score": st.column_config.ProgressColumn("Rule score", min_value=0, max_value=6,
                                                              format="%d / 6"),
                "transaction_id": st.column_config.NumberColumn("Transaction", format="%d"),
            },
        )
        if event.selection.rows:
            tid = int(view.iloc[event.selection.rows[0]]["transaction_id"])
            st.button(f"Investigate transaction {tid} →", type="primary", on_click=go_to_detail, args=(tid,))

        with st.expander("How alerts are created"):
            st.dataframe(load_rules(), hide_index=True, width="stretch")
            st.caption("A transaction becomes an alert when 2 or more rules fire. Thresholds come from feature "
                       "percentiles; the fraud label is never used to set them. The fraud model then estimates "
                       "each alert's probability so the queue can be ranked by expected exposure.")

    with tab_compare:
        summary, curve = policy_comparison(raw, day, capacity, policies)
        st.subheader(f"What each policy would review today at capacity {capacity}")
        st.dataframe(summary, hide_index=True, width="stretch",
                     column_config={
                         "Amount reviewed": st.column_config.NumberColumn(format="$%.0f"),
                         "Share of alert amount": st.column_config.NumberColumn(format="%.1%"),
                         "Avg rule score": st.column_config.NumberColumn(format="%.2f"),
                         "Model-estimated fraud $ reviewed": st.column_config.NumberColumn(format="$%.0f"),
                     })
        st.subheader("Share of today's alert amount covered as capacity grows (%)")
        st.line_chart(curve)
        st.caption("Model-estimated fraud dollars use the fraud model's probabilities, not confirmed outcomes. "
                   "Measured performance on held-out days is on the Fraud risk model page.")

    with tab_volume:
        vol = days.set_index("sim_day")["n"]
        chart = pd.DataFrame({"Within capacity": vol.clip(upper=capacity),
                              "Overflow": (vol - capacity).clip(lower=0)})
        chart.index.name = "Simulated day"
        st.subheader(f"Alerts per day vs. capacity of {capacity}")
        st.bar_chart(chart)
        st.caption(f"{int((vol > capacity).sum())} of {len(vol)} days exceed capacity "
                   f"({int(chart['Overflow'].sum()):,} alerts in total would go unreviewed).")

    with tab_trends:
        stats = daily_stats().set_index("sim_day")
        rule_cols = list(RULE_NAMES)
        trend = pd.DataFrame({"Alerts": stats["alerts"],
                              "7-day average": stats["alerts"].rolling(7, min_periods=1).mean(),
                              "Capacity": capacity})
        trend.index.name = "Simulated day"
        st.subheader("Alert volume trend")
        st.line_chart(trend)
        peak = int(stats["alerts"].idxmax())
        st.caption(f"Busiest day: Day {peak} ({int(stats.loc[peak, 'alerts'])} alerts). "
                   f"Average {stats['alerts'].mean():.0f} alerts per day.")
        r_left, r_right = st.columns(2)
        with r_left:
            st.subheader("Which rules trigger alerts")
            totals = pd.DataFrame({f"Day {day}": stats.loc[day, rule_cols].astype(float),
                                   "All days": stats[rule_cols].sum().astype(float)})
            totals.index = [RULE_NAMES[c] for c in totals.index]
            st.bar_chart(totals / totals.sum() * 100, stack=False)
            st.caption("Share of rule firings (%). One alert can fire several rules.")
        with r_right:
            st.subheader("Rule score distribution")
            dist = score_distribution(day).set_index("risk_score").astype(float)
            dist.columns = [f"Day {day}", "All days"]
            st.bar_chart(dist / dist.sum() * 100, stack=False)
            st.caption("Percentage of alerts at each rule score (2–6).")
        st.subheader("Rule firings over time (7-day average)")
        over_time = stats[rule_cols].rename(columns=RULE_NAMES).rolling(7, min_periods=1).mean()
        over_time.index.name = "Simulated day"
        st.area_chart(over_time)

    with tab_team:
        log, handled = team_metrics()
        if log.empty:
            st.info("No decisions recorded yet. Record decisions on the Alert investigation page.")
        else:
            disp = log[log["action"].isin(DISPOSITIONS)]
            confirmed = int((disp["action"] == "CONFIRM_FRAUD").sum())
            resolved_today = disp.loc[disp["sim_day"] == day, "transaction_id"].nunique()
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Decisions recorded", len(log))
            m2.metric("Alerts resolved", disp["transaction_id"].nunique())
            m3.metric("Avg handle time",
                      f"{handled['handle_minutes'].mean():.1f} min" if not handled.empty else "—",
                      help="First 'Assigned for review' to first final decision, per alert.")
            m4.metric("Fraud confirmation rate", f"{confirmed / len(disp):.0%}" if len(disp) else "—")
            m5.metric(f"Capacity used (Day {day})", f"{resolved_today / capacity:.0%}")
            t_left, t_right = st.columns([3, 2])
            with t_left:
                st.subheader("By analyst")
                per = log.groupby("analyst_name").agg(decisions=("decision_id", "count"),
                                                      alerts_touched=("transaction_id", "nunique"))
                per = per.join(disp.groupby("analyst_name").agg(
                    resolved=("transaction_id", "nunique"),
                    confirmed_fraud=("action", lambda s: int((s == "CONFIRM_FRAUD").sum()))), how="left")
                per = per.join(handled.groupby("analyst_name")["handle_minutes"].mean()
                               .rename("avg_handle_min"), how="left")
                per[["resolved", "confirmed_fraud"]] = per[["resolved", "confirmed_fraud"]].fillna(0)
                st.dataframe(per.reset_index(), hide_index=True, width="stretch",
                             column_config={"avg_handle_min": st.column_config.NumberColumn(
                                 "Avg handle (min)", format="%.1f")})
            with t_right:
                st.subheader("Decisions by action")
                st.bar_chart(log["action"].map(ACTIONS).value_counts())
            st.caption("Computed from decisions recorded in this app (ops_decision_log).")

# ============================================================
# 9. PAGE — ALERT INVESTIGATION
# ============================================================
elif page == "Alert investigation":
    page_header(f"Investigation · Day {day}", "Alert investigation",
                "Why an alert was raised, what the model sees, how it responds to change, and the decision.",
                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"{len(queue)} alerts in queue", "neutral")])
    ids = queue["transaction_id"].astype(int).tolist()
    if st.session_state.get("detail_txn") not in ids:
        st.session_state["detail_txn"] = ids[0]

    def label(t):
        r = queue[queue.transaction_id == t].iloc[0]
        extra = f" · {pct(r['fraud_prob'])} fraud" if fm else f" · rule score {r['risk_score']}"
        return f"#{r['rank']} · Txn {t} · ${r['transaction_amt']:,.2f}{extra} · {r['status']}"

    pos = ids.index(st.session_state["detail_txn"])
    n1, n2, n3 = st.columns([1, 6, 1])
    n1.button("← Previous", disabled=pos == 0, on_click=set_detail,
              args=(ids[max(pos - 1, 0)],), width="stretch")
    n2.selectbox("Alert (in queue rank order)", ids, key="detail_txn", format_func=label,
                 label_visibility="collapsed")
    n3.button("Next →", disabled=pos == len(ids) - 1, on_click=set_detail,
              args=(ids[min(pos + 1, len(ids) - 1)],), width="stretch")

    choice = st.session_state["detail_txn"]
    row = queue[queue.transaction_id == choice].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Amount", f"${row['transaction_amt']:,.2f}")
    if fm:
        c2.metric("Fraud probability", pct(row["fraud_prob"]),
                  help=f"90% model range {pct(row['prob_lo'])}–{pct(row['prob_hi'])}")
        c4.metric("Expected exposure", f"${row['exposure']:,.2f}", help="Fraud probability × amount")
    else:
        c2.metric("Rule score", f"{row['risk_score']} / 6")
        c4.metric("Rule score", f"{row['risk_score']} / 6")
    c3.metric("Queue rank", f"#{row['rank']} of {len(queue)}")
    in_cap = row["action"] == "Review today"
    st.markdown(
        '<div class="chips" style="margin:2px 0 14px 0">'
        f'<span class="chip {"ok" if in_cap else "warn"}">Recommended: {html.escape(row["action"])}</span>'
        f'<span class="chip neutral">Status: {html.escape(row["status"])}</span>'
        f'<span class="chip neutral">Customer {html.escape(str(row["customer_id"]))}</span>'
        f'<span class="chip neutral">{html.escape(sim_time(row["transaction_dt"]))}</span></div>',
        unsafe_allow_html=True)

    tab_why, tab_model, tab_whatif, tab_decide = st.tabs(
        ["Rules and history", "Model explanation", "What-if analysis", "Record decision"])

    with tab_why:
        left, right = st.columns(2)
        with left:
            st.subheader("Rules that created this alert")
            rules = load_rules()
            rules["fired"] = rules["rule_code"].map(lambda c: "✔ Yes" if bool(row[RULE_FLAGS[c]]) else "—")
            st.dataframe(rules[["fired", "rule_name", "rule_text"]], hide_index=True, width="stretch",
                         column_config={"fired": "Fired", "rule_name": "Rule", "rule_text": "Condition"})
            st.subheader("This transaction vs. customer history")
            st.table(pd.DataFrame({
                "Feature": ["Hours since previous transaction", "Transactions in prior 24h",
                            "Customer avg amount (prior 30 days)", "Amount z-score vs. customer"],
                "Value": [fmt(row["hours_since_previous_txn"], "{:.2f}"), fmt(row["txn_count_24h"], "{:.0f}"),
                          fmt(row["customer_avg_amt_30d"], "${:,.2f}"),
                          fmt(row["customer_amount_zscore"], "{:.2f}")],
            }))
        with right:
            st.subheader("Customer's last 30 days")
            hist = load_history(row["customer_id"], row["transaction_dt"])
            if len(hist) <= 1:
                st.info("No earlier transactions: this is a new customer.")
            else:
                hist["hours_before"] = (hist["transaction_dt"] - int(row["transaction_dt"])) / 3600.0
                hist["type"] = np.where(hist["transaction_id"] == choice, "This transaction", "Earlier")
                st.scatter_chart(hist, x="hours_before", y="transaction_amt", color="type",
                                 x_label="Hours before this transaction (0 = now)", y_label="Amount ($)")
            st.caption("Only information available at the time of the transaction is shown (point-in-time rule).")

    with tab_model:
        if not fm:
            st.info("Train the fraud model to see explanations.")
        else:
            one = queue[queue.transaction_id == choice]
            s1 = fraud_scores(one, fm)
            contrib = s1["contrib"][0]
            base_p = float(sigmoid(s1["base"]))
            sim = similar_case_rate(fm["metrics"], float(row["fraud_prob"]))
            with st.container(border=True):
                st.markdown("**How much to trust this number**")
                st.markdown(
                    f"The model estimates a **{pct(row['fraud_prob'])}** chance of fraud "
                    f"(90% model range {pct(row['prob_lo'])}–{pct(row['prob_hi'])})."
                    + (f" On test days the model had never seen, transactions it scored at a similar level turned "
                       f"out to be fraud **{pct(sim[0])}** of the time (based on {sim[1]:,} transactions)."
                       if sim else "")
                    + " It ranks cases for review; it does not prove that this transaction is fraud.")
            st.subheader("Why the model gave this probability (this alert only)")
            st.markdown(f"An average transaction in the training data scores **{pct(base_p)}**. "
                        f"Each bar shows how much one predictor moved **this transaction** from that "
                        f"average, on the log-odds scale. The bars add up to **{pct(row['fraud_prob'])}**.")
            labels = [fm["labels"][f] for f in fm["features"]]
            order = np.argsort(-np.abs(contrib))[:10]
            st.altair_chart(contribution_chart([labels[i] for i in order], contrib[order],
                                               "Contribution to this prediction (log-odds)"),
                            width="stretch")
            up = [labels[i] for i in order if contrib[i] > 0][:3]
            down = [labels[i] for i in order if contrib[i] < 0][:2]
            st.markdown("**Reading it.** "
                        + (f"The biggest upward pushes come from {', '.join(up)}. " if up else "")
                        + (f"{', '.join(down)} pulled the estimate down. " if down else "")
                        + "A bar of +0.7 roughly doubles the odds of fraud; −0.7 roughly halves them.")
            st.caption("This chart explains one prediction (local explanation). Overall importance across all "
                       "transactions is a different view, on the Fraud risk model page. " + NOT_CAUSAL
                       + " IEEE count variables C1–C14 are anonymized by the data provider and strongly "
                         "correlated with each other, so read them as a group rather than one at a time.")

    with tab_whatif:
        if not fm:
            st.info("Train the fraud model to enable what-if analysis.")
        else:
            one = queue[queue.transaction_id == choice].iloc[[0]].copy()
            st.subheader("Compare this alert with a what-if scenario")
            st.caption("The baseline is the transaction as recorded. Edit the inputs below and run the scenario; "
                       "the result is shown side by side with the baseline.")
            cold = bool(one["cold_start_flag"].iloc[0])
            std = one["customer_std_amt_30d"].iloc[0]
            hrs0 = one["hours_since_previous_txn"].iloc[0]
            avg0 = one["customer_avg_amt_30d"].iloc[0]
            ranges = fm.get("ranges")
            with st.form("fraud_whatif"):
                st.markdown("**① Transaction details** · *scenario inputs* — describe a different transaction. "
                            "These are characteristics of the case, not something the bank controls.")
                w1, w2, w3 = st.columns(3)
                amt = w1.number_input("Amount ($)", min_value=0.0, value=float(one["transaction_amt"].iloc[0]),
                                      step=10.0)
                cnt = w2.number_input("Transactions in prior 24h", min_value=0,
                                      value=int(one["txn_count_24h"].iloc[0]), step=1)
                hrs = w3.number_input("Hours since previous transaction", min_value=0.0,
                                      value=0.0 if pd.isna(hrs0) else float(hrs0), step=1.0,
                                      help="Leave at 0 for a new customer.")
                st.markdown("**② Customer history** · *fixed characteristics* — normally fixed for a given customer; "
                            "change them only to test how sensitive the prediction is.")
                w4, w5, w6 = st.columns(3)
                new_cust = w4.checkbox("New customer (no history)", value=cold)
                avg = w5.number_input("Customer avg amount, 30 days ($)", min_value=0.0,
                                      value=0.0 if pd.isna(avg0) else float(avg0), step=10.0,
                                      help="0 means no purchases in the last 30 days.")
                prior = w6.number_input("Customer's prior transaction count", min_value=0,
                                        value=int(one["prior_txn_count"].iloc[0]), step=1)
                st.markdown("**③ Recorded source attributes** · *fixed* — IEEE-CIS counts, time deltas, product code "
                            "and card details stay at their recorded values.")
                st.caption("The Lead's own decision levers are the queue policy and review capacity in the "
                           "settings toolbar; this comparison explores how the model responds to a different case.")
                run = st.form_submit_button("Run scenario", type="primary")

            if run:
                zscore = ((amt - avg) / std) if (not new_cust and avg > 0 and pd.notna(std) and std > 0) else np.nan
                inp = {"new_customer": new_cust, "amount": amt, "count_24h": cnt, "hours_prev": hrs,
                       "avg_30d": avg, "prior": prior, "zscore": zscore}
                base_inp = {"amount": float(one["transaction_amt"].iloc[0]),
                            "count_24h": float(one["txn_count_24h"].iloc[0]),
                            "hours_prev": 0.0 if pd.isna(hrs0) else float(hrs0),
                            "avg_30d": 0.0 if pd.isna(avg0) else float(avg0),
                            "prior": float(one["prior_txn_count"].iloc[0])}
                errors, warnings = check_fraud_inputs(inp, ranges, base_inp)
                if errors:
                    st.session_state["fraud_whatif_result"] = {"txn": choice, "errors": errors}
                else:
                    scen = one.copy()
                    scen["transaction_amt"] = amt
                    scen["txn_count_24h"] = cnt
                    if new_cust:
                        scen[["hours_since_previous_txn", "customer_avg_amt_30d", "customer_amount_zscore"]] = np.nan
                        scen["prior_txn_count"], scen["cold_start_flag"] = 0, True
                    else:
                        scen["hours_since_previous_txn"] = hrs
                        scen["customer_avg_amt_30d"] = avg if avg > 0 else np.nan
                        scen["prior_txn_count"], scen["cold_start_flag"] = prior, False
                        scen["customer_amount_zscore"] = zscore
                    b, sc = fraud_scores(one, fm), fraud_scores(scen, fm)
                    names = [("transaction_amt", "Amount", "${:,.2f}", "scenario input"),
                             ("txn_count_24h", "Transactions in prior 24h", "{:.0f}", "scenario input"),
                             ("hours_since_previous_txn", "Hours since previous", "{:,.1f}", "scenario input"),
                             ("cold_start_flag", "New customer", "{}", "fixed characteristic"),
                             ("customer_avg_amt_30d", "Customer avg amount (30 days)", "${:,.2f}",
                              "fixed characteristic"),
                             ("prior_txn_count", "Prior transaction count", "{:,.0f}", "fixed characteristic")]
                    show = lambda v, f_, col: ("none" if pd.isna(v) else
                                               ("Yes" if v else "No") if col == "cold_start_flag" else f_.format(v))
                    rows_cmp, changes = [], []
                    for col, nm, f_, role in names:
                        a0, a1 = one[col].iloc[0], scen[col].iloc[0]
                        same = (pd.isna(a0) and pd.isna(a1)) or (not pd.isna(a0) and not pd.isna(a1) and a0 == a1)
                        chg = "—" if same else (f"{a1 - a0:+,.2f}" if col not in ("cold_start_flag",) and
                                                not pd.isna(a0) and not pd.isna(a1) else "changed")
                        rows_cmp.append({"Item": nm, "Role": role, "Baseline": show(a0, f_, col),
                                         "Scenario": show(a1, f_, col), "Difference": chg})
                        if not same:
                            changes.append((nm, show(a0, f_, col), show(a1, f_, col)))
                    pb, ps = float(b["p"][0]), float(sc["p"][0])
                    exp_b, exp_s = pb * float(one["transaction_amt"].iloc[0]), ps * amt
                    others = queue[queue.transaction_id != choice]["exposure"].sort_values(ascending=False)
                    pos_b, pos_s = int((others > exp_b).sum()) + 1, int((others > exp_s).sum()) + 1
                    cutoff = float(others.iloc[capacity - 1]) if len(others) >= capacity else 0.0
                    displaced = float(others.iloc[capacity - 1]) if len(others) >= capacity else 0.0
                    rows_cmp += [
                        {"Item": "Fraud probability", "Role": "prediction", "Baseline": pct(pb), "Scenario": pct(ps),
                         "Difference": f"{(ps - pb) * 100:+.1f} pts"},
                        {"Item": "90% model range", "Role": "prediction",
                         "Baseline": f"{pct(b['lo'][0])}–{pct(b['hi'][0])}",
                         "Scenario": f"{pct(sc['lo'][0])}–{pct(sc['hi'][0])}", "Difference": "—"},
                        {"Item": "Expected exposure (probability × amount)", "Role": "prediction",
                         "Baseline": f"${exp_b:,.2f}", "Scenario": f"${exp_s:,.2f}", "Difference": f"{exp_s - exp_b:+,.2f}"},
                        {"Item": "Rank in today's queue (expected exposure)", "Role": "decision",
                         "Baseline": f"#{pos_b} of {len(queue)}", "Scenario": f"#{pos_s} of {len(queue)}",
                         "Difference": "no change" if pos_s == pos_b else
                         f"{abs(pos_s - pos_b)} places {'lower' if pos_s > pos_b else 'higher'} priority"},
                        {"Item": f"Inside today's capacity of {capacity}", "Role": "decision",
                         "Baseline": "Yes" if pos_b <= capacity else "No",
                         "Scenario": "Yes" if pos_s <= capacity else "No", "Difference": "—"},
                    ]
                    delta = sc["contrib"][0] - b["contrib"][0]
                    labels = [fm["labels"][f] for f in fm["features"]]
                    moves = ", ".join(f"{labels[i]} ({'+' if delta[i] > 0 else '−'})"
                                      for i in np.argsort(-np.abs(delta))[:3] if abs(delta[i]) > 0.01)
                    weak = fm["metrics"].get("error_analysis", {}).get("weak_segments", [])
                    product = f"product={one['product_cd'].iloc[0]}"
                    caution = (f"Caution: the model was weaker on {product.replace('product=', 'product code ')} "
                               f"transactions in the final test." if product in weak else "")
                    res = {"txn": choice, "errors": None, "warnings": warnings, "table": rows_cmp,
                           "base": pb, "p": ps,
                           "summary": fraud_summary(changes, {"p": pb, "exp": exp_b},
                                                    {"p": ps, "lo": float(sc["lo"][0]), "hi": float(sc["hi"][0]),
                                                     "exp": exp_s},
                                                    {"pos_base": pos_b, "pos_scen": pos_s, "displaced": displaced,
                                                     "cutoff": cutoff, "moves": moves},
                                                    capacity, fm["metrics"], warnings, caution)}
                    st.session_state["fraud_whatif_result"] = res
                    st.session_state.setdefault("fraud_whatif_log", []).append({
                        "Transaction": choice,
                        "Changes": "; ".join(f"{k} {a}→{c}" for k, a, c in changes) or "none",
                        "Baseline": pct(pb), "Scenario": pct(ps), "Change (pts)": round((ps - pb) * 100, 1),
                        "Rank": f"#{pos_b} → #{pos_s}"})

            res = st.session_state.get("fraud_whatif_result")
            if res and res["txn"] == choice:
                if res.get("errors"):
                    st.error("**Scenario not run — the inputs are inconsistent:**\n\n"
                             + "\n".join(f"- {e}" for e in res["errors"]))
                else:
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Baseline (as recorded)", pct(res["base"]))
                    k2.metric("Scenario", pct(res["p"]), delta=f"{(res['p'] - res['base']) * 100:+.1f} pts",
                              delta_color="inverse")
                    k3.metric("Queue rank", res["table"][-2]["Baseline"].split(" of ")[0] + " → "
                              + res["table"][-2]["Scenario"].split(" of ")[0],
                              help="Rank 1 is reviewed first; a larger number means lower priority.")
                    if res["warnings"]:
                        st.warning("**Plausibility warnings:**\n\n" + "\n".join(f"- {w}" for w in res["warnings"]))
                    st.markdown("#### Baseline vs. scenario")
                    st.dataframe(pd.DataFrame(res["table"]), hide_index=True, width="stretch",
                         height=35 * (len(res["table"]) + 1) + 3)
                    st.markdown("#### Scenario summary")
                    st.info(res["summary"].replace("$", "\\$"))
            if st.session_state.get("fraud_whatif_log"):
                with st.expander("Scenarios run in this session"):
                    st.dataframe(pd.DataFrame(st.session_state["fraud_whatif_log"]), hide_index=True,
                                 width="stretch")

    with tab_decide:
        d_left, d_right = st.columns(2)
        with d_left:
            with st.form("decision_form", clear_on_submit=True):
                analyst = st.text_input("Analyst name", value=st.session_state.get("analyst", "Fraud Analyst 1"))
                action = st.selectbox("Action", list(ACTIONS.keys()), format_func=lambda a: ACTIONS[a])
                note = st.text_area("Note (optional)", placeholder="e.g. Customer confirmed purchase by phone")
                submitted = st.form_submit_button("Save decision", type="primary")
            if submitted:
                if not analyst.strip():
                    st.error("Enter an analyst name.")
                else:
                    st.session_state["analyst"] = analyst
                    record_decision(row, day, policy, capacity, action, analyst, note)
                    st.toast(f"Saved: {ACTIONS[action]} for transaction {choice}.")
                    st.rerun()
        with d_right:
            st.subheader("Decision history")
            log = decision_history(choice)
            if log.empty:
                st.info("No decisions recorded yet.")
            else:
                log["action"] = log["action"].map(ACTIONS)
                st.dataframe(log, hide_index=True, width="stretch")

# ============================================================
# 10. PAGE — FRAUD RISK MODEL (KPI 1)
# ============================================================
elif page == "Fraud risk model":
    ev = load_evaluation()
    page_header("Predictive model · KPI 1", "Fraud risk model",
                "How well the fraud model ranks risk on later days, where it is weaker, and what drives it.",
                [("Logistic regression", ""), ("Evaluated on later, unseen days", "neutral")])
    if not fm:
        st.info("Run `python3 src/modeling/evaluate_week11.py` to build the model.")
        st.stop()
    m = fm["metrics"]
    cap = pd.DataFrame(m["capture_at_capacity"])

    def cap_at(policy_prefix, k=50):
        r = cap[(cap.policy.str.startswith(policy_prefix)) & (cap.capacity == k)]
        return float(r.fraud_value_captured.iloc[0]) if len(r) else None

    cal = pd.DataFrame(m["calibration"])
    top_rate = float(cal.sort_values("mean_predicted").iloc[-1]["observed_rate"]) if len(cal) else None
    base_rate = m["split"]["test_fraud_rate"]
    ea = m.get("error_analysis", {})
    with st.container(border=True):
        st.markdown("#### How much to trust this model")
        p4, p1 = cap_at("P4"), cap_at("P1")
        bullets = []
        if p4 is not None and p1 is not None:
            bullets.append(f"On days the model never saw, reviewing the **50 alerts with the highest expected "
                           f"exposure** caught about **{p4:.0%} of fraud dollars**, compared with {p1:.0%} when "
                           f"reviewing the largest amounts first.")
        if top_rate is not None:
            bullets.append(f"Among the **10% of transactions it rated riskiest, {top_rate:.0%} were fraud** — about "
                           f"{top_rate / base_rate:.0f}× the overall rate of {base_rate:.1%}. Most high-scoring "
                           f"alerts are still legitimate, so every alert needs an analyst's review.")
        if ea.get("weak_segments"):
            bullets.append("It is **weaker for** " + ", ".join(w.replace("_", " ").replace("=", ": ")
                                                              for w in ea["weak_segments"])
                           + " — treat its ranking there with extra caution.")
        worst = ea.get("worst_days_capture_at_50") or {}
        if worst:
            wd, wv = min(worst.items(), key=lambda kv: kv[1])
            bullets.append(f"Results vary by day: on the worst test day (day {wd}) the top 50 alerts caught only "
                           f"{wv:.0%} of that day's fraud dollars, so judge the policy over many days, not one.")
        bullets.append("Results come from public IEEE-CIS data with generated customer identities: they show "
                       "performance in this simulated setting, not proven performance at a real bank.")
        st.markdown("\n".join(f"- {x}" for x in bullets))

    st.markdown(
        "**KPI 1 — Fraud value captured at capacity:** the share of a day's fraud dollars that falls inside the "
        "alerts the team actually reviews. It measures how much loss the review effort can prevent with the same "
        "staff, and links directly to the bank's fraud losses.")
    with st.expander("Model card: predictors, their roles, algorithm and evaluation design"):
        extended = fm.get("feature_set") == "week11_extended"
        st.markdown(
            "- **Predicts:** the probability that a transaction is fraudulent, at the moment it happens.\n"
            "- **Algorithm:** logistic regression on standardized predictors — probabilities that can be checked "
            "for calibration (needed for expected exposure = probability × amount) and exact explanations for "
            "every prediction.\n"
            f"- **Evaluation design:** {m['split'].get('design', 'chronological split')}. All modeling choices were "
            f"made on the validation period; the final test ({m['split']['test_rows']:,} transactions) was run "
            f"once.\n"
            "- **Uncertainty:** 30 bootstrap refits give a 90% range for each prediction.")
        roles = pd.DataFrame([
            ["Transaction amount, transactions in prior 24h, hours since previous", "Scenario input",
             "Describe the case; editable in what-if"],
            ["New-customer flag, customer's 30-day average, prior transaction count, amount z-score",
             "Fixed characteristic", "Fixed for a given customer; editable only to test sensitivity"],
            ["IEEE-CIS counts C1–C14, time deltas D1/D15, product code, credit vs. debit"
             + (", D10–D14, purchaser email, card network" if extended else ""), "Fixed (recorded)",
             "Held at recorded values"],
            ["Queue policy, review capacity", "Decision lever", "Set by the Lead in the settings toolbar"],
        ], columns=["Variables", "Role", "How the app treats them"])
        st.dataframe(roles, hide_index=True, width="stretch")

    st.subheader("KPI 1 on the final test days")
    cap_chart = (alt.Chart(cap).mark_line(point=True)
                 .encode(x=alt.X("capacity:O", title="Review capacity (alerts per day)",
                                 axis=alt.Axis(labelAngle=0)),
                         y=alt.Y("fraud_value_captured:Q", title="Fraud value captured", axis=alt.Axis(format="%")),
                         color=alt.Color("policy:N", title="Policy",
                                         legend=alt.Legend(orient="right", labelLimit=320)),
                         tooltip=["policy", "capacity", alt.Tooltip("fraud_value_captured:Q", format=".1%")])
                 .properties(height=340))
    st.altair_chart(cap_chart, width="stretch")
    pivot = cap.pivot(index="policy", columns="capacity", values="fraud_value_captured")
    st.dataframe(pivot.style.format("{:.1%}"), width="stretch")

    p_left, p_right = st.columns(2)
    with p_left:
        st.subheader("Model vs. baselines")
        comp = pd.DataFrame(m["comparison"]).T.rename(columns={"pr_auc": "PR-AUC", "roc_auc": "ROC-AUC",
                                                               "brier": "Brier score"})
        st.dataframe(comp.style.format("{:.3f}", na_rep="—"), width="stretch")
        st.caption(f"PR-AUC of a random ranking equals the test fraud rate ({base_rate:.3f}). "
                   "Lower Brier score means better-calibrated probabilities.")
    with p_right:
        st.subheader("Calibration")
        lim = float(max(cal["mean_predicted"].max(), cal["observed_rate"].max())) * 1.05
        diag = alt.Chart(pd.DataFrame({"x": [0, lim], "y": [0, lim]})).mark_line(strokeDash=[4, 4], color="gray") \
            .encode(x="x:Q", y="y:Q")
        pts = alt.Chart(cal).mark_line(point=True).encode(
            x=alt.X("mean_predicted:Q", title="Average predicted probability", axis=alt.Axis(format="%")),
            y=alt.Y("observed_rate:Q", title="Observed fraud rate", axis=alt.Axis(format="%")),
            tooltip=[alt.Tooltip("mean_predicted:Q", format=".1%"), alt.Tooltip("observed_rate:Q", format=".1%"),
                     "n"])
        st.altair_chart((diag + pts).properties(height=260), width="stretch")
        st.caption("Each point is one tenth of test transactions. Points near the dashed line mean the "
                   "probabilities can be read at face value.")

    if ea.get("segments"):
        st.subheader("Where the model is weaker (final test)")
        seg = pd.DataFrame(ea["segments"]).rename(columns={
            "segment": "Segment", "level": "Group", "transactions": "Transactions", "fraud_rate": "Fraud rate",
            "avg_predicted": "Avg predicted", "pr_auc": "PR-AUC",
            "fraud_caught_in_top5pct": "Fraud cases in top 5%", "fraud_dollars_caught_in_top5pct":
                "Fraud $ in top 5%"})
        st.dataframe(seg.style.format({"Fraud rate": "{:.1%}", "Avg predicted": "{:.1%}", "PR-AUC": "{:.3f}",
                                       "Fraud cases in top 5%": "{:.0%}", "Fraud $ in top 5%": "{:.0%}"},
                                      na_rep="—"), hide_index=True, width="stretch")
        st.caption(f"Overall, {ea['overall_fraud_caught_in_top5pct']:.0%} of fraud cases fall in the model's top 5% "
                   f"of probabilities. Groups well below that, or where the average prediction differs from the "
                   f"actual fraud rate, are where users should rely less on the ranking.")

    st.subheader("Overall predictor importance (all test transactions)")
    imp = pd.DataFrame(m["global_importance"]).head(15)
    signed = imp["mean_abs_contribution"] * np.sign(imp["coef_per_sd"])
    st.altair_chart(contribution_chart(imp["label"].tolist(), signed.to_numpy(),
                                       "Average size of contribution (log-odds), signed by direction"),
                    width="stretch")
    st.markdown(
        f"**Reading it.** Bar length is how much a predictor moves predictions on average across all test "
        f"transactions; colour shows whether higher values go with higher or lower fraud probability. "
        f"**{imp.iloc[0]['label']}** matters most overall. This is the overall view; the contributions behind a "
        f"single alert are on the Alert investigation page.")
    st.caption(NOT_CAUSAL + " C1–C14 are anonymized and correlated, so opposite signs on related counts partly "
                            "offset each other and should be read together.")

    if ev:
        fe = ev["fraud"]
        with st.expander("Week 11 evaluation details: leakage checks, improvement attempt and selection"):
            st.markdown("**Data-leakage checks**")
            st.dataframe(pd.DataFrame(fe["leakage_checks"]).assign(
                result=lambda d: np.where(d["result"], "Pass", "Flag")), hide_index=True, width="stretch")
            st.markdown("Known caveats: " + " ".join(fe["leakage_caveats"]))
            st.markdown("**Improvement attempt (decided on the validation period)**")
            st.dataframe(pd.DataFrame(fe["development"]).drop(columns=["feature_set"]).style.format(
                {"pr_auc": "{:.3f}", "roc_auc": "{:.3f}", "brier": "{:.4f}", "captured_at_50": "{:.1%}"},
                na_rep="—"), hide_index=True, width="stretch")
            st.markdown(f"**Decision.** {fe['selection']['decision']}")
            st.markdown("**Final test (run once, after the decision)**")
            st.dataframe(pd.DataFrame(fe["final_test"]).style.format(
                {"pr_auc": "{:.3f}", "roc_auc": "{:.3f}", "brier": "{:.4f}", "captured_at_50": "{:.1%}"},
                na_rep="—"), hide_index=True, width="stretch")

# ============================================================
# 11. PAGE — ALERT VOLUME FORECAST (KPI 2)
# ============================================================
else:
    ev = load_evaluation()
    page_header("Predictive model · KPI 2", "Alert volume forecast",
                "Tomorrow's alert load with a 90% range, the chance of overflow, and staffing scenarios.",
                [("Poisson regression", ""), (f"Capacity {capacity}", "neutral")])
    if not vm:
        st.info("Run `python3 src/modeling/evaluate_week11.py` to build the model.")
        st.stop()
    m = vm["metrics"]
    uses_lags = vm.get("feature_set") == "week11_lags"
    history = {int(k): float(v) for k, v in vm["history"].items()}
    vranges = vm.get("ranges") or volume_ranges_from_history(history)
    ea = m.get("error_analysis", {})
    busy = next((r for r in ea.get("segments", []) if r["level"] == "busy days"), None)
    busy_bias = busy["bias_actual_minus_forecast"] if busy else None
    sel = m["comparison"]["Poisson regression (selected)"]
    best_base = min((v["mae"] for k, v in m["comparison"].items() if k.startswith("Baseline")), default=None)
    with st.container(border=True):
        st.markdown("#### How much to trust this forecast")
        bullets = [f"On test days it was off by about **{sel['mae']:.0f} alerts** on average "
                   f"({sel['mape']:.0%})" + (f", compared with {best_base:.0f} for the best simple baseline."
                                              if best_base else "."),
                   f"Its **90% range contained the actual count on {m['interval_coverage_test']:.0%} of test days** — "
                   f"plan around the range, not the single number."]
        if busy_bias and busy_bias > 1:
            bullets.append(f"On the **busiest days it under-forecast by about {busy_bias:.0f} alerts**, so when "
                           f"capacity is tight use the upper end of the range.")
        bullets.append("It assumes the alerting rules and transaction mix stay as they were. After a rule change "
                       "or an unusual event, forecasts should not be relied on until the model is refit.")
        st.markdown("\n".join(f"- {x}" for x in bullets))

    st.markdown(
        "**KPI 2 — Daily alert overflow:** the number of alerts beyond the team's review capacity on a day. "
        "Forecasting it the evening before lets the Lead adjust staffing or deferral rules before the queue "
        "builds up.")
    with st.expander("Model card: predictors, their roles, algorithm and evaluation design"):
        st.markdown(
            "- **Predicts:** how many alerts the rules will create tomorrow.\n"
            "- **Algorithm:** Poisson regression with a negative-binomial 90% range "
            f"(variance ≈ {m['dispersion_phi']:.1f} × mean).\n"
            f"- **Evaluation design:** {m['split'].get('design', 'chronological split')}; final test on days "
            f"{m['split']['test_days'][0]}–{m['split']['test_days'][1]}, run once.")
        st.dataframe(pd.DataFrame([
            ["Review capacity", "Decision lever", "Set by the Lead; changes overflow, not the forecast"],
            ["Alerts yesterday, 7-day average" + (", alerts two days ago, same weekday last week" if uses_lags else ""),
             "External condition", "Scenario assumptions in what-if"],
            ["Day number and weekday", "Fixed", "Calendar; not editable"],
        ], columns=["Variables", "Role", "How the app treats them"]), hide_index=True, width="stretch")

    tp = pd.DataFrame(m["test_predictions"])
    band = alt.Chart(tp).mark_area(opacity=0.25).encode(
        x=alt.X("day:Q", title="Simulated day"), y=alt.Y("lower:Q", title="Alerts"), y2="upper:Q")
    long = tp.melt(id_vars="day", value_vars=["actual", "predicted"], var_name="Series", value_name="alerts")
    long["Series"] = long["Series"].map({"actual": "Actual alerts", "predicted": "Forecast"})
    lines = alt.Chart(long).mark_line(point=True).encode(
        x="day:Q", y="alerts:Q", color=alt.Color("Series:N", legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["day", "Series", alt.Tooltip("alerts:Q", format=".0f")])
    cap_rule = alt.Chart(pd.DataFrame({"y": [capacity]})).mark_rule(strokeDash=[6, 4], color="#C0392B") \
        .encode(y="y:Q")
    st.subheader("Forecast vs. actual on the final test days")
    st.altair_chart((band + lines + cap_rule).properties(height=300), width="stretch")
    st.caption(f"Shaded band: 90% prediction range. Red dashed line: your capacity of {capacity}.")

    a_left, a_right = st.columns(2)
    with a_left:
        st.subheader("Model vs. baselines")
        comp = pd.DataFrame(m["comparison"]).T.rename(columns={"mae": "Avg error (alerts)", "mape": "Avg % error"})
        st.dataframe(comp.style.format({"Avg error (alerts)": "{:.1f}", "Avg % error": "{:.1%}"}),
                     width="stretch")
    with a_right:
        st.subheader("KPI 2 on test days")
        ov = pd.DataFrame(m["overflow_kpi"]).rename(columns={
            "capacity": "Capacity", "actual_overflow_days": "Actual overflow days",
            "predicted_overflow_days_p_over_50pct": "Predicted overflow days",
            "overflow_day_accuracy": "Overflow-day accuracy", "missed_overflow_days": "Missed overflow days",
            "false_alarm_days": "False alarms", "avg_actual_overflow_alerts": "Avg actual overflow",
            "avg_predicted_overflow_alerts": "Avg predicted overflow"})
        st.dataframe(ov.style.format({"Overflow-day accuracy": "{:.0%}", "Avg actual overflow": "{:.1f}",
                                      "Avg predicted overflow": "{:.1f}"}), hide_index=True, width="stretch")
    if ea.get("segments"):
        st.subheader("Where the forecast is weaker (final test)")
        st.dataframe(pd.DataFrame(ea["segments"]).rename(columns={
            "segment": "Segment", "level": "Group", "days": "Days", "avg_alerts": "Avg alerts", "mae": "Avg error",
            "bias_actual_minus_forecast": "Actual − forecast", "coverage_90": "Inside 90% range"}).style.format(
            {"Avg alerts": "{:.0f}", "Avg error": "{:.1f}", "Actual − forecast": "{:+.1f}",
             "Inside 90% range": "{:.0%}"}), hide_index=True, width="stretch")
        st.caption("Positive 'Actual − forecast' means the model under-forecast that group of days.")

    st.subheader("Overall predictor importance (all test days)")
    imp = pd.DataFrame(m["global_importance"])
    signed = imp["mean_abs_contribution"] * np.sign(imp["coef"])
    st.altair_chart(contribution_chart(imp["label"].tolist(), signed.to_numpy(),
                                       "Average size of contribution (log scale), signed by direction"),
                    width="stretch")
    st.caption("Overall importance across test days; the forecast below shows contributions for one day. "
               + NOT_CAUSAL)

    if ev:
        ve = ev["volume"]
        with st.expander("Week 11 evaluation details: leakage checks, improvement attempt and selection"):
            st.dataframe(pd.DataFrame(ve["leakage_checks"]).assign(
                result=lambda d: np.where(d["result"], "Pass", "Flag")), hide_index=True, width="stretch")
            st.markdown("Known caveats: " + " ".join(ve["leakage_caveats"]))
            st.dataframe(pd.DataFrame(ve["development"]).drop(columns=["feature_set"]).style.format(
                {"mae": "{:.1f}", "mape": "{:.1%}", "coverage_90": "{:.0%}"}, na_rep="—"),
                hide_index=True, width="stretch")
            st.markdown(f"**Decision.** {ve['selection']['decision']}")
            st.dataframe(pd.DataFrame(ve["final_test"]).style.format(
                {"mae": "{:.1f}", "mape": "{:.1%}", "coverage_90": "{:.0%}"}, na_rep="—"),
                hide_index=True, width="stretch")

    st.divider()
    st.subheader("Forecast a day and compare a staffing scenario")
    last = max(history)
    fday = st.selectbox("Forecast for", list(range(min(history) + 7, last + 2))[::-1],
                        format_func=lambda d: f"Day {d}" + (" (next day after the data)" if d > last else ""))
    inp0 = volume_lags(history, fday)
    base = volume_forecast(vm, inp0, fday, capacity)
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Baseline forecast", f"{base['mu']:.0f} alerts")
    b2.metric("90% range", f"{base['lo']:.0f} – {base['hi']:.0f}")
    b3.metric(f"Chance of exceeding {capacity}", pct(base["p_over"]))
    b4.metric("Expected overflow", f"{base['exp_over']:.0f} alerts")
    if fday in history:
        st.caption(f"Actual alerts on Day {fday}: {history[fday]:.0f}.")
    vlabels = [vm["labels"][f] for f in vm["features"]]
    nz = [i for i in range(len(vlabels)) if abs(base["contrib"][i]) > 1e-6]
    effects = (np.exp(base["contrib"][nz]) - 1) * 100
    st.altair_chart(contribution_chart([vlabels[i] for i in nz], effects,
                                       "Effect on this forecast vs. an average day (%)"),
                    width="stretch")
    st.caption("Contributions to this one forecast (local). Each bar is the percentage by which a predictor "
               "raises or lowers the forecast relative to an average training day; effects multiply.")

    with st.form("volume_whatif"):
        st.markdown("**① Decision lever** · *you control this*")
        cap_s = st.number_input("Review capacity (alerts the team can review)", min_value=1,
                                value=int(capacity), step=5)
        st.markdown("**② External conditions** · *scenario assumptions — the Lead cannot set these*")
        v1, v2, v3, v4 = st.columns(4)
        lag1_s = v1.number_input("Alerts yesterday", min_value=0, value=int(round(inp0["lag1"])), step=5)
        lag7_s = v2.number_input("Average alerts, previous 7 days", min_value=0.0,
                                 value=round(float(inp0["lag7_mean"]), 1), step=5.0)
        lag2_s = v3.number_input("Alerts two days ago", min_value=0, value=int(round(inp0["lag2"])), step=5,
                                 disabled=not uses_lags, help=None if uses_lags else "Not used by the current model.")
        lag7d_s = v4.number_input("Alerts same weekday last week", min_value=0, value=int(round(inp0["lag7"])),
                                  step=5, disabled=not uses_lags,
                                  help=None if uses_lags else "Not used by the current model.")
        st.caption(f"③ Fixed: the calendar day (Day {fday}, simulated weekday {fday % 7}) and the trend.")
        run_v = st.form_submit_button("Run scenario", type="primary")
    if run_v:
        if abs(lag7_s - inp0["lag7_mean"]) < 0.05:  # the field shows one decimal; treat as unchanged
            lag7_s = inp0["lag7_mean"]
        inp1 = {"lag1": float(lag1_s), "lag7_mean": float(lag7_s),
                "lag2": float(lag2_s) if uses_lags else inp0["lag2"],
                "lag7": float(lag7d_s) if uses_lags else inp0["lag7"]}
        errors, warnings = check_volume_inputs(inp1, int(cap_s), vranges, uses_lags, inp0)
        if errors:
            st.session_state["volume_whatif_result"] = {"day": fday, "errors": errors}
        else:
            new = volume_forecast(vm, inp1, fday, int(cap_s))
            base_c = volume_forecast(vm, inp0, fday, capacity)
            base_c["exp_over_newcap_base"] = volume_forecast(vm, inp1, fday, capacity)["exp_over"]
            items = [("Review capacity", "decision lever", capacity, int(cap_s), "{:,.0f}"),
                     ("Alerts yesterday", "external condition", inp0["lag1"], inp1["lag1"], "{:,.0f}"),
                     ("Average alerts, previous 7 days", "external condition", inp0["lag7_mean"], inp1["lag7_mean"],
                      "{:,.1f}")]
            if uses_lags:
                items += [("Alerts two days ago", "external condition", inp0["lag2"], inp1["lag2"], "{:,.0f}"),
                          ("Alerts same weekday last week", "external condition", inp0["lag7"], inp1["lag7"],
                           "{:,.0f}")]
            table = [{"Item": n, "Role": r, "Baseline": f_.format(a0), "Scenario": f_.format(a1),
                      "Difference": "—" if a0 == a1 else f"{a1 - a0:+,.1f}"} for n, r, a0, a1, f_ in items]
            changes = [(n, f_.format(a0), f_.format(a1)) for n, r, a0, a1, f_ in items if a0 != a1]
            table += [
                {"Item": "Forecast alerts", "Role": "prediction", "Baseline": f"{base_c['mu']:.0f}",
                 "Scenario": f"{new['mu']:.0f}", "Difference": f"{new['mu'] - base_c['mu']:+.0f}"},
                {"Item": "90% range", "Role": "prediction", "Baseline": f"{base_c['lo']:.0f}–{base_c['hi']:.0f}",
                 "Scenario": f"{new['lo']:.0f}–{new['hi']:.0f}", "Difference": "—"},
                {"Item": "Chance of overflow", "Role": "KPI 2", "Baseline": pct(base_c["p_over"]),
                 "Scenario": pct(new["p_over"]), "Difference": f"{(new['p_over'] - base_c['p_over']) * 100:+.1f} pts"},
                {"Item": "Expected alerts beyond capacity", "Role": "KPI 2", "Baseline": f"{base_c['exp_over']:.0f}",
                 "Scenario": f"{new['exp_over']:.0f}", "Difference": f"{new['exp_over'] - base_c['exp_over']:+.0f}"},
            ]
            st.session_state["volume_whatif_result"] = {
                "day": fday, "errors": None, "warnings": warnings, "table": table, "new": new, "base": base_c,
                "summary": volume_summary(changes, base_c, new, capacity, int(cap_s), m, warnings, busy_bias)}
            st.session_state.setdefault("volume_whatif_log", []).append({
                "Day": fday, "Changes": "; ".join(f"{k} {a}→{c}" for k, a, c in changes) or "none",
                "Baseline": round(base_c["mu"]), "Scenario": round(new["mu"]),
                "Overflow chance": pct(new["p_over"])})
    res = st.session_state.get("volume_whatif_result")
    if res and res["day"] == fday:
        if res.get("errors"):
            st.error("**Scenario not run — the inputs are inconsistent:**\n\n"
                     + "\n".join(f"- {e}" for e in res["errors"]))
        else:
            k1, k2, k3 = st.columns(3)
            k1.metric("Baseline forecast", f"{res['base']['mu']:.0f} alerts")
            k2.metric("Scenario forecast", f"{res['new']['mu']:.0f} alerts",
                      delta=f"{res['new']['mu'] - res['base']['mu']:+.0f}", delta_color="inverse")
            k3.metric("Scenario chance of overflow", pct(res["new"]["p_over"]),
                      delta=f"{(res['new']['p_over'] - res['base']['p_over']) * 100:+.1f} pts", delta_color="inverse")
            if res["warnings"]:
                st.warning("**Plausibility warnings:**\n\n" + "\n".join(f"- {w}" for w in res["warnings"]))
            st.markdown("#### Baseline vs. scenario")
            st.dataframe(pd.DataFrame(res["table"]), hide_index=True, width="stretch",
                         height=35 * (len(res["table"]) + 1) + 3)
            st.markdown("#### Scenario summary")
            st.info(res["summary"].replace("$", "\\$"))
    if st.session_state.get("volume_whatif_log"):
        with st.expander("Scenarios run in this session"):
            st.dataframe(pd.DataFrame(st.session_state["volume_whatif_log"]), hide_index=True,
                         width="stretch")

# ============================================================
# 12. FOOTER
# ============================================================
st.markdown(
    '<div class="site-footer"><div><b>FraudOps · Decision Intelligence</b> — prototype decision-support tool for a '
    'Fraud Operations Lead.</div><div>Data: IEEE-CIS transactions with generated customer, account and device '
    'identities · Results are model-based, not guarantees.</div></div>', unsafe_allow_html=True)
