"""Week 12 app changes: sign-in with two roles (Fraud Ops Lead, Fraud Analyst) and four fixes from user testing
(new-customer note, what-if takeaway, estimate vs. actual note, capacity trade-off). Edits app/app.py; saves nothing
on a miss."""
P = "app/app.py"
s = open(P).read()
if "SIGN-IN AND ROLES" in s:
    raise SystemExit("Already applied. No changes made.")
if "UI UPGRADE" not in s:
    raise SystemExit("Apply scripts/improve_ui.py first. No changes saved.")


def replace_once(old, new, text):
    if text.count(old) != 1:
        raise SystemExit(f"Could not find: {old[:60]!r}. No changes saved.")
    return text.replace(old, new)


# 1. Libraries for password checking.
s = replace_once("import html\n", "import hashlib\nimport hmac\nimport html\nimport time\n", s)

# 2. Sign-in page and roles, shown before anything else.
LOGIN = '''# ============================================================
# 6b. SIGN-IN AND ROLES
# ============================================================
ROLE_NAMES = {"lead": "Fraud Ops Lead", "analyst": "Fraud Analyst"}
ROLE_PAGES = {"lead": PAGES, "analyst": ["Alert queue", "Alert investigation"]}


def app_users():
    """Accounts from Streamlit Secrets ([users.<name>] role, salt, hash). Only PBKDF2 hashes are stored."""
    try:
        return {name.lower(): dict(acc) for name, acc in st.secrets["users"].items()}
    except Exception:
        return {}


def check_login(username, password):
    acc = app_users().get(username.strip().lower())
    if not acc or acc.get("role") not in ROLE_NAMES:
        return None
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(acc["salt"]), 200_000).hex()
    return acc["role"] if hmac.compare_digest(digest, acc["hash"]) else None


def sign_out():
    for k in ("auth_user", "auth_role", "page"):
        st.session_state.pop(k, None)


if "auth_role" not in st.session_state:
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(f'<div style="display:flex;gap:14px;align-items:center;margin:8vh 0 18px"><div style="width:48px;'
                    f'height:48px;border-radius:14px;background:#312E81;color:#FFFFFF;display:flex;align-items:center;'
                    f'justify-content:center">{SHIELD_SVG}</div>'
                    f'<div><div style="font-size:1.6rem;font-weight:800">FraudOps</div>'
                    f'<div style="color:var(--muted)">Decision Intelligence · sign in</div></div></div>',
                    unsafe_allow_html=True)
        locked = time.time() < st.session_state.get("login_locked_until", 0)
        with st.form("login"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            ok = st.form_submit_button("Sign in", type="primary", width="stretch", disabled=locked)
        if locked:
            st.error("Too many failed attempts. Wait one minute, then try again.")
        elif ok:
            role = check_login(user, pw)
            if role:
                st.session_state["auth_user"], st.session_state["auth_role"] = user.strip().lower(), role
                st.session_state["login_failures"] = 0
                st.rerun()
            st.session_state["login_failures"] = st.session_state.get("login_failures", 0) + 1
            if st.session_state["login_failures"] >= 5:
                st.session_state["login_locked_until"], st.session_state["login_failures"] = time.time() + 60, 0
            st.error("Wrong username or password.")
        if not app_users():
            st.warning("No accounts are set up yet. Create one with scripts/make_user.py and add it to the secrets.")
        st.caption("Two roles. The Fraud Ops Lead sees every page and sets the queue policy and review capacity. "
                   "A Fraud Analyst works the queue and investigates alerts.")
    st.stop()

ROLE = st.session_state["auth_role"]
ALLOWED_PAGES = ROLE_PAGES[ROLE]
if st.session_state.get("page") not in ALLOWED_PAGES:
    st.session_state["page"] = ALLOWED_PAGES[0]


def tested_capture(k, prefix="P4"):
    """Real fraud-dollar share caught at k reviews a day in the final test (None if not evaluated)."""
    for r in (fm["metrics"].get("capture_at_capacity", []) if fm else []):
        if r["policy"].startswith(prefix) and r["capacity"] == k:
            return float(r["fraud_value_captured"])
    return None


'''
s = replace_once('with st.container(key="topnav"):\n', LOGIN + 'with st.container(key="topnav"):\n', s)
s = replace_once('page = st.radio("Navigation", PAGES, key="page"', 'page = st.radio("Navigation", ALLOWED_PAGES, key="page"', s)

# 3. Toolbar: who is signed in, sign out, and Lead-only controls.
s = replace_once('''    st.markdown('<div class="toolbar-title">Decision settings · what-if controls used by every page</div>',
                unsafe_allow_html=True)
''', '''    tb1, tb2 = st.columns([5, 1.2], vertical_alignment="center")
    tb1.markdown(f'<div class="toolbar-title">Decision settings · signed in as {html.escape(st.session_state["auth_user"])}'
                 f' ({ROLE_NAMES[ROLE]})</div>', unsafe_allow_html=True)
    tb2.button("Sign out", on_click=sign_out, width="stretch")
''', s)
s = replace_once('policy_label = t2.selectbox("Queue policy", list(policies.keys()))',
                 'policy_label = t2.selectbox("Queue policy", list(policies.keys()), disabled=ROLE != "lead",\n'
                 '                                help=None if ROLE == "lead" else "Set by the Fraud Ops Lead.")', s)
