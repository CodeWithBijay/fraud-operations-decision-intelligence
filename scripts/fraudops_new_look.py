"""FraudOps new look: calm palette (one accent + neutrals, red only for risk), light/dark switch,
illustrations, gauges, live priority ticker and a mobile layout. Presentation only: data, models and numbers
are untouched. Works on the Week 11 app, with or without the earlier dark-console script.
Run from the project folder:  python3 scripts/fraudops_new_look.py
"""
import re

P = "app/app.py"
s = open(P).read()
if "LIGHT/DARK THEME" in s:
    raise SystemExit("New look already applied. No changes made.")
V1 = "art=PAGE_ART" in s  # earlier dark-console script already applied


def sub_once(pattern, repl, text):
    new, n = re.subn(pattern, lambda m: repl, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"Could not find: {pattern[:70]!r}. No changes saved.")
    return new


def replace_once(old, new, text):
    if text.count(old) != 1:
        raise SystemExit(f"Expected one match for: {old[:70]!r} (found {text.count(old)}). No changes saved.")
    return text.replace(old, new)


CSS = r'''# LIGHT/DARK THEME: one stylesheet, two palettes. The viewer's choice (or their device setting) picks one.
THEME_MODE = "light" if st.context.theme.type == "light" else "dark"
PALETTES = {
    "dark": {"bg": "#0B0D10", "panel": "#12161B", "panel2": "#161B21", "line": "rgba(148,163,184,.16)",
             "accent": "#2DD4BF", "accent-soft": "rgba(45,212,191,.12)", "accent-line": "rgba(45,212,191,.35)",
             "rose": "#F43F5E", "rose-soft": "rgba(244,63,94,.12)", "text": "#E5E7EB", "muted": "#94A3B8",
             "grid": "rgba(148,163,184,.035)", "glow": "rgba(45,212,191,.10)", "nav": "rgba(11,13,16,.86)",
             "btn-text": "#04201C", "shadow": "rgba(0,0,0,.35)"},
    "light": {"bg": "#F5F6F8", "panel": "#FFFFFF", "panel2": "#FFFFFF", "line": "rgba(15,23,42,.10)",
              "accent": "#0F766E", "accent-soft": "rgba(15,118,110,.08)", "accent-line": "rgba(15,118,110,.30)",
              "rose": "#E11D48", "rose-soft": "rgba(225,29,72,.08)", "text": "#111827", "muted": "#6B7280",
              "grid": "rgba(15,23,42,.03)", "glow": "rgba(15,118,110,.07)", "nav": "rgba(255,255,255,.88)",
              "btn-text": "#FFFFFF", "shadow": "rgba(15,23,42,.08)"},
}
THEME_VARS = ":root { " + " ".join(f"--{k}: {v};" for k, v in PALETTES[THEME_MODE].items()) + " }"

APP_CSS = """
<style>
/* FraudOps theme: light/dark */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');
__VARS__
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea, select { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: radial-gradient(900px 500px at 85% -10%, var(--glow), transparent 60%),
                     linear-gradient(var(--grid) 1px, transparent 1px) 0 0 / 100% 32px,
                     linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0 / 32px 100%, var(--bg); }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding: 0 2.5rem 2rem 2.5rem !important; max-width: 1480px; }
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
h1, h2, h3, h4 { letter-spacing: -0.01em; color: var(--text); font-family: 'Space Grotesk', sans-serif; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: 0.4rem; }
h4 { font-size: .98rem !important; }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes pulse { 0%,100% { opacity: 1; } 60% { opacity: .35; } }
@keyframes sweep { to { transform: rotate(360deg); } }
@keyframes blink { 0%,100% { opacity: .25; } 50% { opacity: 1; } }
@keyframes gauge { from { stroke-dashoffset: var(--full); } to { stroke-dashoffset: var(--target); } }
@keyframes ticker { from { transform: translateX(0); } to { transform: translateX(-50%); } }

/* Top navigation */
.st-key-topnav { position: sticky; top: 0; z-index: 999; background: var(--nav); backdrop-filter: blur(12px);
                 border-bottom: 1px solid var(--line); box-sizing: border-box;
                 width: 100vw !important; max-width: 100vw !important; min-width: 100vw;
                 margin-left: calc(50% - 50vw); margin-top: -1rem; padding: 10px 2.5rem; }
.st-key-topnav [data-testid="stHorizontalBlock"] { align-items: center; }
.st-key-topnav iframe { display: block; }
.brand { display: flex; align-items: center; gap: 11px; color: var(--accent); }
.brand-logo { width: 38px; height: 38px; border-radius: 11px; display: flex; align-items: center; justify-content: center;
              background: var(--accent-soft); border: 1px solid var(--accent-line); flex-shrink: 0; }
.brand-name { font-weight: 700; font-size: 1.08rem; color: var(--text); line-height: 1.1; letter-spacing: .02em; }
.brand-sub { font-size: 0.64rem; color: var(--muted); letter-spacing: 0.16em; text-transform: uppercase; display: flex; align-items: center; gap: 6px; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: pulse 2s infinite; display: inline-block; }
.st-key-topnav div[role="radiogroup"] { gap: 4px; flex-wrap: nowrap; justify-content: center; }
.st-key-topnav label[data-testid="stRadioOption"] { padding: 8px 14px; border-radius: 9px; margin: 0; border: 1px solid transparent;
                                                    transition: all .18s; white-space: nowrap; }
.st-key-topnav label[data-testid="stRadioOption"]:hover { background: var(--accent-soft); }
.st-key-topnav label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none; }
.st-key-topnav label[data-testid="stRadioOption"] p { font-size: 0.9rem; font-weight: 500; color: var(--muted); }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] { background: var(--accent-soft); border-color: var(--accent-line); }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] p { color: var(--accent); font-weight: 600; }

/* Hero */
.hero { margin: 22px 0 18px 0; padding: 26px 30px; border-radius: 18px; color: var(--text); position: relative; overflow: hidden;
        background: var(--panel); border: 1px solid var(--line); box-shadow: 0 1px 2px var(--shadow);
        display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap; animation: rise .45s ease both; }
.hero::before { content: ""; position: absolute; inset: 0; pointer-events: none;
                background: radial-gradient(500px 220px at 100% 0%, var(--glow), transparent 70%); }
.hero-text { position: relative; flex: 1 1 420px; }
.hero .eyebrow { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent);
                 font-family: 'JetBrains Mono', monospace; }
.hero h1 { color: var(--text) !important; font-size: 2.1rem; font-weight: 700; margin: 6px 0 6px 0; padding: 0; }
.hero p { color: var(--muted); margin: 0 0 14px 0; font-size: 0.98rem; max-width: 680px; }
.hero-art { position: relative; flex: 0 0 auto; display: flex; align-items: center; gap: 18px; color: var(--accent); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { font-size: 0.76rem; font-weight: 500; padding: 5px 11px; border-radius: 8px; background: var(--accent-soft);
        color: var(--accent); border: 1px solid var(--accent-line); white-space: nowrap; font-family: 'JetBrains Mono', monospace; }
.chip.warn { background: var(--rose-soft); color: var(--rose); border-color: var(--rose); }
.chip.ok { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-line); }
.chip.neutral { background: transparent; color: var(--muted); border-color: var(--line); }
.radar .sweep { transform-origin: 70px 70px; animation: sweep 4s linear infinite; }
.radar .blip { animation: blink 2.2s ease-in-out infinite; }
.gauge-wrap { text-align: center; }
.gauge-arc { animation: gauge 1.4s cubic-bezier(.2,.8,.2,1) both; }
.gauge-label { font-size: .66rem; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin-top: 2px; }

/* Live ticker */
.ticker { border: 1px solid var(--line); background: var(--panel); border-radius: 12px; overflow: hidden;
          display: flex; align-items: center; margin: 4px 0 18px 0; }
.ticker-tag { flex: 0 0 auto; padding: 9px 14px; background: var(--rose-soft); color: var(--rose); font-weight: 700;
              font-size: .72rem; letter-spacing: .14em; border-right: 1px solid var(--line); display: flex; gap: 8px; align-items: center;
              font-family: 'JetBrains Mono', monospace; }
.ticker-tag .live-dot { background: var(--rose); }
.ticker-window { overflow: hidden; flex: 1; }
.ticker-track { display: inline-flex; gap: 34px; white-space: nowrap; padding: 9px 0; animation: ticker 38s linear infinite;
                font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: var(--muted); }
.ticker:hover .ticker-track { animation-play-state: paused; }
.ticker-track b { color: var(--accent); font-weight: 600; }
.ticker-track .hot { color: var(--text); font-weight: 600; }

/* Settings toolbar */
.st-key-toolbar { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 14px 18px 4px 18px;
                  margin-bottom: 18px; animation: rise .5s ease both; box-shadow: 0 1px 2px var(--shadow); }
.toolbar-title { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent);
                 margin-bottom: 2px; font-family: 'JetBrains Mono', monospace; }

/* Footer */
.site-footer { margin-top: 48px; padding: 22px 0 6px 0; border-top: 1px solid var(--line); display: flex;
               justify-content: space-between; gap: 16px; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); }
.site-footer b { color: var(--text); }

/* Cards and metrics */
[data-testid="stMetric"] { background: var(--panel2); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px;
                           position: relative; overflow: hidden; box-shadow: 0 1px 2px var(--shadow);
                           transition: transform .18s, border-color .18s, box-shadow .18s; animation: rise .5s ease both; }
[data-testid="stMetric"]::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 2px;
                                   background: linear-gradient(90deg, var(--accent), transparent); }
[data-testid="stMetric"]:hover { transform: translateY(-3px); border-color: var(--accent-line); box-shadow: 0 10px 28px var(--shadow); }
[data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] { animation-delay: .06s; }
[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] { animation-delay: .12s; }
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] { animation-delay: .18s; }
[data-testid="stColumn"]:nth-child(5) [data-testid="stMetric"] { animation-delay: .24s; }
[data-testid="stMetricLabel"] p { font-size: 0.72rem !important; color: var(--muted) !important; font-weight: 600;
                                  text-transform: uppercase; letter-spacing: .1em; }
[data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; color: var(--text);
                                font-family: 'JetBrains Mono', monospace !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 12px; overflow: hidden; }
[data-testid="stExpander"] details { border-radius: 12px; border-color: var(--line); background: var(--panel); }
[data-testid="stAlert"] { border-radius: 12px; }

/* Tabs as a segmented control */
.stTabs [role="tablist"] { gap: 4px; background: var(--panel); padding: 4px; border-radius: 12px; border: 1px solid var(--line);
                           width: fit-content; max-width: 100%; overflow-x: auto; margin-bottom: 8px; }
.stTabs [data-testid="stTab"] { height: 36px; padding: 0 16px; border-radius: 9px; background: transparent;
                                display: flex; align-items: center; transition: background .15s; }
.stTabs [data-testid="stTab"] p { font-size: 0.88rem; font-weight: 500; color: var(--muted); margin: 0; }
.stTabs [data-testid="stTab"]:hover p { color: var(--text); }
.stTabs [data-testid="stTab"][aria-selected="true"] { background: var(--accent-soft); box-shadow: inset 0 0 0 1px var(--accent-line); }
.stTabs [data-testid="stTab"][aria-selected="true"] p { color: var(--accent) !important; font-weight: 600; }
.stTabs .react-aria-SelectionIndicator { display: none; }
.stTabs [role="tablist"]::after, .stTabs [role="tablist"]::before { display: none; }

/* Buttons */
.stButton > button, .stFormSubmitButton > button { border-radius: 10px; font-weight: 600; transition: transform .15s, box-shadow .15s; }
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] { color: var(--btn-text) !important; }
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
    transform: translateY(-1px); box-shadow: 0 6px 20px var(--accent-line); }

/* Mobile and tablet */
@media (max-width: 900px) {
  .block-container { padding: 0 1rem 1.5rem 1rem !important; }
  .st-key-topnav { padding: 8px 1rem; margin-top: -.5rem; }
  .st-key-topnav [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 8px; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(1) { flex: 1 1 55% !important; min-width: 55% !important; width: 55% !important; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(3) { flex: 1 1 35% !important; min-width: 35% !important; width: 35% !important;
                                                          order: 2; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(2) { flex: 1 1 100% !important; min-width: 100% !important; width: 100% !important;
                                                          order: 3; }
  .st-key-topnav div[role="radiogroup"] { justify-content: flex-start; overflow-x: auto; flex-wrap: nowrap;
                                          scrollbar-width: none; padding-bottom: 2px; }
  .st-key-topnav div[role="radiogroup"]::-webkit-scrollbar { display: none; }
  .st-key-topnav label[data-testid="stRadioOption"] { padding: 7px 10px; }
  .st-key-topnav label[data-testid="stRadioOption"] p { font-size: .82rem; }
  .hero { padding: 18px; gap: 12px; margin: 14px 0 12px 0; }
  .hero h1 { font-size: 1.5rem; }
  .hero p { font-size: .9rem; }
  .hero-art { width: 100%; justify-content: center; }
  .hero-art .radar, .hero-art > svg { display: none; }
  .st-key-toolbar { padding: 12px 12px 2px 12px; }
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
  .stTabs [role="tablist"] { width: 100%; }
  .stTabs [data-testid="stTab"] { padding: 0 11px; flex-shrink: 0; }
  .ticker-tag { padding: 9px 10px; font-size: .66rem; }
  .site-footer { flex-direction: column; }
}
@media (max-width: 640px) {
  .hero-art .gauge-wrap svg { width: 96px; height: 96px; }
  .brand-name { font-size: 1rem; }
  .brand-sub { display: none; }
}
</style>
""".replace("__VARS__", THEME_VARS)
st.markdown(APP_CSS'''
s = sub_once(r'APP_CSS = """\n<style>.*?</style>\n"""\nst\.markdown\(APP_CSS', CSS, s)

