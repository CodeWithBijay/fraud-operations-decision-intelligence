"""Fraud Operations Decision Intelligence — Week 10 application.

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
Models (folder models/, built by src/modeling/train_*.py)
    fraud_model.joblib, alert_volume_model.joblib

Run:  streamlit run app/app.py
"""
import html
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
from common import (FRAUD_FEATURES, MODEL_DIR, fraud_design, linear_contributions,  # noqa: E402
                    sigmoid, volume_design)

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
SOURCE_COLS = ["product_cd", "card6"] + [f"c{i}" for i in range(1, 15)] + ["d1", "d15"]
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
    src = ", ".join(f"t.{c}" + ("::float8" if c not in ("product_cd", "card6") else "") + f" AS {c}"
                    for c in SOURCE_COLS)
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
    X, _ = fraud_design(df, fm["fill"])
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


def volume_forecast(vm, lag1, lag7_mean, day, capacity):
    X = volume_design([lag1], [lag7_mean], [day])
    base, contrib = linear_contributions(X, vm["coef"], vm["intercept"], vm["train_mean"])
    mu = float(np.exp(vm["intercept"] + X[0] @ vm["coef"]))
    dist = count_dist(mu, vm["phi"])
    q = (1 - vm["interval"]) / 2
    k = np.arange(capacity + 1, int(dist.ppf(0.9999)) + 2)
    return {"mu": mu, "lo": float(dist.ppf(q)), "hi": float(dist.ppf(1 - q)),
            "p_over": float(1 - dist.cdf(capacity)),
            "exp_over": float(np.sum((k - capacity) * dist.pmf(k))),
            "base": base, "contrib": contrib[0]}


def volume_inputs(history, day):
    """Inputs known the evening before `day`: yesterday's count and the previous 7-day average."""
    prev = [history.get(d, np.nan) for d in range(day - 7, day)]
    return float(history.get(day - 1, np.nan)), float(np.nanmean(prev))


