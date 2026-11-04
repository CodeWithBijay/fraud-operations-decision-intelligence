"""UI upgrade: indigo side panel with group headings, instant Light/Dark switch (no reload),
and a decision board at the top of the Alert queue. Edits app/app.py; saves nothing on a miss."""
P = "app/app.py"
s = open(P).read()
if "UI UPGRADE" in s:
    raise SystemExit("UI upgrade already applied. No changes made.")


def replace_once(old, new, text):
    if text.count(old) != 1:
        raise SystemExit(f"Could not find: {old[:60]!r}. No changes saved.")
    return text.replace(old, new)


# 1. Both palettes in the stylesheet, so the switch can recolour the page without asking Python.
s = replace_once(
    'THEME_VARS = ":root { " + " ".join(f"--{k}: {v};" for k, v in PALETTES[THEME_MODE].items()) + " }"\n',
    'THEME_VARS = ":root { " + " ".join(f"--{k}: {v};" for k, v in PALETTES[THEME_MODE].items()) + " }\\n" + "\\n".join(\n'
    '    f\':root[data-fo-theme="{m}"] {{ \' + " ".join(f"--{k}: {v};" for k, v in pal.items()) + " }"\n'
    '    for m, pal in PALETTES.items())\n', s)

# 2. Short navigation labels.
s = replace_once('PAGES = ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast"]\n',
                 'PAGES = ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast"]\n'
                 'NAV_LABELS = {"Alert queue": "Queue", "Alert investigation": "Investigate",\n'
                 '              "Fraud risk model": "Fraud model", "Alert volume forecast": "Volume"}\n', s)
s = replace_once('format_func=lambda p: f"{PAGE_ICONS[p]}&nbsp;{p}")',
                 'format_func=lambda p: f"{PAGE_ICONS[p]}&nbsp;{NAV_LABELS[p]}")', s)

# 3. Smaller switch at the foot of the panel (the honesty note above it is drawn by the stylesheet).
s = replace_once("components.html(theme_switch_html(THEME_MODE), height=96)",
                 "components.html(theme_switch_html(THEME_MODE), height=44)", s)

