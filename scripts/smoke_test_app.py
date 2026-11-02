"""Opens every page of the app headlessly and runs one valid and one invalid what-if."""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("../app/app.py", default_timeout=180).run()
problems = []
for page in ["Alert queue", "Alert investigation", "Fraud risk model", "Alert volume forecast"]:
    at.radio(key="page").set_value(page).run()
    errs = [e.value for e in at.exception]
    print(f"{page:<24} {'OK' if not errs else 'ERROR: ' + str(errs[0])[:200]}")
    problems += errs

at.radio(key="page").set_value("Alert investigation").run()
form_inputs = [n for n in at.number_input if n.label == "Amount ($)"]
form_inputs[0].set_value(form_inputs[0].value * 3)
at.button[[b.label for b in at.button].index("Run scenario")].click().run()
print("What-if (amount x3)     ", "OK - table + summary shown" if any("Baseline vs. scenario" in m.value
      for m in at.markdown) else "no result shown", "| errors:", len(at.exception))

prior = [n for n in at.number_input if n.label == "Customer's prior transaction count"][0]
cnt = [n for n in at.number_input if n.label == "Transactions in prior 24h"][0]
cnt.set_value(prior.value + 5)
at.button[[b.label for b in at.button].index("Run scenario")].click().run()
print("Invalid input check     ", "OK - blocked" if any("inconsistent" in e.value for e in at.error)
      else "not blocked")
print("RESULT:", "ALL PAGES OK" if not problems else f"{len(problems)} problem(s)")
