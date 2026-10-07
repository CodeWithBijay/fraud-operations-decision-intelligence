from pathlib import Path
import json

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

# Find the main project directory automatically.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Location of the original IEEE-CIS files.
TRANSACTION_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ieee_cis"
    / "train_transaction.csv"
)

IDENTITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ieee_cis"
    / "train_identity.csv"
)

# Folder where audit results will be saved.
OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "input_audit"
)


# ============================================================
# 2. CHECK INPUT FILES
# ============================================================

def check_input_files():
    """
    Make sure both required IEEE-CIS files exist
    before beginning the audit.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            f"Transaction file not found:\n{TRANSACTION_FILE}"
        )

    if not IDENTITY_FILE.exists():
        raise FileNotFoundError(
            f"Identity file not found:\n{IDENTITY_FILE}"
        )

    print("Input files found successfully.")


# ============================================================
# 3. LOAD DATA
# ============================================================

def load_data():
    """
    Read the original IEEE-CIS CSV files.

    This function only reads the files.
    It does not modify or overwrite them.
    """

    print("\nLoading transaction data...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        low_memory=False
    )

    print("Transaction data loaded.")

    print("\nLoading identity data...")

    identity = pd.read_csv(
        IDENTITY_FILE,
        low_memory=False
    )

    print("Identity data loaded.")

    return transactions, identity


# ============================================================
# 4. DATASET STRUCTURE
# ============================================================

def audit_dataset_structure(transactions, identity):
    """
    Record the number of rows and columns
    in each source dataset.
    """

    return {
        "transaction_rows": int(len(transactions)),
        "transaction_columns": int(len(transactions.columns)),
        "identity_rows": int(len(identity)),
        "identity_columns": int(len(identity.columns)),
    }


# ============================================================
# 5. TRANSACTION ID AUDIT
# ============================================================

def audit_transaction_ids(transactions, identity):
    """
    Check TransactionID integrity and the relationship
    between the transaction and identity files.
    """

    transaction_missing_ids = int(
        transactions["TransactionID"].isna().sum()
    )

    transaction_duplicate_ids = int(
        transactions["TransactionID"].duplicated().sum()
    )

    identity_missing_ids = int(
        identity["TransactionID"].isna().sum()
    )

    identity_duplicate_ids = int(
        identity["TransactionID"].duplicated().sum()
    )

    # Check which transactions have a corresponding identity record.
    identity_ids = set(
        identity["TransactionID"]
        .dropna()
        .tolist()
    )

    transactions_with_identity = int(
        transactions["TransactionID"]
        .isin(identity_ids)
        .sum()
    )

    transactions_without_identity = int(
        len(transactions) - transactions_with_identity
    )

    identity_coverage_percent = (
        transactions_with_identity
        / len(transactions)
        * 100
    )

    # Check whether identity records reference transactions
    # that do not exist in the transaction file.
    transaction_ids = set(
        transactions["TransactionID"]
        .dropna()
        .tolist()
    )

    orphan_identity_records = int(
        (~identity["TransactionID"]
         .isin(transaction_ids))
        .sum()
    )

    return {
        "transaction_missing_ids": transaction_missing_ids,
        "transaction_duplicate_ids": transaction_duplicate_ids,

        "identity_missing_ids": identity_missing_ids,
        "identity_duplicate_ids": identity_duplicate_ids,

        "transactions_with_identity": transactions_with_identity,
        "transactions_without_identity": transactions_without_identity,

        "identity_coverage_percent": round(
            identity_coverage_percent,
            4
        ),

        "orphan_identity_records": orphan_identity_records,
    }


# ============================================================
# 6. FRAUD OUTCOME AUDIT
# ============================================================

def audit_fraud(transactions):
    """
    Measure the observed fraud outcome in the source data.
    """

    fraud_count = int(
        (transactions["isFraud"] == 1).sum()
    )

    nonfraud_count = int(
        (transactions["isFraud"] == 0).sum()
    )

    missing_fraud_labels = int(
        transactions["isFraud"].isna().sum()
    )

    valid_labels = fraud_count + nonfraud_count

    if valid_labels > 0:
        fraud_rate = (
            fraud_count
            / valid_labels
            * 100
        )
    else:
        fraud_rate = 0

    return {
        "fraud_transactions": fraud_count,
        "nonfraud_transactions": nonfraud_count,
        "missing_fraud_labels": missing_fraud_labels,
        "fraud_rate_percent": round(
            fraud_rate,
            4
        ),
    }


# ============================================================
# 7. TRANSACTION AMOUNT AUDIT
# ============================================================

def audit_transaction_amount(transactions):
    """
    Describe the observed TransactionAmt distribution.
    """

    amount = transactions["TransactionAmt"]

    return {
        "missing_values": int(amount.isna().sum()),

        "minimum": round(float(amount.min()), 4),
        "maximum": round(float(amount.max()), 4),

        "mean": round(float(amount.mean()), 4),
        "median": round(float(amount.median()), 4),

        "standard_deviation": round(
            float(amount.std()),
            4
        ),

        "percentile_25": round(
            float(amount.quantile(0.25)),
            4
        ),

        "percentile_75": round(
            float(amount.quantile(0.75)),
            4
        ),

        "percentile_95": round(
            float(amount.quantile(0.95)),
            4
        ),

        "percentile_99": round(
            float(amount.quantile(0.99)),
            4
        ),
    }


# ============================================================
# 8. TRANSACTION TIME AUDIT
# ============================================================

def audit_transaction_time(transactions):
    """
    Inspect TransactionDT without pretending that it
    represents an actual calendar date.
    """

    transaction_time = transactions["TransactionDT"]

    return {
        "missing_values": int(
            transaction_time.isna().sum()
        ),

        "minimum_transaction_dt": float(
            transaction_time.min()
        ),

        "maximum_transaction_dt": float(
            transaction_time.max()
        ),

        "original_order_is_chronological": bool(
            transaction_time
            .dropna()
            .is_monotonic_increasing
        ),
    }


# ============================================================
# 9. MISSINGNESS AUDIT
# ============================================================

def calculate_missingness(df, dataset_name):
    """
    Measure missing values for every source column.
    """

    missing_count = df.isna().sum()

    missing_percent = (
        missing_count
        / len(df)
        * 100
    )

    results = pd.DataFrame({
        "dataset": dataset_name,
        "column": df.columns,
        "data_type": df.dtypes.astype(str).values,
        "missing_count": missing_count.values,
        "missing_percent": missing_percent.values,
    })

    results["missing_percent"] = (
        results["missing_percent"]
        .round(4)
    )

    return results.sort_values(
        by="missing_percent",
        ascending=False
    )


# ============================================================
# 10. SAVE AUDIT RESULTS
# ============================================================

def save_results(
    summary,
    transaction_missingness,
    identity_missingness
):
    """
    Save the audit results without changing
    the original IEEE-CIS files.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Main summary.
    summary_file = (
        OUTPUT_DIR
        / "input_audit.json"
    )

    with summary_file.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            summary,
            file,
            indent=4
        )

    # Transaction missingness.
    transaction_missingness.to_csv(
        OUTPUT_DIR
        / "transaction_missingness.csv",
        index=False
    )

    # Identity missingness.
    identity_missingness.to_csv(
        OUTPUT_DIR
        / "identity_missingness.csv",
        index=False
    )

    print("\nAudit results saved to:")
    print(OUTPUT_DIR)