# 4. Side-panel and decision-board styles, loaded after the main stylesheet.
UI_CSS = '''
# UI UPGRADE: indigo side panel, group headings, decision board.
st.markdown("""
<style>
.st-key-topnav { width: 224px !important; left: 16px; top: 16px; bottom: 16px; padding: 16px 12px 0 12px;
                 background: #312E81; border-radius: 20px; box-shadow: 0 20px 50px rgba(49,46,129,.30); overflow: hidden; }
.block-container { padding-left: calc(224px + 3.4rem) !important; }
.st-key-topnav [data-testid="stLayoutWrapper"] { flex: 1 1 auto; height: 100%; }
.st-key-topnav [data-testid="stHorizontalBlock"] { height: 100% !important; gap: 0; align-items: stretch; }
.st-key-topnav [data-testid="stColumn"]:nth-child(1) { width: 100% !important; padding: 0 4px 14px 4px;
                                                       border-bottom: 1px solid rgba(255,255,255,.12); }
.brand { justify-content: flex-start; align-items: center; gap: 10px; }
.brand-logo { width: 38px; height: 38px; border-radius: 11px; background: rgba(255,255,255,.12); color: #E0E7FF;
              box-shadow: none; flex-shrink: 0; }
.brand-name { display: block !important; font-size: .98rem; font-weight: 800; color: #FFFFFF; line-height: 1.15; }
.brand-sub { display: block !important; font-size: .72rem; color: #A5B4FC; }
.st-key-topnav [data-testid="stColumn"]:nth-child(2) { flex: 1 1 auto !important; padding-top: 6px; overflow-y: auto; }
.st-key-topnav [data-testid="stElementContainer"], .st-key-topnav .stRadio { width: 100% !important; }
.st-key-topnav div[role="radiogroup"] { flex-direction: column; align-items: stretch; gap: 4px; margin-top: 0; width: 100%; }
.st-key-topnav div[role="radiogroup"] > :nth-child(1)::before,
.st-key-topnav div[role="radiogroup"] > :nth-child(3)::before { display: block; padding: 12px 12px 6px; font-size: .68rem;
    font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: rgba(165,180,252,.70); }
.st-key-topnav div[role="radiogroup"] > :nth-child(1)::before { content: "Operations"; }
.st-key-topnav div[role="radiogroup"] > :nth-child(3)::before { content: "Models"; }
.st-key-topnav label[data-testid="stRadioOption"] { position: relative; width: 100% !important; height: 44px; margin: 0;
    padding: 0 12px !important; border-radius: 10px; display: flex; align-items: center; justify-content: flex-start;
    box-sizing: border-box; transition: background .15s; }
.st-key-topnav label[data-testid="stRadioOption"]:hover { background: rgba(67,56,202,.55); }
.st-key-topnav label[data-testid="stRadioOption"] p { flex-direction: row !important; align-items: center; gap: 10px !important;
    font-size: .875rem !important; font-weight: 600; color: #A5B4FC; text-align: left; white-space: nowrap; }
.st-key-topnav label[data-testid="stRadioOption"] p span { font-size: 1.3rem !important; }
.st-key-topnav label[data-testid="stRadioOption"]:hover p { color: #E0E7FF; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] { background: #4338CA; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF !important; }
.st-key-topnav label[data-testid="stRadioOption"][data-selected="true"]::before { content: ""; position: absolute;
    left: -12px; top: 50%; width: 4px; height: 26px; margin-top: -13px; border-radius: 0 4px 4px 0; background: #A5B4FC; }
.st-key-topnav [data-testid="stColumn"]:nth-child(3) { margin: auto -12px 0 -12px !important; width: calc(100% + 24px) !important;
    flex: 0 0 auto !important; background: #3730A3; padding: 12px; }
.st-key-topnav [data-testid="stColumn"]:nth-child(3)::before { content: "Decision support only. Analysts make the final call.";
    display: block; margin: 0 2px 10px; font-size: .72rem; line-height: 1.4; color: #C7D2FE; }
.st-key-topnav iframe { width: 100% !important; height: 44px !important; }
.decision { display: flex; flex-wrap: wrap; gap: 18px 28px; align-items: center; margin: 0 0 18px 0; padding: 20px 24px;
            border-radius: 22px; color: #FFFFFF; background: linear-gradient(135deg, #1E1B4B 0%, #312E81 60%, #4338CA 100%);
            box-shadow: 0 16px 40px rgba(49,46,129,.28); animation: rise .5s ease both; }
.decision-main { flex: 1 1 300px; }
.decision-main .tag { font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #A5B4FC; }
.decision-main h2 { margin: 4px 0 6px 0; font-size: 1.35rem; color: #FFFFFF !important; }
.decision-main p { margin: 0; font-size: .9rem; color: #C7D2FE; }
.decision-stat { flex: 0 0 auto; min-width: 120px; padding-left: 18px; border-left: 1px solid rgba(255,255,255,.18); }
.decision-stat .lab { font-size: .72rem; font-weight: 600; color: #C7D2FE; }
.decision-stat .val { font-size: 1.45rem; font-weight: 800; color: #FFFFFF; }
.first-row { font-size: .9rem; color: var(--text); line-height: 1.35; }
.first-row .muted { color: var(--muted); font-size: .8rem; }
.first-row .risk { color: var(--rose); font-weight: 700; }
@media (max-width: 900px) {
  .st-key-topnav { left: 10px; right: 10px; bottom: 10px; top: auto; width: auto !important; height: 76px;
                   padding: 6px 8px; border-radius: 22px; overflow: visible; }
  .block-container { padding-left: 1rem !important; }
  .st-key-topnav [data-testid="stLayoutWrapper"] { height: auto; }
  .st-key-topnav [data-testid="stHorizontalBlock"] { flex-direction: row; height: 64px !important; align-items: center; gap: 4px; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(1),
  .st-key-topnav [data-testid="stColumn"]:nth-child(3)::before { display: none; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(2) { flex: 1 1 auto !important; width: auto !important; min-width: 0;
                                                         padding-top: 0; overflow: visible; }
  .st-key-topnav div[role="radiogroup"] { flex-direction: row; gap: 2px; }
  .st-key-topnav div[role="radiogroup"] > :nth-child(1)::before,
  .st-key-topnav div[role="radiogroup"] > :nth-child(3)::before,
  .st-key-topnav label[data-testid="stRadioOption"][data-selected="true"]::before { display: none; }
  .st-key-topnav label[data-testid="stRadioOption"] { flex: 1 1 0; min-width: 0; height: 58px; padding: 0 2px !important;
                                                      justify-content: center; border-radius: 14px; }
  .st-key-topnav label[data-testid="stRadioOption"] p { flex-direction: column !important; gap: 2px !important;
                                                        font-size: .6rem !important; }
  .st-key-topnav label[data-testid="stRadioOption"] p span { font-size: 1.15rem !important; }
  .st-key-topnav [data-testid="stColumn"]:nth-child(3) { margin: 0 !important; width: 84px !important; flex: 0 0 84px !important;
                                                         background: transparent; padding: 0; }
  .st-key-topnav iframe { width: 84px !important; height: 50px !important; }
  .decision-stat { border-left: 0; padding-left: 0; min-width: 40%; }
}
</style>
""", unsafe_allow_html=True)
'''
s = replace_once("st.markdown(APP_CSS, unsafe_allow_html=True)\n", "st.markdown(APP_CSS, unsafe_allow_html=True)\n" + UI_CSS, s)