s = sub_once(r"SHIELD_SVG = \(.*?\n\n\ndef page_header\(eyebrow, title, subtitle, chips=\(\)(?:, art=None)?\):.*?unsafe_allow_html=True\)",
             HELPERS, s)
s = sub_once(r'RAISES, LOWERS = "#[0-9A-Fa-f]{6}", "#[0-9A-Fa-f]{6}"', 'RAISES, LOWERS = "#E8556D", "#14B8A6"', s)
s = sub_once(r'<div class="brand-sub">[^<]*(?:<span class="live-dot"></span>[^<]*)?</div>',
             '<div class="brand-sub"><span class="live-dot"></span>Fraud ops console</div>', s)

# Theme switch replaces the user label in the top bar
s = replace_once("import streamlit as st\n", "import streamlit as st\nimport streamlit.components.v1 as components\n", s)
s = replace_once("""    n3.markdown('<div class="user-pill"><div><div class="user-name">Fraud Operations Lead</div>'
                '<div class="user-sub">Demo workspace · simulated data</div></div><div class="avatar">FL</div></div>',
                unsafe_allow_html=True)""", """    with n3:
        components.html(theme_switch_html(THEME_MODE), height=46)""", s)

GAUGE = """art=(gauge_svg(row["fraud_prob"], "Fraud probability",
                               "var(--rose)" if row["fraud_prob"] >= 0.3 else "var(--accent)") if fm else "")
                    + PAGE_ART["network"])"""
