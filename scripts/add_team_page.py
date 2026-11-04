"""Add an 'About the team' page and polish the navigation rail. Checks every spot first; saves nothing on a miss."""
P = "app/app.py"
s = open(P).read()
if "TEAM PAGE" in s:
    raise SystemExit("Team page already added. No changes made.")
if "SOFT DASHBOARD" not in s:
    raise SystemExit("Apply the soft-dashboard look first (scripts/apply_soft_look.py). No changes saved.")


def replace_once(old, new, text):
    if text.count(old) != 1:
        raise SystemExit(f"Could not find: {old[:60]!r}. No changes saved.")
    return text.replace(old, new)


RAIL_CSS = '''
# TEAM PAGE + polished rail: extra styles loaded after the main stylesheet.
st.markdown("""
<style>
.st-key-topnav [data-testid="stLayoutWrapper"] { flex: 1 1 auto; height: 100%; }
.st-key-topnav [data-testid="stHorizontalBlock"] { height: 100% !important; gap: 12px; }
.st-key-topnav [data-testid="stColumn"]:nth-child(1) { width: 64px !important; padding-bottom: 14px;
                                                       border-bottom: 1px solid rgba(255,255,255,.16); }
.st-key-topnav [data-testid="stColumn"]:nth-child(3) { margin-top: auto; }
.brand-logo { width: 48px; height: 48px; border-radius: 16px; }
.st-key-topnav div[role="radiogroup"] { margin-top: 4px; gap: 8px; }
.st-key-topnav label[data-testid="stRadioOption"] { position: relative; width: 76px; padding: 11px 4px 9px;
                                                    transition: background .2s, transform .2s, box-shadow .2s; }
.st-key-topnav label[data-testid="stRadioOption"]:hover { background: rgba(255,255,255,.10); transform: translateY(-1px); }
.st-key-topnav label[data-testid="stRadioOption"] p { font-size: .68rem; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] { background: #FFFFFF; box-shadow: 0 10px 24px rgba(0,0,0,.22); }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] p { color: var(--rail) !important; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"]::before { content: ""; position: absolute; left: -10px;
    top: 50%; width: 4px; height: 24px; margin-top: -12px; border-radius: 0 4px 4px 0; background: #FFFFFF; }
.team-card { background: var(--panel); border-radius: 24px; padding: 24px; box-shadow: 0 12px 34px var(--shadow);
             height: 100%; animation: rise .5s ease both; }
.team-head { display: flex; gap: 16px; align-items: center; margin-bottom: 14px; }
.team-avatar { width: 64px; height: 64px; border-radius: 20px; display: flex; align-items: center; justify-content: center;
               font-weight: 800; font-size: 1.3rem; color: #FFFFFF; flex-shrink: 0; }
.team-name { font-size: 1.25rem; font-weight: 800; color: var(--text); line-height: 1.2; }
.team-role { font-size: .85rem; font-weight: 600; color: var(--accent); }
.team-sub { font-size: .8rem; color: var(--muted); }
.team-card ul { margin: 0; padding-left: 1.1rem; color: var(--text); font-size: .9rem; }
.team-card li { margin: 6px 0; }
.info-card { background: var(--panel); border-radius: 22px; padding: 20px 24px; box-shadow: 0 10px 28px var(--shadow);
             color: var(--text); font-size: .92rem; margin-top: 18px; }
.info-card b { color: var(--text); }
.info-card .muted { color: var(--muted); }
@media (max-width: 900px) {
  .st-key-topnav [data-testid="stLayoutWrapper"] { height: auto; }
  .st-key-topnav [data-testid="stHorizontalBlock"] { height: 72px !important; gap: 4px; align-items: center; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(2) { min-width: 0; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(3) { margin-top: 0; height: 62px; overflow: hidden;
                                                         flex: 0 0 96px !important; width: 96px !important; }
  .st-key-topnav iframe { width: 96px !important; height: 62px !important; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(3) [data-testid="stElementContainer"] { height: 62px; }
  .st-key-topnav label[data-testid="stRadioOption"] { width: auto; min-width: 0; padding: 8px 1px; }
  .st-key-topnav label[data-testid="stRadioOption"] p { font-size: .56rem; white-space: nowrap; }
  .st-key-topnav label[data-testid="stRadioOption"][data-selected="true"]::before { display: none; }
}
</style>
""", unsafe_allow_html=True)
'''
s = replace_once("st.markdown(APP_CSS, unsafe_allow_html=True)\n",
                 "st.markdown(APP_CSS, unsafe_allow_html=True)\n" + RAIL_CSS, s)
s = replace_once('''    "Alert volume forecast": ":material/insights:",
}''', '''    "Alert volume forecast": ":material/insights:",
    "About the team": ":material/groups:",
}''', s)
s = replace_once('PAGES = ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast"]\n',
                 'PAGES = ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast", "About the team"]\n'
                 'NAV_LABELS = {"Alert queue": "Queue", "Alert investigation": "Investigate", "Fraud risk model": "Fraud model",\n'
                 '              "Alert volume forecast": "Volume", "About the team": "Team"}\n', s)
s = replace_once('format_func=lambda p: f"{PAGE_ICONS[p]}&nbsp;{p}")',
                 'format_func=lambda p: f"{PAGE_ICONS[p]}&nbsp;{NAV_LABELS[p]}")', s)