# 5. Instant Light/Dark switch: changes Streamlit's theme in place (no page reload) and our colours with it.
a = s.find("def theme_switch_html(mode):")
b = s.find("\n\ndef ticker_html(", a)
if a < 0 or b < 0:
    raise SystemExit("Could not find theme_switch_html. No changes saved.")
SWITCH = r'''def theme_switch_html(mode):
    """Light/Dark switch at the foot of the side panel. Switches Streamlit's theme in place - no page reload."""
    sun = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
           '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2'
           'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>')
    moon = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">'
            '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>')
    return """<html><head><style>
html,body{margin:0;height:100%;background:transparent;font-family:'Plus Jakarta Sans',system-ui,sans-serif}
.sw{display:flex;gap:4px;height:100%;padding:4px;box-sizing:border-box;border-radius:12px;background:rgba(0,0,0,.20)}
button{flex:1;border:0;border-radius:9px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;
font:600 13px/1 inherit;background:transparent;color:#A5B4FC;transition:background .2s,color .2s}
button:hover{color:#FFFFFF}
button[aria-pressed=true]{background:#FFFFFF;color:#312E81;box-shadow:0 4px 12px rgba(0,0,0,.20)}
@media (max-width:140px){button span{display:none}}
</style></head><body><div class="sw" role="group" aria-label="Colour theme">
<button data-t="Light" aria-pressed="__L__" title="Light mode">__SUN__<span>Light</span></button>
<button data-t="Dark" aria-pressed="__D__" title="Dark mode">__MOON__<span>Dark</span></button></div>
<script>
var P = window.parent;
function mark(t){ document.querySelectorAll('button').forEach(function(b){ b.setAttribute('aria-pressed', String(b.dataset.t === t)); }); }
function themeHook(){
  try {
    var el = P.document.querySelector('[data-testid="stApp"]') || P.document.querySelector('.stApp');
    var k = Object.keys(el).find(function(x){ return x.indexOf('__reactFiber$') === 0; });
    var f = el[k], n = 0;
    while (f && n < 600) {
      var v = f.memoizedProps && f.memoizedProps.value;
      if (v && typeof v === 'object' && typeof v.setTheme === 'function' && Array.isArray(v.availableThemes)) return v;
      f = f.return; n++;
    }
  } catch (e) {}
  return null;
}
function setTheme(t){
  mark(t);
  try { P.document.documentElement.setAttribute('data-fo-theme', t.toLowerCase()); } catch (e) {}
  var h = themeHook();
  var th = h && h.availableThemes.find(function(x){ return x.name === t || x.name.endsWith(' ' + t); });
  if (th) { h.setTheme(th); return; }
  try { P.localStorage.setItem('stActiveTheme-' + P.location.pathname + '-v2', JSON.stringify(t)); P.location.reload(); } catch (e) {}
}
document.querySelectorAll('button').forEach(function(b){ b.onclick = function(){ setTheme(b.dataset.t); }; });
try { var cur = P.document.documentElement.getAttribute('data-fo-theme'); if (cur) mark(cur === 'dark' ? 'Dark' : 'Light'); } catch (e) {}
</script></body></html>""".replace("__SUN__", sun).replace("__MOON__", moon) \
        .replace("__L__", str(mode == "light").lower()).replace("__D__", str(mode == "dark").lower())'''
