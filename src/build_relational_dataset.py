from pathlib import Path
import json

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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

CUSTOMER_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "customer"
    / "transaction_customer_mapping.csv"
)

ACCOUNT_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "account"
    / "transaction_account_mapping.csv"
)

DEVICE_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "device"
    / "transaction_device_mapping.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "final"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "relational_build"
)


# ============================================================
# 2. CHECK REQUIRED FILES
# ============================================================

def check_files():
    """
    Confirm that all source and validated mapping files exist.
    """

    required_files = [
        TRANSACTION_FILE,
        IDENTITY_FILE,
        CUSTOMER_MAPPING_FILE,
        ACCOUNT_MAPPING_FILE,
        DEVICE_MAPPING_FILE,
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                "Required file not found:\n"
                f"{file_path}"
            )

    print("Required files found.")


# ============================================================
# 3. LOAD DATA
# ============================================================

def load_data():
    """
    Load the original source data and generated mappings.

    The original source files are read only.
    """

    print("\nLoading IEEE-CIS transaction data...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        low_memory=False,
    )

    print(
        f"Transaction rows: {len(transactions):,}"
    )

    print("\nLoading IEEE-CIS identity data...")

    identity = pd.read_csv(
        IDENTITY_FILE,
        low_memory=False,
    )

    print(
        f"Identity rows: {len(identity):,}"
    )

    print("\nLoading CustomerID mapping...")

    customer_mapping = pd.read_csv(
        CUSTOMER_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "CustomerID",
            "CustomerID_method",
        ],
        low_memory=False,
    )

    print("\nLoading AccountID mapping...")

    account_mapping = pd.read_csv(
        ACCOUNT_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "AccountID",
            "AccountID_method",
        ],
        low_memory=False,
    )

    print("\nLoading DeviceID mapping...")

    device_mapping = pd.read_csv(
        DEVICE_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "DeviceID",
            "DeviceID_method",
        ],
        low_memory=False,
    )

    return (
        transactions,
        identity,
        customer_mapping,
        account_mapping,
        device_mapping,
    )


# ============================================================
# 4. BUILD ENTITY LINEAGE
# ============================================================