def contribution_chart(labels, values, value_title):
    df = pd.DataFrame({"Predictor": labels, "Contribution": values})
    df["Direction"] = np.where(df["Contribution"] >= 0, "Raises prediction", "Lowers prediction")
    return (alt.Chart(df).mark_bar()
            .encode(x=alt.X("Contribution:Q", title=value_title),
                    y=alt.Y("Predictor:N", sort=alt.EncodingSortField("Contribution", op="sum", order="descending"),
                            title=None),
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
def fraud_summary(changes, base_p, new_p, new_lo, new_hi, top_moves, queue_pos, n_alerts, capacity, metrics):
    if not changes:
        lead = "No inputs were changed, so the scenario equals the baseline."
    else:
        lead = "Scenario inputs: " + "; ".join(f"{k} {a} → {b}" for k, a, b in changes) + "."
    diff = (new_p - base_p) * 100
    direction = "unchanged" if abs(diff) < 0.05 else ("higher" if diff > 0 else "lower")
    lines = [
        f"**Inputs.** {lead} Source attributes (IEEE-CIS counts, time deltas, product code, card type) "
        f"were held at their recorded values.",
        f"**Updated prediction.** Fraud probability {pct(new_p)} (90% model range {pct(new_lo)}–{pct(new_hi)}).",
        f"**Change from baseline.** {pct(base_p)} → {pct(new_p)}, {abs(diff):.1f} percentage points {direction}."
        + (f" Largest drivers of the change: {top_moves}." if top_moves else ""),
        f"**Implication.** Under the expected-exposure policy this scenario would rank #{queue_pos} of "
        f"{n_alerts} of today's alerts — "
        + ("inside" if queue_pos <= capacity else "outside") + f" today's review capacity of {capacity}.",
        f"**Limitations.** This is a model-based scenario: it shows how the model's estimate responds, not what "
        f"would happen if the customer behaved differently, and not proof of cause. On later test days the model "
        f"reached PR-AUC {metrics['comparison']['Logistic regression (selected)']['pr_auc']:.2f}, so many "
        f"high-probability alerts are still legitimate. The range reflects uncertainty in the model's "
        f"coefficients only. Data are IEEE-CIS transactions with generated customer identities.",
    ]
    return "\n\n".join(lines)


def volume_summary(changes, base, new, capacity, metrics):
    lead = ("No inputs were changed, so the scenario equals the baseline." if not changes else
            "Scenario inputs: " + "; ".join(f"{k} {a} → {b}" for k, a, b in changes) + ".")
    diff = new["mu"] - base["mu"]
    lines = [
        f"**Inputs.** {lead}",
        f"**Updated forecast.** About {new['mu']:.0f} alerts (90% range {new['lo']:.0f}–{new['hi']:.0f}); "
        f"{pct(new['p_over'])} chance of exceeding a capacity of {capacity}.",
        f"**Change from baseline.** {base['mu']:.0f} → {new['mu']:.0f} alerts ({diff:+.0f}); chance of overflow "
        f"{pct(base['p_over'])} → {pct(new['p_over'])}; expected alerts beyond capacity "
        f"{base['exp_over']:.0f} → {new['exp_over']:.0f}.",
        "**Implication.** "
        + ("Overflow is more likely than not: consider adding review capacity or deferring low-exposure alerts."
           if new["p_over"] > 0.5 else
           "Capacity is likely sufficient; the remaining risk is a busy day in the upper part of the range."),
        f"**Limitations.** A model-based scenario, not a guarantee. The forecast assumes the alerting rules and "
        f"transaction mix stay as they were on training days. Its 90% range contained the actual count on "
        f"{metrics['interval_coverage_test']:.0%} of test days. Changing yesterday's count shows how the model "
        f"responds; it does not cause tomorrow's volume.",
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
            st.info("Train the fraud model (src/modeling/train_fraud_model.py) to see explanations.")
        else:
            one = queue[queue.transaction_id == choice]
            s1 = fraud_scores(one, fm)
            contrib = s1["contrib"][0]
            base_p = float(sigmoid(s1["base"]))
            st.subheader("Why the model gave this probability")
            st.markdown(f"An average transaction in the training data scores **{pct(base_p)}**. "
                        f"Each bar shows how much one predictor moved **this transaction** from that "
                        f"average, on the log-odds scale. The bars add up to **{pct(row['fraud_prob'])}**.")
            labels = [fm["labels"][f] for f in FRAUD_FEATURES]
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
            st.caption("This chart explains one prediction (local). Overall importance across all transactions "
                       "is on the Fraud risk model page. " + NOT_CAUSAL
                       + " IEEE count variables C1–C14 are anonymized by the data provider and strongly "
                         "correlated with each other, so read them as a group rather than one at a time.")

    with tab_whatif:
        if not fm:
            st.info("Train the fraud model to enable what-if analysis.")
        else:
            one = queue[queue.transaction_id == choice].iloc[[0]].copy()
            st.subheader("What if this transaction looked different?")
            st.caption("Change the behavioral inputs and run the scenario. The baseline is the transaction as "
                       "recorded. IEEE-CIS source attributes stay at their recorded values.")
            cold = bool(one["cold_start_flag"].iloc[0])
            std = one["customer_std_amt_30d"].iloc[0]
            with st.form("fraud_whatif"):
                w1, w2, w3 = st.columns(3)
                amt = w1.number_input("Amount ($)", min_value=0.0, value=float(one["transaction_amt"].iloc[0]),
                                      step=10.0)
                cnt = w2.number_input("Transactions in prior 24h", min_value=0,
                                      value=int(one["txn_count_24h"].iloc[0]), step=1)
                new_cust = w3.checkbox("New customer (no history)", value=cold)
                w4, w5, w6 = st.columns(3)
                hrs0 = one["hours_since_previous_txn"].iloc[0]
                avg0 = one["customer_avg_amt_30d"].iloc[0]
                hrs = w4.number_input("Hours since previous transaction", min_value=0.0,
                                      value=0.0 if pd.isna(hrs0) else float(hrs0), step=1.0)
                avg = w5.number_input("Customer avg amount, 30 days ($)", min_value=0.0,
                                      value=0.0 if pd.isna(avg0) else float(avg0), step=10.0)
                prior = w6.number_input("Customer's prior transaction count", min_value=0,
                                        value=int(one["prior_txn_count"].iloc[0]), step=1)
                st.caption("When 'New customer' is ticked, the history inputs are ignored.")
                run = st.form_submit_button("Run scenario", type="primary")

            if run:
                scen = one.copy()
                scen["transaction_amt"] = amt
                scen["txn_count_24h"] = 0 if new_cust else cnt
                if new_cust:
                    scen[["hours_since_previous_txn", "customer_avg_amt_30d",
                          "customer_amount_zscore"]] = np.nan
                    scen["prior_txn_count"], scen["cold_start_flag"] = 0, True
                else:
                    scen["hours_since_previous_txn"] = hrs if (hrs > 0 or not pd.isna(hrs0)) else np.nan
                    scen["customer_avg_amt_30d"] = avg if (avg > 0 or not pd.isna(avg0)) else np.nan
                    scen["prior_txn_count"] = max(prior, 1)
                    scen["cold_start_flag"] = False
                    scen["customer_amount_zscore"] = ((amt - avg) / std
                                                      if pd.notna(std) and std > 0 else np.nan)
                b, s = fraud_scores(one, fm), fraud_scores(scen, fm)
                names = {"transaction_amt": ("Amount", "${:,.2f}"),
                         "txn_count_24h": ("Transactions in prior 24h", "{:.0f}"),
                         "hours_since_previous_txn": ("Hours since previous", "{:.1f}"),
                         "customer_avg_amt_30d": ("Customer avg amount", "${:,.2f}"),
                         "prior_txn_count": ("Prior transaction count", "{:.0f}"),
                         "cold_start_flag": ("New customer", "{}")}
                changes = []
                for col, (nm, f_) in names.items():
                    a0, a1 = one[col].iloc[0], scen[col].iloc[0]
                    if (pd.isna(a0) and pd.isna(a1)) or (not pd.isna(a0) and not pd.isna(a1) and a0 == a1):
                        continue
                    show = lambda v: "none" if pd.isna(v) else f_.format(bool(v) if col == "cold_start_flag" else v)
                    changes.append((nm, show(a0), show(a1)))
                delta = s["contrib"][0] - b["contrib"][0]
                labels = [fm["labels"][f] for f in FRAUD_FEATURES]
                moves = [f"{labels[i]} ({'+' if delta[i] > 0 else '−'})"
                         for i in np.argsort(-np.abs(delta))[:3] if abs(delta[i]) > 0.01]
                new_exp = float(s["p"][0]) * amt
                others = queue[queue.transaction_id != choice]["exposure"]
                queue_pos = int((others > new_exp).sum()) + 1
                res = {"base": float(b["p"][0]), "p": float(s["p"][0]), "lo": float(s["lo"][0]),
                       "hi": float(s["hi"][0]),
                       "summary": fraud_summary(changes, float(b["p"][0]), float(s["p"][0]), float(s["lo"][0]),
                                                float(s["hi"][0]), ", ".join(moves), queue_pos, len(queue),
                                                capacity, fm["metrics"]),
                       "txn": choice, "changes": changes}
                st.session_state["fraud_whatif_result"] = res
                st.session_state.setdefault("fraud_whatif_log", []).append({
                    "Transaction": choice, "Changes": "; ".join(f"{k} {a}→{b2}" for k, a, b2 in changes) or "none",
                    "Baseline": pct(res["base"]), "Scenario": pct(res["p"]),
                    "Change (pts)": round((res["p"] - res["base"]) * 100, 1)})

            res = st.session_state.get("fraud_whatif_result")
            if res and res["txn"] == choice:
                k1, k2, k3 = st.columns(3)
                k1.metric("Baseline (as recorded)", pct(res["base"]))
                k2.metric("Scenario", pct(res["p"]), delta=f"{(res['p'] - res['base']) * 100:+.1f} pts",
                          delta_color="inverse")
                k3.metric("Scenario 90% model range", f"{pct(res['lo'])} – {pct(res['hi'])}")
                st.markdown("#### Scenario summary")
                st.info(res["summary"])
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
    page_header("Predictive model · KPI 1", "Fraud risk model",
                "How well the fraud model ranks risk on later days, and which predictors drive it overall.",
                [("Logistic regression", ""), ("Tested on later 30% of time", "neutral")])
    if not fm:
        st.info("Run `python3 src/modeling/train_fraud_model.py` to build the model.")
        st.stop()
    m = fm["metrics"]
    st.markdown(
        "**KPI 1 — Fraud value captured at capacity:** the share of a day's fraud dollars that falls inside the "
        "alerts the team actually reviews. The team can review only a limited number of alerts, so this KPI "
        "measures how much loss the review effort can prevent with the same staff. It links directly to "
        "operational performance and to the bank's fraud losses.")
    with st.expander("Model card: predictors, algorithm and evaluation"):
        st.markdown(
            "- **Predicts:** the probability that a transaction is fraudulent, at the moment it happens.\n"
            "- **Predictors:** 7 point-in-time behavioral features built in this project (amount, hours since "
            "previous transaction, transactions in prior 24h, customer's 30-day average, amount z-score, "
            "prior transaction count, new-customer flag) and IEEE-CIS source attributes recorded with the "
            "transaction (anonymized counts C1–C14, time deltas D1 and D15, product code, credit vs. debit). "
            "All are available before a review decision, so the model uses no future information.\n"
            "- **Algorithm:** logistic regression on standardized predictors. Chosen because it produces "
            "probabilities that can be checked for calibration (needed for expected exposure = probability × "
            "amount) and because every prediction can be explained exactly. Gradient boosting was trained as a "
            "comparison: it is more accurate, but its predictions cannot be explained as directly.\n"
            f"- **Evaluation:** trained on the earliest 70% of time ({m['split']['train_rows']:,} transactions), "
            f"tested on the latest 30% ({m['split']['test_rows']:,}).\n"
            "- **Uncertainty:** 30 bootstrap refits give a 90% range for each prediction.")

    st.subheader("KPI 1 on held-out test days")
    cap = pd.DataFrame(m["capture_at_capacity"])
    cap_chart = (alt.Chart(cap).mark_line(point=True)
                 .encode(x=alt.X("capacity:O", title="Review capacity (alerts per day)",
                                 axis=alt.Axis(labelAngle=0)),
                         y=alt.Y("fraud_value_captured:Q", title="Fraud value captured", axis=alt.Axis(format="%")),
                         color=alt.Color("policy:N", title="Policy",
                                         legend=alt.Legend(orient="right", labelLimit=320)),
                         tooltip=["policy", "capacity", alt.Tooltip("fraud_value_captured:Q", format=".1%")])
                 .properties(height=360))
    st.altair_chart(cap_chart, width="stretch")
    pivot = cap.pivot(index="policy", columns="capacity", values="fraud_value_captured")
    st.dataframe(pivot.style.format("{:.1%}"), width="stretch")
    st.caption("Average across test days of: fraud dollars in the top-K transactions ÷ all fraud dollars that "
               "day. 'Model A' uses behavioral features only, showing what the IEEE-CIS attributes add.")

    p_left, p_right = st.columns(2)
    with p_left:
        st.subheader("Predictive performance")
        comp = pd.DataFrame(m["comparison"]).T.rename(columns={"pr_auc": "PR-AUC", "roc_auc": "ROC-AUC",
                                                               "brier": "Brier score"})
        st.dataframe(comp.style.format("{:.3f}", na_rep="—"), width="stretch")
        st.caption(f"PR-AUC of a random ranking equals the test fraud rate ({m['split']['test_fraud_rate']:.3f}). "
                   "Lower Brier score means better-calibrated probabilities.")
    with p_right:
        st.subheader("Calibration")
        cal = pd.DataFrame(m["calibration"])
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

    st.subheader("Overall predictor importance (all test transactions)")
    imp = pd.DataFrame(m["global_importance"]).head(15)
    signed = imp["mean_abs_contribution"] * np.sign(imp["coef_per_sd"])
    st.altair_chart(contribution_chart(imp["label"].tolist(), signed.to_numpy(),
                                       "Average size of contribution (log-odds), signed by direction"),
                    width="stretch")
    top = imp.iloc[0]
    st.markdown(
        f"**Reading it.** Bar length is how much a predictor moves predictions on average; colour shows "
        f"whether higher values of it go with higher or lower fraud probability. **{top['label']}** matters "
        f"most overall. Odds ratios per one standard deviation are in the table below. Among the behavioral "
        f"features, a larger transaction amount raises the estimate, while a longer gap since the previous "
        f"transaction and a higher usual spend lower it.")
    st.dataframe(imp[["label", "mean_abs_contribution", "odds_ratio_per_sd"]].rename(columns={
        "label": "Predictor", "mean_abs_contribution": "Avg |contribution|",
        "odds_ratio_per_sd": "Odds ratio per 1 SD"}).style.format({"Avg |contribution|": "{:.3f}",
                                                                 "Odds ratio per 1 SD": "{:.2f}"}),
        hide_index=True, width="stretch")
    st.caption("Overall importance summarizes the whole test period; it is different from the contributions to "
               "a single alert shown on the Alert investigation page. " + NOT_CAUSAL
               + " C1–C14 are anonymized and correlated, so opposite signs on related counts (for example C1 "
                 "and C14) partly offset each other and should be read together.")

# ============================================================
# 11. PAGE — ALERT VOLUME FORECAST (KPI 2)
# ============================================================
else:
    page_header("Predictive model · KPI 2", "Alert volume forecast",
                "Tomorrow's alert load with a 90% range, the chance of overflow, and staffing scenarios.",
                [("Poisson regression", ""), (f"Capacity {capacity}", "neutral")])
    if not vm:
        st.info("Run `python3 src/modeling/train_alert_volume_model.py` to build the model.")
        st.stop()
    m = vm["metrics"]
    history = {int(k): float(v) for k, v in vm["history"].items()}
    st.markdown(
        "**KPI 2 — Daily alert overflow:** the number of alerts beyond the team's review capacity on a day. "
        "Overflow alerts may miss the 24-hour review deadline, so fraud can go unreviewed. Forecasting it the "
        "evening before lets the Lead adjust staffing or deferral rules before the queue builds up, which "
        "supports service levels and controls labour cost.")
    with st.expander("Model card: predictors, algorithm and evaluation"):
        st.markdown(
            "- **Predicts:** how many alerts the rules will create tomorrow.\n"
            "- **Predictors:** alerts yesterday, average alerts over the previous 7 days, simulated weekday and "
            "a trend term. All are known the evening before, so the forecast is usable for planning.\n"
            "- **Algorithm:** Poisson regression, a model for counts: predictions are never negative and its "
            "spread grows with the level. Daily counts vary more than a pure Poisson allows "
            f"(variance ≈ {m['dispersion_phi']:.1f} × mean), so the 90% range uses a negative binomial "
            "distribution with that measured spread.\n"
            f"- **Evaluation:** trained on days {m['split']['train_days'][0]}–{m['split']['train_days'][1]}, "
            f"tested one day ahead on days {m['split']['test_days'][0]}–{m['split']['test_days'][1]}.")

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
    st.subheader("Forecast vs. actual on held-out test days")
    st.altair_chart((band + lines + cap_rule).properties(height=320), width="stretch")
    st.caption(f"Shaded band: 90% prediction range. Red dashed line: your capacity of {capacity}. The range "
               f"contained the actual count on {m['interval_coverage_test']:.0%} of test days.")

    a_left, a_right = st.columns(2)
    with a_left:
        st.subheader("Forecast accuracy")
        comp = pd.DataFrame(m["comparison"]).T.rename(columns={"mae": "Avg error (alerts)", "mape": "Avg % error"})
        st.dataframe(comp.style.format({"Avg error (alerts)": "{:.1f}", "Avg % error": "{:.1%}"}),
                     width="stretch")
    with a_right:
        st.subheader("KPI 2 on test days")
        ov = pd.DataFrame(m["overflow_kpi"]).rename(columns={
            "capacity": "Capacity", "actual_overflow_days": "Actual overflow days",
            "predicted_overflow_days_p_over_50pct": "Predicted overflow days",
            "overflow_day_accuracy": "Overflow-day accuracy",
            "avg_actual_overflow_alerts": "Avg actual overflow", "avg_predicted_overflow_alerts":
                "Avg predicted overflow"})
        st.dataframe(ov.style.format({"Overflow-day accuracy": "{:.0%}", "Avg actual overflow": "{:.1f}",
                                      "Avg predicted overflow": "{:.1f}"}), hide_index=True,
                     width="stretch")

    st.subheader("Overall predictor importance (all test days)")
    imp = pd.DataFrame(m["global_importance"])
    signed = imp["mean_abs_contribution"] * np.sign(imp["coef"])
    st.altair_chart(contribution_chart(imp["label"].tolist(), signed.to_numpy(),
                                       "Average size of contribution (log scale), signed by direction"),
                    width="stretch")
    st.caption("Overall importance across test days; the forecast below shows contributions for one day. "
               + NOT_CAUSAL)

    st.divider()
    st.subheader("Forecast and what-if for a chosen day")
    last = max(history)
    fday = st.selectbox("Forecast for", list(range(min(history) + 7, last + 2))[::-1],
                        format_func=lambda d: f"Day {d}" + (" (next day after the data)" if d > last else ""))
    lag1_0, lag7_0 = volume_inputs(history, fday)
    base = volume_forecast(vm, lag1_0, lag7_0, fday, capacity)
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
        v1, v2, v3 = st.columns(3)
        lag1_s = v1.number_input("Alerts yesterday", min_value=0, value=int(round(lag1_0)), step=5)
        lag7_s = v2.number_input("Average alerts, previous 7 days", min_value=0.0, value=round(float(lag7_0), 1),
                                 step=5.0)
        cap_s = v3.number_input("Review capacity", min_value=1, value=int(capacity), step=5)
        run_v = st.form_submit_button("Run scenario", type="primary")
    if run_v:
        new = volume_forecast(vm, lag1_s, lag7_s, fday, int(cap_s))
        base_c = volume_forecast(vm, lag1_0, lag7_0, fday, int(cap_s))
        changes = [(k, a, b) for k, a, b in [
            ("Alerts yesterday", f"{lag1_0:.0f}", f"{lag1_s:.0f}"),
            ("7-day average", f"{lag7_0:.1f}", f"{lag7_s:.1f}"),
            ("Capacity", f"{capacity}", f"{int(cap_s)}")] if a != b]
        st.session_state["volume_whatif_result"] = {"day": fday, "new": new, "base": base_c,
                                             "summary": volume_summary(changes, base_c, new, int(cap_s), m)}
        st.session_state.setdefault("volume_whatif_log", []).append({
            "Day": fday, "Changes": "; ".join(f"{k} {a}→{b}" for k, a, b in changes) or "none",
            "Baseline": round(base_c["mu"]), "Scenario": round(new["mu"]),
            "Overflow chance": pct(new["p_over"])})
    res = st.session_state.get("volume_whatif_result")
    if res and res["day"] == fday:
        k1, k2, k3 = st.columns(3)
        k1.metric("Baseline forecast", f"{res['base']['mu']:.0f} alerts")
        k2.metric("Scenario forecast", f"{res['new']['mu']:.0f} alerts",
                  delta=f"{res['new']['mu'] - res['base']['mu']:+.0f}", delta_color="inverse")
        k3.metric("Scenario chance of overflow", pct(res["new"]["p_over"]),
                  delta=f"{(res['new']['p_over'] - res['base']['p_over']) * 100:+.1f} pts", delta_color="inverse")
        st.markdown("#### Scenario summary")
        st.info(res["summary"])
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
