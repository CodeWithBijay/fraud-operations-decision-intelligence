"""Week 12 fix (TEST-22): the Assistant also searches singular forms of plural words ("KPIs" -> "KPI").
Safe to run more than once."""
P = "app/app.py"
s = open(P).read()
old = "        sims = linear_kernel(vec.transform([question]), mat).ravel()\n"
new = ("        words = re.findall(r\"[\\w-]+\", question.lower())\n"
       "        question = question + \" \" + \" \".join(w[:-1] for w in words if len(w) > 3 and w.endswith(\"s\"))\n"
       "        sims = linear_kernel(vec.transform([question]), mat).ravel()\n")
if "w.endswith(\"s\")" in s:
    print("Already applied.")
elif s.count(old) == 1:
    open(P, "w").write(s.replace(old, new)); print("Plural matching added to the Assistant.")
else:
    raise SystemExit("Assistant search line not found. No changes made.")