if V1:
    s = sub_once(r'art=\(gauge_svg\(row\["fraud_prob"\], "Fraud probability",.*?PAGE_ART\["network"\]\)', GAUGE, s)
else:
    s = replace_once("""                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"Capacity {capacity}", "neutral"),
                 (f"{over} over capacity", "warn") if over > 0 else ("Within capacity", "ok")])
""", """                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"Capacity {capacity}", "neutral"),
                 (f"{over} over capacity", "warn") if over > 0 else ("Within capacity", "ok")],
                art=(gauge_svg(queue.loc[queue["rank"] <= capacity, "exposure"].sum() / max(queue["exposure"].sum(), 1e-9),
                               "Est. fraud $ covered") if fm else
                     gauge_svg(min(capacity, len(queue)) / max(len(queue), 1), "Alerts covered")) + RADAR_SVG)
""", s)
    s = replace_once("""    tab_queue, tab_compare, tab_volume, tab_trends, tab_team = st.tabs(""",
                     """    st.markdown(ticker_html(queue.head(10)), unsafe_allow_html=True)
    tab_queue, tab_compare, tab_volume, tab_trends, tab_team = st.tabs(""", s)
    s = replace_once("""    page_header(f"Investigation · Day {day}", "Alert investigation",
                "Why an alert was raised, what the model sees, how it responds to change, and the decision.",
                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"{len(queue)} alerts in queue", "neutral")])
    ids = queue["transaction_id"].astype(int).tolist()""", """    ids = queue["transaction_id"].astype(int).tolist()""", s)
    s = replace_once("""    choice = st.session_state["detail_txn"]
    row = queue[queue.transaction_id == choice].iloc[0]
""", """    choice = st.session_state["detail_txn"]
    row = queue[queue.transaction_id == choice].iloc[0]
    page_header(f"Investigation · Day {day}", "Alert investigation",
                "Why an alert was raised, what the model sees, how it responds to change, and the decision.",
                [(f"Policy: {POLICY_SHORT[policy]}", ""), (f"{len(queue)} alerts in queue", "neutral"),
                 (f"Txn {choice}", "neutral")],
                """ + GAUGE + """
""", s)
    s = replace_once("""                [("Logistic regression", ""), ("Evaluated on later, unseen days", "neutral")])""",
                     """                [("Logistic regression", ""), ("Evaluated on later, unseen days", "neutral")],
                art=PAGE_ART["network"] + RADAR_SVG)""", s)
    s = replace_once("""                [("Poisson regression", ""), (f"Capacity {capacity}", "neutral")])""",
                     """                [("Poisson regression", ""), (f"Capacity {capacity}", "neutral")],
                art=PAGE_ART["bars"])""", s)
open(P, "w").write(s)

# Streamlit theme: light and dark variants (default follows the viewer's device)
open(".streamlit/config.toml", "w").write('''[theme]
font = "sans serif"

[theme.light]
primaryColor = "#0F766E"
backgroundColor = "#F5F6F8"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#111827"

[theme.dark]
primaryColor = "#2DD4BF"
backgroundColor = "#0B0D10"
secondaryBackgroundColor = "#161B21"
textColor = "#E5E7EB"

[client]
toolbarMode = "minimal"

[browser]
gatherUsageStats = false
''')
print("New look applied to app/app.py and .streamlit/config.toml")
