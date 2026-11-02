"""Fixes found when reviewing the Week 11 app in the browser."""
p = "app/app.py"
s = open(p).read()
fixes = [
    # 1. Dollar signs in summaries were read as math formulas
    ('st.info(res["summary"])', 'st.info(res["summary"].replace("$", "\\\\$"))', 2),
    # 2. Chart labels were cut off ("Purchaser email …" twice)
    ('y=alt.Y("Predictor:N", sort=alt.EncodingSortField("Contribution", op="sum", order="descending"),\n'
     '                            title=None),',
     'y=alt.Y("Predictor:N", sort=alt.EncodingSortField("Contribution", op="sum", order="descending"),\n'
     '                            title=None, axis=alt.Axis(labelLimit=340)),', 1),
    # 3. Comparison tables hid their first row
    ('st.dataframe(pd.DataFrame(res["table"]), hide_index=True, width="stretch")',
     'st.dataframe(pd.DataFrame(res["table"]), hide_index=True, width="stretch",\n'
     '                         height=35 * (len(res["table"]) + 1) + 3)', 2),
    # 4. "+19 places" was ambiguous (a larger rank number means lower priority)
    ('"Difference": f"{pos_s - pos_b:+d} places"},',
     '"Difference": "no change" if pos_s == pos_b else\n'
     '                         f"{abs(pos_s - pos_b)} places {\'lower\' if pos_s > pos_b else \'higher\'} priority"},', 1),
    ('k3.metric("Change in rank", res["table"][-2]["Difference"])',
     'k3.metric("Queue rank", res["table"][-2]["Baseline"].split(" of ")[0] + " → "\n'
     '                              + res["table"][-2]["Scenario"].split(" of ")[0],\n'
     '                              help="Rank 1 is reviewed first; a larger number means lower priority.")', 1),
    # 5. "On 0 of 53 test days ..." read oddly; report the worst day instead
    ('        if ea.get("days_with_zero_capture_at_50") is not None:\n'
     '            bullets.append(f"On {ea[\'days_with_zero_capture_at_50\']} of {ea[\'test_days\']} test days the top 50 "\n'
     '                           f"alerts contained none of that day\'s fraud dollars, so a single day\'s result can be "\n'
     '                           f"poor even when the average is good.")\n',
     '        worst = ea.get("worst_days_capture_at_50") or {}\n'
     '        if worst:\n'
     '            wd, wv = min(worst.items(), key=lambda kv: kv[1])\n'
     '            bullets.append(f"Results vary by day: on the worst test day (day {wd}) the top 50 alerts caught only "\n'
     '                           f"{wv:.0%} of that day\'s fraud dollars, so judge the policy over many days, not one.")\n', 1),
]
for i, (old, new, n) in enumerate(fixes, 1):
    found = s.count(old)
    if found != n:
        raise SystemExit(f"Fix {i}: expected {n} match(es), found {found}. No changes saved.")
    s = s.replace(old, new)
open(p, "w").write(s)
print(f"Applied {len(fixes)} fixes to {p}")
