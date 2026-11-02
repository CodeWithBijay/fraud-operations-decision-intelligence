"""Week 11, item 1a-1b: time-based three-way split and data-leakage checks.

Split (oldest -> newest): development 60% | validation 15% | final test 25%.
Run: python3 src/modeling/week11_split_and_leakage.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FEATURE_SETS, FRAUD_FEATURE_LABELS, ROOT, fraud_design, get_engine  # noqa: E402

QUERY = """
SELECT f.transaction_dt, f.transaction_amt::float8 AS transaction_amt,
       f.hours_since_previous_txn::float8 AS hours_since_previous_txn, f.txn_count_24h,
       f.customer_avg_amt_30d::float8 AS customer_avg_amt_30d,
       f.customer_amount_zscore::float8 AS customer_amount_zscore, f.prior_txn_count, f.cold_start_flag,
       t.is_fraud::int AS is_fraud, t.product_cd, t.card4, t.card6, t.p_emaildomain,
       t.c1, t.c2, t.c3, t.c4, t.c5, t.c6, t.c7, t.c8, t.c9, t.c10, t.c11, t.c12, t.c13, t.c14,
       t.d1, t.d10, t.d11, t.d12, t.d13, t.d14, t.d15
FROM transaction_features f JOIN transaction t USING (transaction_id)
"""

with get_engine().connect() as conn:
    df = pd.read_sql(QUERY, conn).sort_values("transaction_dt").reset_index(drop=True)

# ---- 1a. Three-way split by time ---------------------------------------------
q60, q75 = df["transaction_dt"].quantile([0.60, 0.75])
dev = df[df.transaction_dt < q60]
val = df[(df.transaction_dt >= q60) & (df.transaction_dt < q75)]
test = df[df.transaction_dt >= q75]
print("SPLIT (by time)")
for name, part in [("development", dev), ("validation", val), ("final test", test)]:
    print(f"  {name:12s} {len(part):>8,} transactions   days {int(part.transaction_dt.min() // 86400):>3}-"
          f"{int(part.transaction_dt.max() // 86400):<3}   fraud rate {part.is_fraud.mean():.2%}")

# ---- 1b. Leakage checks ---------------------------------------------------------
checks = []
checks.append(("Time order: development < validation < final test",
               dev.transaction_dt.max() <= val.transaction_dt.min() <= test.transaction_dt.min(), ""))
hrs = df.hours_since_previous_txn.dropna()
checks.append(("History features use only earlier transactions (hours since previous > 0)",
               (hrs <= 0).sum() == 0, f"{int((hrs <= 0).sum())} violations of {len(hrs):,}"))
bad24 = int((df.txn_count_24h > df.prior_txn_count).sum())
checks.append(("Transactions in prior 24h never exceed prior transaction count", bad24 == 0, f"{bad24} violations"))
checks.append(("Fraud label is not a predictor", "is_fraud" not in FEATURE_SETS["week11_extended"], ""))
X, _ = fraud_design(dev, feature_set="week11_extended")
y = dev.is_fraud.to_numpy()
best = max(((f, max(a, 1 - a)) for f, a in
            ((f, roc_auc_score(y, X[:, j])) for j, f in enumerate(FEATURE_SETS["week11_extended"])
             if X[:, j].std() > 0)), key=lambda t: t[1])
checks.append(("No single predictor separates fraud almost perfectly (AUC < 0.90)", best[1] < 0.90,
               f"strongest single predictor: {FRAUD_FEATURE_LABELS[best[0]]}, AUC {best[1]:.3f}"))

print("\nLEAKAGE CHECKS")
for name, ok, detail in checks:
    print(f"  [{'PASS' if ok else 'FLAG'}] {name}" + (f" — {detail}" if detail else ""))

with open(os.path.join(ROOT, "reports", "week11", "split_and_leakage.json"), "w") as f:
    json.dump({"split": {n: {"rows": len(p), "first_day": int(p.transaction_dt.min() // 86400),
                             "last_day": int(p.transaction_dt.max() // 86400), "fraud_rate": float(p.is_fraud.mean())}
                         for n, p in [("development", dev), ("validation", val), ("final_test", test)]},
               "checks": [{"check": n, "pass": bool(ok), "detail": d} for n, ok, d in checks]}, f, indent=2)
print("\nSaved reports/week11/split_and_leakage.json")
