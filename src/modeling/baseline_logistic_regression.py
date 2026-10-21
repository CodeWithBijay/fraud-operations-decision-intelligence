import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

df = pd.read_csv("model_dataset_ml.csv")

X = df[
    [
        "hours_since_previous_txn",
        "txn_count_24h",
        "customer_avg_amt_30d",
        "amount_deviation_from_customer_avg",
        "customer_amount_zscore"
    ]
]

y = df["is_fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

model = LogisticRegression(max_iter=1000)

model.fit(X_train, y_train)

predictions = model.predict(X_test)

print(classification_report(y_test, predictions)) 