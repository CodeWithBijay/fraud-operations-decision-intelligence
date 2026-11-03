"""Fix found in the AI-assisted pilot walkthrough: dollar amounts in warning and error boxes were read as math."""
p = "app/app.py"
s = open(p).read()
fixes = [
    ('"\\n".join(f"- {w}" for w in res["warnings"]))', '"\\n".join(f"- {w}" for w in res["warnings"]).replace("$", "\\\\$"))', 2),
    ('"\\n".join(f"- {e}" for e in res["errors"]))', '"\\n".join(f"- {e}" for e in res["errors"]).replace("$", "\\\\$"))', 2),
]
for i, (old, new, n) in enumerate(fixes, 1):
    if s.count(old) != n:
        raise SystemExit(f"Fix {i}: expected {n} match(es), found {s.count(old)}. No changes saved.")
    s = s.replace(old, new)
open(p, "w").write(s)
print("Applied pilot fix to", p)