s = replace_once('''    capacity = t3.slider("Review capacity (alerts per day)", 5, 300, 50, 5,
                         help="Assumption: how many alerts the analyst team can review today.")''',
                 '''    capacity = t3.slider("Review capacity (alerts per day)", 5, 300, 50, 5, disabled=ROLE != "lead",
                         help="Assumption: how many alerts the analyst team can review today."
                              + ("" if ROLE == "lead" else " Set by the Fraud Ops Lead."))''', s)
s = replace_once('value=st.session_state.get("analyst", "Fraud Analyst 1"))',
                 'value=st.session_state.get("analyst", st.session_state["auth_user"]))', s)

# 4. Queue page: estimate vs. actual note, and the Lead's capacity trade-off.
s = replace_once('''        f'<div class="decision-stat"><div class="lab">Not reviewed</div><div class="val">{n_wait}</div></div></div>',
        unsafe_allow_html=True)
''', '''        f'<div class="decision-stat"><div class="lab">Not reviewed</div><div class="val">{n_wait}</div></div></div>',
        unsafe_allow_html=True)
    if fm:
        t50 = tested_capture(50)
        st.caption("**Estimate vs. actual.** Est. fraud $ covered is the model's own estimate, and it counts only today's "
                   "alerts. The tested KPI on the Fraud risk model page counts real fraud dollars across all of a day's "
                   "transactions, so it is lower"
                   + (f": about {t50:.0%} at 50 reviews a day in the final test." if t50 is not None else "."))
        if ROLE == "lead":
            exp_sorted = queue["exposure"].sort_values(ascending=False)
            total_exp, more = max(exp_sorted.sum(), 1e-9), min(capacity + 50, len(queue))
            if more > capacity:
                gain = (exp_sorted.head(more).sum() - exp_sorted.head(capacity).sum()) / total_exp
                line = (f"Reviewing {more} alerts instead of {capacity} today (+{more - capacity} reviews) would raise "
                        f"estimated fraud covered by {gain * 100:.0f} percentage points.")
            else:
                line = (f"All {len(queue)} of today's alerts already fit inside a capacity of {capacity}, so extra "
                        f"reviewers would not add coverage today.")
            tested = " · ".join(f"{k} a day: {tested_capture(k):.0%}" for k in (25, 50, 100, 200)
                                if tested_capture(k) is not None)
            st.info(f"**Capacity trade-off.** {line}"
                    + (f" In the final test, real fraud dollars caught by capacity: {tested}." if tested else ""))
''', s)

# 5. Model page: say that the tested KPI differs from the queue's estimate.
s = replace_once('''        bullets.append("Results come from public IEEE-CIS data''',
                 '''        bullets.append("This is the real, tested result. The Alert queue page shows a different number: the model's "
                       "own estimate for today's alerts only, which is often higher.")
        bullets.append("Results come from public IEEE-CIS data''', s)

# 6. What-if: explain the zeros for a new customer.
s = replace_once('''                                        value=int(one["prior_txn_count"].iloc[0]), step=1)
''', '''                                        value=int(one["prior_txn_count"].iloc[0]), step=1)
                if cold:
                    st.info("**New customer: no history.** The history fields show 0 because nothing is recorded, not "
                            "because a 0 was recorded; the model treats them as missing. Untick 'New customer' only "
                            "to test how an existing customer would score.")
''', s)

# 7. What-if result: a three-line takeaway first (with the range warning), full summary folded away.
s = replace_once('''                    k1, k2, k3 = st.columns(3)
                    k1.metric("Baseline (as recorded)", pct(res["base"]))''',
                 '''                    rank_row, cap_row = res["table"][-2], res["table"][-1]
                    act = "reviewed today" if cap_row["Scenario"] == "Yes" else "not reviewed today"
                    take = [f"**What changed:** fraud probability {pct(res['base'])} → {pct(res['p'])}; queue rank "
                            f"{rank_row['Baseline'].split(' of ')[0]} → {rank_row['Scenario'].split(' of ')[0]}.",
                            "**Action:** " + (f"no change, still {act}." if cap_row["Baseline"] == cap_row["Scenario"]
                                              else f"changes, now {act}."),
                            (f"**⚠ Caution:** {len(res['warnings'])} input(s) are outside the range the model was "
                             "trained on, so treat this result as a rough guide." if res["warnings"] else
                             "**Reliability:** inputs are within the model's usual range. It is still a model "
                             "estimate, not proof of fraud.")]
                    (st.warning if res["warnings"] else st.success)("**Takeaway**\\n\\n" + "\\n\\n".join(take))
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Baseline (as recorded)", pct(res["base"]))''', s)
s = replace_once('''                    st.markdown("#### Scenario summary")
                    st.info(res["summary"].replace("$", "\\\\$"))''',
                 '''                    with st.expander("Full scenario summary: inputs, comparison, trade-off, implication, limitations"):
                        st.info(res["summary"].replace("$", "\\\\$"))''', s)

open(P, "w").write(s)
print("Sign-in, roles and user-test fixes added:", s.count("\n") + 1, "lines")
