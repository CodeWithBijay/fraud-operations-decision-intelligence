"""Fraud Operations Decision Intelligence — Week 9 prototype.

Decision-maker: Fraud Operations Lead.
Decision supported: which of today's fraud alerts the team reviews, given limited review capacity.

Screen 1 · Alert Queue
    Queue             ranked alerts, filters, click a row to open it
    Compare policies  P0 / P1 / P2 side by side at the chosen capacity
    Alert volume      alerts per day within capacity vs. overflow
    Trends & rules    volume trend, rule-trigger distribution, risk-score distribution, rule firings over time
    Team performance  decisions, alerts resolved, average handle time, per-analyst table
Screen 2 · Alert Detail
    why the transaction was alerted, the customer's prior behavior, record a decision, decision history

Data (PostgreSQL, database fraud_risk_db):
    transaction_features  built by sql/features/build_transaction_features.sql
    alert_queue           built by sql/alerts/build_alert_queue.sql
    alert_rule_config     built by sql/alerts/build_alert_queue.sql
    ops_decision_log      created by sql/ops/create_decision_log.sql (run automatically at start-up)

The fraud label (is_fraud) is never shown or used in this app.

Run:  streamlit run app/app.py
"""
import os

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Fraud Ops Decision Intelligence", layout="wide")

# ============================================================
# 1. SETTINGS
# ============================================================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