s = s[:a] + SWITCH + s[b:]

# 6. Alert queue: a decision board first (answer + numbers + top alerts to open), no radar or ticker.
s = replace_once('"Alerts covered")) + RADAR_SVG)', '"Alerts covered")))', s)
s = replace_once("    st.markdown(ticker_html(queue.head(10)), unsafe_allow_html=True)\n", "", s)
old_start = s.find("    c1, c2, c3, c4, c5 = st.columns(5)\n")
old_end = s.find("will not be reviewed.\")\n", old_start)
if old_start < 0 or old_end < 0:
    raise SystemExit("Could not find the queue metrics block. No changes saved.")
old_end += len("will not be reviewed.\")\n")
BOARD = '''    n_rev, n_wait = len(selected), len(waiting)
    if fm:
        cov = selected["exposure"].sum() / max(queue["exposure"].sum(), 1e-9)
        cov_lab, cov_val = "Est. fraud $ covered", f"{cov:.0%}"
    else:
        cov_lab, cov_val = "Alerts covered", f"{n_rev / max(len(queue), 1):.0%}"
    if n_wait == 0:
        advice = f"All {len(queue)} alerts fit inside today's capacity of {capacity}."
    else:
        advice = (f"{n_wait} alerts (&#36;{waiting['transaction_amt'].sum():,.0f}) will not be reviewed. "
                  f"A capacity of {len(queue)} would cover them all.")
    st.markdown(
        f'<div class="decision"><div class="decision-main"><div class="tag">Today\\'s decision · Day {day}</div>'
        f'<h2>Review the top {n_rev} alerts today</h2><p>{advice}</p></div>'
        f'<div class="decision-stat"><div class="lab">Alerts today</div><div class="val">{len(queue)}</div></div>'
        f'<div class="decision-stat"><div class="lab">Amount in review</div>'
        f'<div class="val">&#36;{selected["transaction_amt"].sum():,.0f}</div></div>'
        f'<div class="decision-stat"><div class="lab">{cov_lab}</div><div class="val">{cov_val}</div></div>'
        f'<div class="decision-stat"><div class="lab">Not reviewed</div><div class="val">{n_wait}</div></div></div>',
        unsafe_allow_html=True)

    st.subheader("Review these first")
    st.caption("The highest-priority open alerts under the selected policy. Open one to see why it was raised and decide.")
    for _, r in selected[selected["status"] == "Open"].head(5).iterrows():
        tid = int(r["transaction_id"])
        with st.container(border=True):
            q1, q2, q3, q4 = st.columns([1.3, 1.2, 2.6, 0.9], vertical_alignment="center")
            q1.markdown(f'<div class="first-row"><b>#{int(r["rank"])} · Txn {tid}</b><br>'
                        f'<span class="muted">{html.escape(str(r["customer_id"]))}</span></div>', unsafe_allow_html=True)
            risk = f' · <span class="risk">{r["fraud_prob"] * 100:.1f}% risk</span>' if fm else ""
            q2.markdown(f'<div class="first-row"><b>&#36;{r["transaction_amt"]:,.2f}</b>{risk}</div>',
                        unsafe_allow_html=True)
            q3.markdown(f'<div class="first-row"><span class="muted">{html.escape(str(r["reasons"]))}</span></div>',
                        unsafe_allow_html=True)
            q4.button("Open", key=f"open_{tid}", on_click=go_to_detail, args=(tid,), type="primary", width="stretch")
'''
s = s[:old_start] + BOARD + s[old_end:]
open(P, "w").write(s)
print("UI upgrade applied:", s.count("\n") + 1, "lines")
