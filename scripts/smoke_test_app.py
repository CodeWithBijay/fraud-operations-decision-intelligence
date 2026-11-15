"""Opens every page of the app headlessly and runs one valid and one invalid what-if."""
from streamlit.testing.v1 import AppTest

# Sign-in: without an account the app must stop at the sign-in page.
gate = AppTest.from_file("../app/app.py", default_timeout=180).run()
print("Sign-in page shown      ", "OK" if any(b.label == "Sign in" for b in gate.button) and
      not [r for r in gate.radio if r.key == "page"] else "NOT SHOWN")
gate.text_input[0].set_value("nobody")
gate.text_input[1].set_value("wrong-password")
gate.button[[b.label for b in gate.button].index("Sign in")].click().run()
print("Wrong password blocked  ", "OK" if any("Wrong username or password" in e.value for e in gate.error)
      else "NOT BLOCKED")

analyst = AppTest.from_file("../app/app.py", default_timeout=180)
analyst.session_state["auth_user"], analyst.session_state["auth_role"] = "test-analyst", "analyst"
analyst.run()
print("Analyst pages limited   ", "OK" if len(analyst.radio(key="page").options) == 3 and
      [s.disabled for s in analyst.slider if s.label.startswith("Review capacity")] == [True] else "NOT LIMITED")

at = AppTest.from_file("../app/app.py", default_timeout=180)
at.session_state["auth_user"], at.session_state["auth_role"] = "test-lead", "lead"
at.run()
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
at.radio(key="page").set_value("Ask FraudOps").run()
at.chat_input[0].set_value("What does PR-AUC mean?").run()
bot = [m for m in at.chat_message if m.name == "assistant"]
print("Assistant chatbot       ", "OK - answer + sources" if bot and any("Sources" in e.label for e in at.expander)
      and not at.exception else "no answer", "| errors:", len(at.exception))
problems += [e.value for e in at.exception]
print("RESULT:", "ALL PAGES OK" if not problems else f"{len(problems)} problem(s)")