# ============================================================
# 11. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)
    print("IEEE-CIS INPUT DATA AUDIT")
    print("=" * 60)

    check_input_files()

    transactions, identity = load_data()

    print("\nAuditing dataset structure...")
    structure = audit_dataset_structure(
        transactions,
        identity
    )

    print("Auditing TransactionID...")
    transaction_ids = audit_transaction_ids(
        transactions,
        identity
    )

    print("Auditing fraud outcome...")
    fraud = audit_fraud(
        transactions
    )

    print("Auditing TransactionAmt...")
    transaction_amount = audit_transaction_amount(
        transactions
    )

    print("Auditing TransactionDT...")
    transaction_time = audit_transaction_time(
        transactions
    )

    print("Calculating transaction missingness...")
    transaction_missingness = calculate_missingness(
        transactions,
        "train_transaction"
    )

    print("Calculating identity missingness...")
    identity_missingness = calculate_missingness(
        identity,
        "train_identity"
    )

    summary = {
        "dataset_structure": structure,
        "transaction_id_audit": transaction_ids,
        "fraud_outcome": fraud,
        "transaction_amount": transaction_amount,
        "transaction_time": transaction_time,
    }

    save_results(
        summary,
        transaction_missingness,
        identity_missingness
    )

    print("\n" + "=" * 60)
    print("INPUT AUDIT COMPLETED")
    print("=" * 60)

    print(
        "\nNo synthetic data were generated."
    )

    print(
        "The original IEEE-CIS files were not modified."
    )


if __name__ == "__main__":
    main()