def build_lineage(
    transactions,
    customer_mapping,
    account_mapping,
    device_mapping,
):
    """
    Build transaction-level lineage for all generated
    analytical entity relationships.
    """

    lineage = transactions[
        [
            "TransactionID",
        ]
    ].copy()

    lineage = lineage.merge(
        customer_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    lineage = lineage.merge(
        account_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    lineage = lineage.merge(
        device_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    return lineage


# ============================================================
# 5. BUILD CUSTOMER TABLE
# ============================================================

def build_customer_table(lineage):
    """
    Produce one row per analytical CustomerID.
    """

    customer = (
        lineage[
            [
                "CustomerID",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by="CustomerID"
        )
        .reset_index(
            drop=True
        )
    )

    return customer


# ============================================================
# 6. BUILD ACCOUNT TABLE
# ============================================================

def build_account_table(lineage):
    """
    Produce one row per AccountID with its parent CustomerID.
    """

    account = (
        lineage[
            [
                "AccountID",
                "CustomerID",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by=[
                "CustomerID",
                "AccountID",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return account


# ============================================================
# 7. BUILD DEVICE TABLE
# ============================================================

def build_device_table(lineage):
    """
    Produce one row per non-null DeviceID with its
    parent CustomerID.

    NULL DeviceID does not create a device entity.
    """

    device = (
        lineage.loc[
            lineage[
                "DeviceID"
            ].notna(),
            [
                "DeviceID",
                "CustomerID",
            ],
        ]
        .drop_duplicates()
        .sort_values(
            by=[
                "CustomerID",
                "DeviceID",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return device


# ============================================================
# 8. BUILD TRANSACTION TABLE
# ============================================================

def build_transaction_table(
    transactions,
    lineage,
):
    """
    Add analytical foreign keys to the original IEEE-CIS
    transaction records.

    All original transaction columns are preserved.
    """

    transaction = transactions.merge(
        lineage[
            [
                "TransactionID",
                "CustomerID",
                "AccountID",
                "DeviceID",
            ]
        ],
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    # Move analytical relationship fields near TransactionID
    # for easier reading.

    original_columns = list(
        transactions.columns
    )

    relationship_columns = [
        "CustomerID",
        "AccountID",
        "DeviceID",
    ]

    ordered_columns = [
        "TransactionID",
        *relationship_columns,
        *[
            column
            for column in original_columns
            if column
            != "TransactionID"
        ],
    ]

    transaction = transaction[
        ordered_columns
    ]

    return transaction


# ============================================================
# 9. BUILD TRANSACTION IDENTITY TABLE
# ============================================================

def build_transaction_identity_table(identity):
    """
    Preserve the original IEEE-CIS identity table.

    No synthetic identity rows are created.
    """

    return identity.copy()


# ============================================================
# 10. BUILD SUMMARY
# ============================================================

def create_build_summary(
    customer,
    account,
    device,
    transaction,
    transaction_identity,
    lineage,
):
    """
    Produce compact summary information for review.
    """

    return {
        "customer_rows": int(
            len(customer)
        ),

        "account_rows": int(
            len(account)
        ),

        "device_rows": int(
            len(device)
        ),

        "transaction_rows": int(
            len(transaction)
        ),

        "transaction_identity_rows": int(
            len(
                transaction_identity
            )
        ),

        "lineage_rows": int(
            len(lineage)
        ),

        "transaction_missing_customer_id": int(
            transaction[
                "CustomerID"
            ]
            .isna()
            .sum()
        ),

        "transaction_missing_account_id": int(
            transaction[
                "AccountID"
            ]
            .isna()
            .sum()
        ),

        "transaction_missing_device_id": int(
            transaction[
                "DeviceID"
            ]
            .isna()
            .sum()
        ),

        "distinct_customers_in_transaction": int(
            transaction[
                "CustomerID"
            ]
            .nunique()
        ),

        "distinct_accounts_in_transaction": int(
            transaction[
                "AccountID"
            ]
            .nunique()
        ),

        "distinct_devices_in_transaction": int(
            transaction[
                "DeviceID"
            ]
            .nunique(
                dropna=True
            )
        ),

        "customer_id_method_counts": {
            str(key): int(value)
            for key, value
            in lineage[
                "CustomerID_method"
            ]
            .value_counts(
                dropna=False
            )
            .to_dict()
            .items()
        },

        "account_id_method_counts": {
            str(key): int(value)
            for key, value
            in lineage[
                "AccountID_method"
            ]
            .value_counts(
                dropna=False
            )
            .to_dict()
            .items()
        },

        "device_id_method_counts": {
            str(key): int(value)
            for key, value
            in lineage[
                "DeviceID_method"
            ]
            .value_counts(
                dropna=False
            )
            .to_dict()
            .items()
        },
    }


# ============================================================
# 11. BUILD-STAGE SAFETY CHECKS
# ============================================================

def run_build_checks(
    transactions,
    identity,
    customer,
    account,
    device,
    transaction,
    transaction_identity,
    lineage,
):
    """
    Immediate integration checks.

    These are NOT the final relational validation phase.
    """

    print(
        "\nRunning relational build safety checks..."
    )

    # Original transaction population preserved.
    assert (
        len(transaction)
        == len(transactions)
    ), (
        "Transaction row count changed."
    )

    # Original identity population preserved.
    assert (
        len(
            transaction_identity
        )
        == len(identity)
    ), (
        "Identity row count changed."
    )

    # One lineage record per transaction.
    assert (
        len(lineage)
        == len(transactions)
    ), (
        "Lineage row count does not match transactions."
    )

    # TransactionID remains unique.
    assert (
        transaction[
            "TransactionID"
        ].is_unique
    ), (
        "TransactionID is not unique."
    )

    # CustomerID required.
    assert (
        transaction[
            "CustomerID"
        ]
        .notna()
        .all()
    ), (
        "Missing CustomerID found."
    )

    # AccountID required.
    assert (
        transaction[
            "AccountID"
        ]
        .notna()
        .all()
    ), (
        "Missing AccountID found."
    )

    # DeviceID is intentionally nullable.

    # Entity IDs unique.
    assert (
        customer[
            "CustomerID"
        ].is_unique
    )

    assert (
        account[
            "AccountID"
        ].is_unique
    )

    assert (
        device[
            "DeviceID"
        ].is_unique
    )

    # Every account belongs to one customer.
    account_customer_counts = (
        account.groupby(
            "AccountID"
        )[
            "CustomerID"
        ]
        .nunique()
    )

    assert (
        account_customer_counts
        .max()
        <= 1
    )

    # Every device belongs to one customer.
    if len(device) > 0:

        device_customer_counts = (
            device.groupby(
                "DeviceID"
            )[
                "CustomerID"
            ]
            .nunique()
        )

        assert (
            device_customer_counts
            .max()
            <= 1
        )

    print(
        "Relational build safety checks passed."
    )


# ============================================================
# 12. SAVE FINAL TABLES
# ============================================================

def save_final_tables(
    customer,
    account,
    device,
    transaction,
    transaction_identity,
    lineage,
    summary,
):
    """
    Save the six final Version 1 relational tables locally.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\nWriting customer.csv..."
    )

    customer.to_csv(
        OUTPUT_DIR
        / "customer.csv",
        index=False,
    )

    print(
        "Writing account.csv..."
    )

    account.to_csv(
        OUTPUT_DIR
        / "account.csv",
        index=False,
    )

    print(
        "Writing device.csv..."
    )

    device.to_csv(
        OUTPUT_DIR
        / "device.csv",
        index=False,
    )

    print(
        "Writing transaction.csv..."
    )

    transaction.to_csv(
        OUTPUT_DIR
        / "transaction.csv",
        index=False,
    )

    print(
        "Writing transaction_identity.csv..."
    )

    transaction_identity.to_csv(
        OUTPUT_DIR
        / "transaction_identity.csv",
        index=False,
    )

    print(
        "Writing transaction_entity_lineage.csv..."
    )

    lineage.to_csv(
        OUTPUT_DIR
        / "transaction_entity_lineage.csv",
        index=False,
    )

    summary_file = (
        REPORT_DIR
        / "relational_build_summary.json"
    )

    with summary_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=4,
        )

    print(
        "\nBuild summary saved to:"
    )

    print(
        summary_file
    )


# ============================================================
# 13. PRINT SUMMARY
# ============================================================

def print_summary(summary):

    print("\n" + "=" * 75)
    print("RELATIONAL DATASET BUILD SUMMARY")
    print("=" * 75)

    print(
        f"Customers: "
        f"{summary['customer_rows']:,}"
    )

    print(
        f"Accounts: "
        f"{summary['account_rows']:,}"
    )

    print(
        f"Devices: "
        f"{summary['device_rows']:,}"
    )

    print(
        f"Transactions: "
        f"{summary['transaction_rows']:,}"
    )

    print(
        "Transaction identity rows: "
        f"{summary['transaction_identity_rows']:,}"
    )

    print(
        f"Lineage rows: "
        f"{summary['lineage_rows']:,}"
    )

    print(
        "\nMissing relationship IDs:"
    )

    print(
        "  CustomerID: "
        f"{summary['transaction_missing_customer_id']:,}"
    )

    print(
        "  AccountID: "
        f"{summary['transaction_missing_account_id']:,}"
    )

    print(
        "  DeviceID: "
        f"{summary['transaction_missing_device_id']:,}"
    )


# ============================================================
# 14. MAIN
# ============================================================

def main():

    print("=" * 75)
    print("BUILD VERSION 1 RELATIONAL DATASET")
    print("=" * 75)

    print(
        "\nThis script assembles previously generated "
        "and validated relationships."
    )

    print(
        "It does not create new CustomerID, "
        "AccountID, or DeviceID values."
    )

    check_files()

    (
        transactions,
        identity,
        customer_mapping,
        account_mapping,
        device_mapping,
    ) = load_data()

    print(
        "\nBuilding transaction entity lineage..."
    )

    lineage = build_lineage(
        transactions,
        customer_mapping,
        account_mapping,
        device_mapping,
    )

    print(
        "Building customer table..."
    )

    customer = build_customer_table(
        lineage
    )

    print(
        "Building account table..."
    )

    account = build_account_table(
        lineage
    )

    print(
        "Building device table..."
    )

    device = build_device_table(
        lineage
    )

    print(
        "Building transaction table..."
    )

    transaction = build_transaction_table(
        transactions,
        lineage,
    )

    print(
        "Building transaction identity table..."
    )

    transaction_identity = (
        build_transaction_identity_table(
            identity
        )
    )

    run_build_checks(
        transactions,
        identity,
        customer,
        account,
        device,
        transaction,
        transaction_identity,
        lineage,
    )

    summary = create_build_summary(
        customer,
        account,
        device,
        transaction,
        transaction_identity,
        lineage,
    )

    save_final_tables(
        customer,
        account,
        device,
        transaction,
        transaction_identity,
        lineage,
        summary,
    )

    print_summary(
        summary
    )

    print("\n" + "=" * 75)
    print("RELATIONAL DATASET BUILD COMPLETED")
    print("=" * 75)

    print(
        "\nNo original IEEE-CIS files were modified."
    )


if __name__ == "__main__":
    main()