POLICIES = {
    "P2 · Rule risk score": "P2",
    "P1 · Largest amount first": "P1",
    "P0 · Random (baseline)": "P0",
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


# ============================================================
# 2. DATABASE
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
    return query(
        """
        SELECT transaction_id, customer_id, device_id, transaction_dt,
               transaction_amt::float8            AS transaction_amt,
               hours_since_previous_txn::float8   AS hours_since_previous_txn,
               txn_count_24h,
               customer_avg_amt_30d::float8       AS customer_avg_amt_30d,
               customer_amount_zscore::float8     AS customer_amount_zscore,
               risk_score, reasons,
               r1_velocity, r2_amount_spike, r3_rapid_repeat,
               r4_new_customer, r5_large_amount, r6_new_device
        FROM alert_queue
        WHERE sim_day = :day
        ORDER BY transaction_id
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
        SELECT sim_day,
               COUNT(*)                          AS alerts,
               AVG(risk_score)::float8           AS avg_score,
               SUM(transaction_amt)::float8      AS alert_amount,
               SUM(r1_velocity::int)     AS r1, SUM(r2_amount_spike::int) AS r2,
               SUM(r3_rapid_repeat::int) AS r3, SUM(r4_new_customer::int) AS r4,
               SUM(r5_large_amount::int) AS r5, SUM(r6_new_device::int)   AS r6
        FROM alert_queue GROUP BY sim_day ORDER BY sim_day
        """
    )


def score_distribution(day):
    return query(
        """
        SELECT risk_score,
               COUNT(*) FILTER (WHERE sim_day = :day) AS today,
               COUNT(*)                               AS all_days
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
    # Handle time: first ASSIGN_REVIEW -> first final disposition after it, per alert.
    handled = query_live(
        """
        WITH a AS (
            SELECT transaction_id, MIN(decided_at) AS assigned_at
            FROM ops_decision_log WHERE action = 'ASSIGN_REVIEW' GROUP BY transaction_id
        ),
        d AS (
            SELECT DISTINCT ON (l.transaction_id)
                   l.transaction_id, l.analyst_name, l.action, l.decided_at
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
# 4. DECISION LOGIC
# ============================================================
def sim_time(dt):
    """Format a TransactionDT offset (seconds) as simulated 'Day N HH:MM'."""
    dt = int(dt)
    return f"Day {dt // 86400}  {(dt % 86400) // 3600:02d}:{(dt % 3600) // 60:02d}"


def rank_queue(df, policy, day):
    """Order alerts by the chosen policy and number them 1..n."""
    df = df.copy()
    if policy == "P0":
        rng = np.random.default_rng(1000 + int(day))  # seeded: same day -> same order
        df["priority"] = rng.random(len(df))
    elif policy == "P1":
        df["priority"] = df["transaction_amt"]
    else:  # P2: risk score, ties broken by amount
        df["priority"] = df["risk_score"] + df["transaction_amt"] / (df["transaction_amt"].max() + 1)
    df = df.sort_values("priority", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    return df


def policy_comparison(raw, day, k):
    """What each policy would review at capacity k, plus coverage as capacity grows."""
    total = raw["transaction_amt"].sum()
    steps = sorted(set(np.linspace(1, len(raw), num=min(40, len(raw))).astype(int)))
    rows, curves = [], {}
    for label, code in POLICIES.items():
        ranked = rank_queue(raw, code, day)
        top = ranked.head(k)
        rows.append({
            "Policy": label,
            "Alerts reviewed": len(top),
            "Amount reviewed": top["transaction_amt"].sum(),
            "Share of alert amount": top["transaction_amt"].sum() / total,
            "Avg risk score": top["risk_score"].mean(),
            "High-score alerts (≥3) reviewed": int((top["risk_score"] >= 3).sum()),
        })
        cum = ranked["transaction_amt"].cumsum().to_numpy()
        curves[label] = [cum[s - 1] / total * 100 for s in steps]
    curve = pd.DataFrame(curves, index=steps)
    curve.index.name = "Capacity (alerts reviewed)"
    return pd.DataFrame(rows), curve


def go_to_detail(tid):
    st.session_state["screen"] = "2 · Alert Detail"
    st.session_state["detail_txn"] = int(tid)


def set_detail(tid):
    st.session_state["detail_txn"] = int(tid)


def fmt(value, pattern):
    return "n/a (no history)" if pd.isna(value) else pattern.format(value)


# ============================================================
# 5. SIDEBAR — decision settings
# ============================================================
st.sidebar.title("Fraud Ops Lead")
screen = st.sidebar.radio("Screen", ["1 · Alert Queue", "2 · Alert Detail"], key="screen")

days = load_days()
day = st.sidebar.selectbox(
    "Simulated day", days["sim_day"].tolist(),
    format_func=lambda d: f"Day {d}  ({int(days.loc[days.sim_day == d, 'n'].iloc[0])} alerts)",
)
policy_label = st.sidebar.selectbox("Queue policy", list(POLICIES.keys()))
policy = POLICIES[policy_label]
capacity = st.sidebar.slider(
    "Review capacity (alerts per day)", min_value=5, max_value=300, value=50, step=5,
    help="Assumption: how many alerts the analyst team can review today.",
)
st.sidebar.caption("Capacity and policy are what-if settings; change them to see how the queue responds.")

# Today's ranked queue with live status
raw = load_day(day)
queue = rank_queue(raw, policy, day)
queue["action"] = np.where(queue["rank"] <= capacity, "Review today", "Wait / expire")
queue = queue.merge(latest_status(day), on="transaction_id", how="left")
queue["status"] = queue["last_action"].map(ACTIONS).fillna("Open")

# ============================================================
# 6. SCREEN 1 — ALERT QUEUE
# ============================================================
if screen.startswith("1"):
    st.title("Alert Queue")
    st.caption(f"Day {day} · {policy_label} · capacity {capacity} alerts")

    selected = queue[queue["action"] == "Review today"]
    waiting = queue[queue["action"] != "Review today"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Alerts today", len(queue))
    c2.metric("Selected for review", len(selected))
    c3.metric("Amount under review", f"${selected['transaction_amt'].sum():,.0f}")
    c4.metric("Not reviewed today", len(waiting), help="At risk of missing the 24-hour deadline.")
    c5.metric("Decisions recorded", int((queue["status"] != "Open").sum()))
    if len(queue) > capacity:
        st.warning(f"{len(queue) - capacity} alerts exceed today's capacity — "
                   f"${waiting['transaction_amt'].sum():,.0f} in transactions will not be reviewed.")

    tab_queue, tab_compare, tab_volume, tab_trends, tab_team = st.tabs(
        ["Queue", "Compare policies", "Alert volume", "Trends & rules", "Team performance"])

    # ---------- Queue ----------
    with tab_queue:
        f1, f2, f3, f4 = st.columns([1, 2, 1, 1])
        min_score = f1.slider("Min risk score", 2, 6, 2)
        reasons = f2.multiselect("Reason contains any of", REASONS)
        action_filter = f3.selectbox("Action", ["All", "Review today", "Wait / expire"])
        search = f4.text_input("Search transaction / customer")

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
        table = view.assign(time=view["transaction_dt"].map(sim_time))[
            ["rank", "action", "status", "transaction_id", "time", "transaction_amt",
             "risk_score", "reasons", "customer_id"]]
        event = st.dataframe(
            table, hide_index=True, use_container_width=True,
            on_select="rerun", selection_mode="single-row", key="queue_table",
            column_config={
                "transaction_amt": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=6,
                                                              format="%d / 6"),
                "transaction_id": st.column_config.NumberColumn("Transaction", format="%d"),
            },
        )
        if event.selection.rows:
            tid = int(view.iloc[event.selection.rows[0]]["transaction_id"])
            st.button(f"Open transaction {tid} in Alert Detail →", type="primary",
                      on_click=go_to_detail, args=(tid,))

        with st.expander("How alerts are scored"):
            st.dataframe(load_rules(), hide_index=True, use_container_width=True)
            st.caption("A transaction becomes an alert when 2 or more rules fire. Thresholds come from feature "
                       "percentiles; the fraud label is never used to set them.")

    # ---------- Compare policies ----------
    with tab_compare:
        summary, curve = policy_comparison(raw, day, capacity)
        st.subheader(f"What each policy would review today at capacity {capacity}")
        st.dataframe(summary, hide_index=True, use_container_width=True,
                     column_config={
                         "Amount reviewed": st.column_config.NumberColumn(format="$%.0f"),
                         "Share of alert amount": st.column_config.NumberColumn(format="%.1%"),
                         "Avg risk score": st.column_config.NumberColumn(format="%.2f"),
                     })
        st.subheader("Share of today's alert amount covered as capacity grows (%)")
        st.line_chart(curve)
        st.caption("P1 always covers the most dollars by design; P2 prioritizes more risk signals instead. "
                   "Which policy actually stops more fraud is tested in Week 10 with the predictive model "
                   "and outcomes, since these screens use no fraud labels.")

    # ---------- Alert volume ----------
    with tab_volume:
        vol = days.set_index("sim_day")["n"]
        chart = pd.DataFrame({"Within capacity": vol.clip(upper=capacity),
                              "Overflow": (vol - capacity).clip(lower=0)})
        chart.index.name = "Simulated day"
        st.subheader(f"Alerts per day vs. capacity of {capacity}")
        st.bar_chart(chart)
        over = int((vol > capacity).sum())
        st.caption(f"{over} of {len(vol)} days exceed capacity "
                   f"({int(chart['Overflow'].sum()):,} alerts in total would go unreviewed).")

    # ---------- Trends & rules ----------
    with tab_trends:
        stats = daily_stats().set_index("sim_day")
        rule_cols = list(RULE_NAMES)

        trend = pd.DataFrame({
            "Alerts": stats["alerts"],
            "7-day average": stats["alerts"].rolling(7, min_periods=1).mean(),
            "Capacity": capacity,
        })
        trend.index.name = "Simulated day"
        st.subheader("Alert volume trend")
        st.line_chart(trend)
        peak = int(stats["alerts"].idxmax())
        st.caption(f"Busiest day: Day {peak} ({int(stats.loc[peak, 'alerts'])} alerts). "
                   f"Average {stats['alerts'].mean():.0f} alerts per day.")

        r_left, r_right = st.columns(2)
        with r_left:
            st.subheader("Which rules trigger alerts")
            totals = pd.DataFrame({
                f"Day {day}": stats.loc[day, rule_cols].astype(float),
                "All days": stats[rule_cols].sum().astype(float),
            })
            totals.index = [RULE_NAMES[c] for c in totals.index]
            st.bar_chart(totals / totals.sum() * 100, stack=False)
            st.caption("Share of rule firings (%). One alert can fire several rules.")
        with r_right:
            st.subheader("Risk score distribution")
            dist = score_distribution(day).set_index("risk_score").astype(float)
            dist.columns = [f"Day {day}", "All days"]
            st.bar_chart(dist / dist.sum() * 100, stack=False)
            st.caption("Percentage of alerts at each risk score (2–6).")

        st.subheader("Rule firings over time (7-day average)")
        over_time = stats[rule_cols].rename(columns=RULE_NAMES).rolling(7, min_periods=1).mean()
        over_time.index.name = "Simulated day"
        st.area_chart(over_time)
        st.caption("If one rule's share changes over time, the transaction pattern is shifting — "
                   "an early drift signal to check against model performance in later weeks.")

    # ---------- Team performance ----------
    with tab_team:
        log, handled = team_metrics()
        if log.empty:
            st.info("No decisions recorded yet. Record decisions in Alert Detail to see team metrics here.")
        else:
            disp = log[log["action"].isin(DISPOSITIONS)]
            resolved = disp["transaction_id"].nunique()
            confirmed = int((disp["action"] == "CONFIRM_FRAUD").sum())
            resolved_today = disp.loc[disp["sim_day"] == day, "transaction_id"].nunique()

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Decisions recorded", len(log))
            m2.metric("Alerts resolved", resolved, help="Alerts with a final decision: fraud or legitimate.")
            m3.metric("Avg handle time",
                      f"{handled['handle_minutes'].mean():.1f} min" if not handled.empty else "—",
                      help="First 'Assign for review' to first final decision, per alert.")
            m4.metric("Fraud confirmation rate", f"{confirmed / len(disp):.0%}" if len(disp) else "—",
                      help="Share of final decisions that confirmed fraud.")
            m5.metric(f"Capacity used (Day {day})", f"{resolved_today / capacity:.0%}",
                      help="Alerts resolved on this day ÷ review capacity.")

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
                per["confirmation_rate"] = per["confirmed_fraud"] / per["resolved"].replace(0, np.nan)
                st.dataframe(per.reset_index(), hide_index=True, use_container_width=True,
                             column_config={
                                 "avg_handle_min": st.column_config.NumberColumn("Avg handle (min)",
                                                                                 format="%.1f"),
                                 "confirmation_rate": st.column_config.NumberColumn("Confirmation rate",
                                                                                    format="%.0%"),
                             })
            with t_right:
                st.subheader("Decisions by action")
                st.bar_chart(log["action"].map(ACTIONS).value_counts())
            st.caption("Computed from decisions recorded in this app (ops_decision_log). Handle times reflect "
                       "real time between recorded steps, so demo values are short.")

# ============================================================
# 7. SCREEN 2 — ALERT DETAIL
# ============================================================
else:
    st.title("Alert Detail")
    ids = queue["transaction_id"].astype(int).tolist()
    if st.session_state.get("detail_txn") not in ids:
        st.session_state["detail_txn"] = ids[0]

    def label(t):
        r = queue[queue.transaction_id == t].iloc[0]
        return f"#{r['rank']} · Txn {t} · ${r['transaction_amt']:,.2f} · score {r['risk_score']} · {r['status']}"

    # Navigation through the queue in rank order
    pos = ids.index(st.session_state["detail_txn"])
    n1, n2, n3 = st.columns([1, 6, 1])
    n1.button("← Previous", disabled=pos == 0, on_click=set_detail,
              args=(ids[max(pos - 1, 0)],), use_container_width=True)
    n2.selectbox("Alert (in queue rank order)", ids, key="detail_txn", format_func=label,
                 label_visibility="collapsed")
    n3.button("Next →", disabled=pos == len(ids) - 1, on_click=set_detail,
              args=(ids[min(pos + 1, len(ids) - 1)],), use_container_width=True)

    choice = st.session_state["detail_txn"]
    row = queue[queue.transaction_id == choice].iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Amount", f"${row['transaction_amt']:,.2f}")
    c2.metric("Risk score", f"{row['risk_score']} / 6")
    c3.metric("Queue rank", f"#{row['rank']} of {len(queue)}")
    c4.metric("Recommended action", row["action"])
    c5.metric("Status", row["status"])
    st.caption(f"Customer {row['customer_id']} · {sim_time(row['transaction_dt'])} · {policy_label}")

    left, right = st.columns(2)
    with left:
        st.subheader("Why it was alerted")
        rules = load_rules()
        rules["fired"] = rules["rule_code"].map(lambda c: "✔ Yes" if bool(row[RULE_FLAGS[c]]) else "—")
        st.dataframe(rules[["fired", "rule_name", "rule_text"]], hide_index=True, use_container_width=True)

        st.subheader("This transaction vs. customer history")
        st.table(pd.DataFrame({
            "Feature": ["Hours since previous transaction", "Transactions in prior 24h",
                        "Customer avg amount (prior 30 days)", "Amount z-score vs. customer"],
            "Value": [fmt(row["hours_since_previous_txn"], "{:.2f}"), fmt(row["txn_count_24h"], "{:.0f}"),
                      fmt(row["customer_avg_amt_30d"], "${:,.2f}"), fmt(row["customer_amount_zscore"], "{:.2f}")],
        }))

    with right:
        st.subheader("Customer's last 30 days (up to this transaction)")
        hist = load_history(row["customer_id"], row["transaction_dt"])
        if len(hist) <= 1:
            st.info("No earlier transactions: this is a new customer (cold start).")
        else:
            hist["hours_before"] = (hist["transaction_dt"] - int(row["transaction_dt"])) / 3600.0
            hist["type"] = np.where(hist["transaction_id"] == choice, "This transaction", "Earlier")
            st.scatter_chart(hist, x="hours_before", y="transaction_amt", color="type")
            st.dataframe(hist.assign(time=hist["transaction_dt"].map(sim_time))[
                             ["time", "transaction_amt", "device_id", "type"]],
                         hide_index=True, use_container_width=True)
        st.caption("Only information available at the time of the transaction is shown (point-in-time rule).")

    st.divider()
    d_left, d_right = st.columns(2)
    with d_left:
        st.subheader("Record decision")
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
                st.success(f"Saved: {ACTIONS[action]} for transaction {choice}.")
                st.rerun()
    with d_right:
        st.subheader("Decision history for this alert")
        log = decision_history(choice)
        if log.empty:
            st.info("No decisions recorded yet.")
        else:
            log["action"] = log["action"].map(ACTIONS)
            st.dataframe(log, hide_index=True, use_container_width=True)