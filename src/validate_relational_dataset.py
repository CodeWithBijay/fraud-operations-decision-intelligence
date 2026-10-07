from pathlib import Path
import json

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_TRANSACTION_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ieee_cis"
    / "train_transaction.csv"
)

RAW_IDENTITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ieee_cis"
    / "train_identity.csv"
)

FINAL_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "final"
)

CUSTOMER_FILE = (
    FINAL_DIR
    / "customer.csv"
)

ACCOUNT_FILE = (
    FINAL_DIR
    / "account.csv"
)

DEVICE_FILE = (
    FINAL_DIR
    / "device.csv"
)

TRANSACTION_FILE = (
    FINAL_DIR
    / "transaction.csv"
)

IDENTITY_FILE = (
    FINAL_DIR
    / "transaction_identity.csv"
)

LINEAGE_FILE = (
    FINAL_DIR
    / "transaction_entity_lineage.csv"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "relational_validation"
)


# ============================================================
# 2. REQUIRED FILE CHECK
# ============================================================

def check_files():

    required_files = [
        RAW_TRANSACTION_FILE,
        RAW_IDENTITY_FILE,
        CUSTOMER_FILE,
        ACCOUNT_FILE,
        DEVICE_FILE,
        TRANSACTION_FILE,
        IDENTITY_FILE,
        LINEAGE_FILE,
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                "Required file not found:\n"
                f"{file_path}"
            )

    print("All required files found.")


# ============================================================
# 3. LOAD DATA
# ============================================================

def load_data():

    print("\nLoading final relational tables...")

    customer = pd.read_csv(
        CUSTOMER_FILE,
        low_memory=False,
    )

    account = pd.read_csv(
        ACCOUNT_FILE,
        low_memory=False,
    )

    device = pd.read_csv(
        DEVICE_FILE,
        low_memory=False,
    )

    transaction = pd.read_csv(
        TRANSACTION_FILE,
        low_memory=False,
    )

    identity = pd.read_csv(
        IDENTITY_FILE,
        low_memory=False,
    )

    lineage = pd.read_csv(
        LINEAGE_FILE,
        low_memory=False,
    )

    print("\nLoading source fields needed for preservation checks...")

    raw_transaction = pd.read_csv(
        RAW_TRANSACTION_FILE,
        usecols=[
            "TransactionID",
            "TransactionDT",
            "TransactionAmt",
            "isFraud",
        ],
        low_memory=False,
    )

    raw_identity = pd.read_csv(
        RAW_IDENTITY_FILE,
        low_memory=False,
    )

    return {
        "customer": customer,
        "account": account,
        "device": device,
        "transaction": transaction,
        "identity": identity,
        "lineage": lineage,
        "raw_transaction": raw_transaction,
        "raw_identity": raw_identity,
    }


# ============================================================
# 4. RESULT HELPER
# ============================================================

def make_result(
    test_id,
    category,
    description,
    passed,
    observed,
):

    return {
        "test_id": test_id,
        "category": category,
        "description": description,
        "status": (
            "PASS"
            if passed
            else "FAIL"
        ),
        "observed": str(observed),
    }


# ============================================================
# 5. PRIMARY KEY VALIDATION
# ============================================================

def validate_primary_keys(data):

    results = []

    tests = [
        (
            "REL-PK-001",
            data["customer"],
            "CustomerID",
            "Customer",
        ),
        (
            "REL-PK-002",
            data["account"],
            "AccountID",
            "Account",
        ),
        (
            "REL-PK-003",
            data["device"],
            "DeviceID",
            "Device",
        ),
        (
            "REL-PK-004",
            data["transaction"],
            "TransactionID",
            "Transaction",
        ),
        (
            "REL-PK-005",
            data["identity"],
            "TransactionID",
            "TransactionIdentity",
        ),
        (
            "REL-PK-006",
            data["lineage"],
            "TransactionID",
            "TransactionEntityLineage",
        ),
    ]

    for (
        test_id,
        table,
        key,
        table_name,
    ) in tests:

        missing = int(
            table[key]
            .isna()
            .sum()
        )

        duplicates = int(
            table[key]
            .duplicated()
            .sum()
        )

        passed = (
            missing == 0
            and duplicates == 0
        )

        results.append(
            make_result(
                test_id,
                "PRIMARY_KEY",
                (
                    f"{table_name}.{key} "
                    "is unique and non-null."
                ),
                passed,
                (
                    f"missing={missing}; "
                    f"duplicates={duplicates}"
                ),
            )
        )

    return results


# ============================================================
# 6. FOREIGN KEY HELPER
# ============================================================

def count_orphans(
    child,
    child_column,
    parent,
    parent_column,
    nullable=False,
):

    child_values = (
        child[child_column]
    )

    if nullable:

        child_values = (
            child_values
            .dropna()
        )

    parent_values = set(
        parent[parent_column]
        .dropna()
    )

    orphan_count = int(
        (
            ~child_values
            .isin(parent_values)
        ).sum()
    )

    return orphan_count


# ============================================================
# 7. FOREIGN KEY VALIDATION
# ============================================================

def validate_foreign_keys(data):

    results = []

    checks = [
        (
            "REL-FK-001",
            data["account"],
            "CustomerID",
            data["customer"],
            "CustomerID",
            False,
            (
                "Every Account.CustomerID references "
                "an existing Customer."
            ),
        ),
        (
            "REL-FK-002",
            data["device"],
            "CustomerID",
            data["customer"],
            "CustomerID",
            False,
            (
                "Every Device.CustomerID references "
                "an existing Customer."
            ),
        ),
        (
            "REL-FK-003",
            data["transaction"],
            "CustomerID",
            data["customer"],
            "CustomerID",
            False,
            (
                "Every Transaction.CustomerID references "
                "an existing Customer."
            ),
        ),
        (
            "REL-FK-004",
            data["transaction"],
            "AccountID",
            data["account"],
            "AccountID",
            False,
            (
                "Every Transaction.AccountID references "
                "an existing Account."
            ),
        ),
        (
            "REL-FK-005",
            data["transaction"],
            "DeviceID",
            data["device"],
            "DeviceID",
            True,
            (
                "Every non-null Transaction.DeviceID "
                "references an existing Device."
            ),
        ),
        (
            "REL-FK-006",
            data["identity"],
            "TransactionID",
            data["transaction"],
            "TransactionID",
            False,
            (
                "Every identity record references "
                "an existing Transaction."
            ),
        ),
        (
            "REL-FK-007",
            data["lineage"],
            "TransactionID",
            data["transaction"],
            "TransactionID",
            False,
            (
                "Every lineage record references "
                "an existing Transaction."
            ),
        ),
    ]

    for (
        test_id,
        child,
        child_column,
        parent,
        parent_column,
        nullable,
        description,
    ) in checks:

        orphan_count = count_orphans(
            child,
            child_column,
            parent,
            parent_column,
            nullable,
        )

        results.append(
            make_result(
                test_id,
                "FOREIGN_KEY",
                description,
                orphan_count == 0,
                (
                    "orphan_records="
                    f"{orphan_count}"
                ),
            )
        )

    return results


# ============================================================
# 8. CUSTOMER-ACCOUNT OWNERSHIP
# ============================================================

def validate_account_ownership(data):

    transaction = data[
        "transaction"
    ]

    account = data[
        "account"
    ]

    comparison = transaction[
        [
            "TransactionID",
            "CustomerID",
            "AccountID",
        ]
    ].merge(
        account[
            [
                "AccountID",
                "CustomerID",
            ]
        ],
        on="AccountID",
        how="left",
        suffixes=(
            "_transaction",
            "_account",
        ),
        validate="many_to_one",
    )

    mismatches = int(
        (
            comparison[
                "CustomerID_transaction"
            ]
            != comparison[
                "CustomerID_account"
            ]
        ).sum()
    )

    return [
        make_result(
            "REL-OWN-001",
            "OWNERSHIP",
            (
                "Transaction CustomerID agrees "
                "with Account owner CustomerID."
            ),
            mismatches == 0,
            (
                "customer_account_mismatches="
                f"{mismatches}"
            ),
        )
    ]


# ============================================================
# 9. CUSTOMER-DEVICE OWNERSHIP
# ============================================================

def validate_device_ownership(data):

    transaction = data[
        "transaction"
    ]

    device = data[
        "device"
    ]

    with_device = transaction.loc[
        transaction[
            "DeviceID"
        ].notna(),
        [
            "TransactionID",
            "CustomerID",
            "DeviceID",
        ],
    ]

    comparison = with_device.merge(
        device[
            [
                "DeviceID",
                "CustomerID",
            ]
        ],
        on="DeviceID",
        how="left",
        suffixes=(
            "_transaction",
            "_device",
        ),
        validate="many_to_one",
    )

    mismatches = int(
        (
            comparison[
                "CustomerID_transaction"
            ]
            != comparison[
                "CustomerID_device"
            ]
        ).sum()
    )

    return [
        make_result(
            "REL-OWN-002",
            "OWNERSHIP",
            (
                "Transaction CustomerID agrees "
                "with Device owner CustomerID."
            ),
            mismatches == 0,
            (
                "customer_device_mismatches="
                f"{mismatches}"
            ),
        )
    ]


# ============================================================
# 10. SOURCE TRANSACTION PRESERVATION
# ============================================================

def validate_transaction_source_preservation(
    data,
):

    results = []

    raw = data[
        "raw_transaction"
    ]

    final = data[
        "transaction"
    ]

    comparison = raw.merge(
        final[
            [
                "TransactionID",
                "TransactionDT",
                "TransactionAmt",
                "isFraud",
            ]
        ],
        on="TransactionID",
        how="outer",
        suffixes=(
            "_source",
            "_final",
        ),
        indicator=True,
    )

    unmatched = int(
        (
            comparison[
                "_merge"
            ]
            != "both"
        ).sum()
    )

    results.append(
        make_result(
            "REL-SRC-001",
            "SOURCE_PRESERVATION",
            (
                "Every original TransactionID "
                "is preserved."
            ),
            unmatched == 0,
            (
                "unmatched_transaction_ids="
                f"{unmatched}"
            ),
        )
    )

    matched = comparison.loc[
        comparison[
            "_merge"
        ] == "both"
    ].copy()

    fields = [
        "TransactionDT",
        "TransactionAmt",
        "isFraud",
    ]

    for index, field in enumerate(
        fields,
        start=2,
    ):

        source_values = matched[
            f"{field}_source"
        ]

        final_values = matched[
            f"{field}_final"
        ]

        both_missing = (
            source_values.isna()
            & final_values.isna()
        )

        equal_values = (
            source_values
            == final_values
        )

        mismatches = int(
            (
                ~(
                    both_missing
                    | equal_values
                )
            ).sum()
        )

        results.append(
            make_result(
                f"REL-SRC-00{index}",
                "SOURCE_PRESERVATION",
                (
                    f"Original {field} values "
                    "are preserved."
                ),
                mismatches == 0,
                (
                    f"changed_{field}="
                    f"{mismatches}"
                ),
            )
        )

    return results


# ============================================================
# 11. IDENTITY SOURCE PRESERVATION
# ============================================================

def normalize_for_compare(series):
    """
    Normalize values for source-preservation comparison.

    Missing values receive the same explicit marker.
    """

    return (
        series
        .fillna("__MISSING__")
        .astype(str)
    )


def validate_identity_preservation(data):

    results = []

    raw_identity = data[
        "raw_identity"
    ]

    final_identity = data[
        "identity"
    ]

    results.append(
        make_result(
            "REL-ID-001",
            "IDENTITY",
            (
                "Final identity row count matches "
                "the original identity row count."
            ),
            (
                len(raw_identity)
                == len(final_identity)
            ),
            (
                f"source={len(raw_identity)}; "
                f"final={len(final_identity)}"
            ),
        )
    )

    source_ids = set(
        raw_identity[
            "TransactionID"
        ]
    )

    final_ids = set(
        final_identity[
            "TransactionID"
        ]
    )

    missing_ids = len(
        source_ids
        - final_ids
    )

    extra_ids = len(
        final_ids
        - source_ids
    )

    results.append(
        make_result(
            "REL-ID-002",
            "IDENTITY",
            (
                "Identity TransactionID population "
                "is preserved."
            ),
            (
                missing_ids == 0
                and extra_ids == 0
            ),
            (
                f"missing={missing_ids}; "
                f"extra={extra_ids}"
            ),
        )
    )

    common_columns = [
        column
        for column
        in raw_identity.columns
        if column
        in final_identity.columns
    ]

    comparison = raw_identity[
        common_columns
    ].merge(
        final_identity[
            common_columns
        ],
        on="TransactionID",
        how="inner",
        suffixes=(
            "_source",
            "_final",
        ),
        validate="one_to_one",
    )

    changed_cells = 0

    for column in common_columns:

        if column == "TransactionID":
            continue

        source_values = normalize_for_compare(
            comparison[
                f"{column}_source"
            ]
        )

        final_values = normalize_for_compare(
            comparison[
                f"{column}_final"
            ]
        )

        changed_cells += int(
            (
                source_values
                != final_values
            ).sum()
        )

    results.append(
        make_result(
            "REL-ID-003",
            "IDENTITY",
            (
                "Original identity source values "
                "are preserved."
            ),
            changed_cells == 0,
            (
                "changed_identity_cells="
                f"{changed_cells}"
            ),
        )
    )

    return results


# ============================================================
# 12. LINEAGE CONSISTENCY
# ============================================================

def validate_lineage_consistency(data):

    results = []

    transaction = data[
        "transaction"
    ]

    lineage = data[
        "lineage"
    ]

    comparison = transaction[
        [
            "TransactionID",
            "CustomerID",
            "AccountID",
            "DeviceID",
        ]
    ].merge(
        lineage[
            [
                "TransactionID",
                "CustomerID",
                "AccountID",
                "DeviceID",
            ]
        ],
        on="TransactionID",
        how="outer",
        suffixes=(
            "_transaction",
            "_lineage",
        ),
        indicator=True,
        validate="one_to_one",
    )

    unmatched = int(
        (
            comparison[
                "_merge"
            ]
            != "both"
        ).sum()
    )

    results.append(
        make_result(
            "REL-LIN-001",
            "LINEAGE",
            (
                "Every transaction has exactly one "
                "matching lineage record."
            ),
            unmatched == 0,
            (
                "unmatched_lineage_records="
                f"{unmatched}"
            ),
        )
    )

    matched = comparison.loc[
        comparison[
            "_merge"
        ] == "both"
    ].copy()

    # CustomerID
    customer_mismatch = int(
        (
            matched[
                "CustomerID_transaction"
            ]
            != matched[
                "CustomerID_lineage"
            ]
        ).sum()
    )

    results.append(
        make_result(
            "REL-LIN-002",
            "LINEAGE",
            (
                "Transaction and lineage CustomerID "
                "values agree."
            ),
            customer_mismatch == 0,
            (
                "customer_id_mismatches="
                f"{customer_mismatch}"
            ),
        )
    )

    # AccountID
    account_mismatch = int(
        (
            matched[
                "AccountID_transaction"
            ]
            != matched[
                "AccountID_lineage"
            ]
        ).sum()
    )

    results.append(
        make_result(
            "REL-LIN-003",
            "LINEAGE",
            (
                "Transaction and lineage AccountID "
                "values agree."
            ),
            account_mismatch == 0,
            (
                "account_id_mismatches="
                f"{account_mismatch}"
            ),
        )
    )

    # DeviceID including NULL equality
    transaction_device = (
        matched[
            "DeviceID_transaction"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    lineage_device = (
        matched[
            "DeviceID_lineage"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    device_mismatch = int(
        (
            transaction_device
            != lineage_device
        ).sum()
    )

    results.append(
        make_result(
            "REL-LIN-004",
            "LINEAGE",
            (
                "Transaction and lineage DeviceID "
                "values agree including NULL values."
            ),
            device_mismatch == 0,
            (
                "device_id_mismatches="
                f"{device_mismatch}"
            ),
        )
    )

    return results


# ============================================================
# 13. ENTITY POPULATION CONSISTENCY
# ============================================================

def validate_entity_population(data):

    results = []

    transaction = data[
        "transaction"
    ]

    customer = data[
        "customer"
    ]

    account = data[
        "account"
    ]

    device = data[
        "device"
    ]

    transaction_customers = int(
        transaction[
            "CustomerID"
        ]
        .nunique()
    )

    customer_rows = len(
        customer
    )

    results.append(
        make_result(
            "REL-POP-001",
            "POPULATION",
            (
                "Customer table population equals "
                "distinct CustomerIDs in transactions."
            ),
            (
                transaction_customers
                == customer_rows
            ),
            (
                f"transaction_distinct="
                f"{transaction_customers}; "
                f"customer_rows="
                f"{customer_rows}"
            ),
        )
    )

    transaction_accounts = int(
        transaction[
            "AccountID"
        ]
        .nunique()
    )

    account_rows = len(
        account
    )

    results.append(
        make_result(
            "REL-POP-002",
            "POPULATION",
            (
                "Account table population equals "
                "distinct AccountIDs in transactions."
            ),
            (
                transaction_accounts
                == account_rows
            ),
            (
                f"transaction_distinct="
                f"{transaction_accounts}; "
                f"account_rows="
                f"{account_rows}"
            ),
        )
    )

    transaction_devices = int(
        transaction[
            "DeviceID"
        ]
        .nunique(
            dropna=True
        )
    )

    device_rows = len(
        device
    )

    results.append(
        make_result(
            "REL-POP-003",
            "POPULATION",
            (
                "Device table population equals "
                "distinct non-null DeviceIDs in transactions."
            ),
            (
                transaction_devices
                == device_rows
            ),
            (
                f"transaction_distinct="
                f"{transaction_devices}; "
                f"device_rows="
                f"{device_rows}"
            ),
        )
    )

    return results


# ============================================================
# 14. LINEAGE METHOD COMPLETENESS
# ============================================================

def validate_lineage_methods(data):

    lineage = data[
        "lineage"
    ]

    results = []

    required_fields = [
        "CustomerID_method",
        "AccountID_method",
        "DeviceID_method",
    ]

    for index, field in enumerate(
        required_fields,
        start=1,
    ):

        missing = int(
            lineage[field]
            .isna()
            .sum()
        )

        results.append(
            make_result(
                f"REL-METHOD-00{index}",
                "LINEAGE",
                (
                    f"Every lineage record contains "
                    f"{field}."
                ),
                missing == 0,
                (
                    f"missing_{field}="
                    f"{missing}"
                ),
            )
        )

    return results


# ============================================================
# 15. CREATE SUMMARY
# ============================================================

def create_summary(
    data,
    results,
):

    passed = sum(
        result[
            "status"
        ] == "PASS"
        for result
        in results
    )

    failed = sum(
        result[
            "status"
        ] == "FAIL"
        for result
        in results
    )

    transaction = data[
        "transaction"
    ]

    return {
        "customer_rows": int(
            len(
                data[
                    "customer"
                ]
            )
        ),

        "account_rows": int(
            len(
                data[
                    "account"
                ]
            )
        ),

        "device_rows": int(
            len(
                data[
                    "device"
                ]
            )
        ),

        "transaction_rows": int(
            len(
                transaction
            )
        ),

        "transaction_identity_rows": int(
            len(
                data[
                    "identity"
                ]
            )
        ),

        "lineage_rows": int(
            len(
                data[
                    "lineage"
                ]
            )
        ),

        "transactions_missing_customer_id": int(
            transaction[
                "CustomerID"
            ]
            .isna()
            .sum()
        ),

        "transactions_missing_account_id": int(
            transaction[
                "AccountID"
            ]
            .isna()
            .sum()
        ),

        "transactions_missing_device_id": int(
            transaction[
                "DeviceID"
            ]
            .isna()
            .sum()
        ),

        "tests_run": int(
            len(
                results
            )
        ),

        "tests_passed": int(
            passed
        ),

        "tests_failed": int(
            failed
        ),

        "overall_status": (
            "PASS"
            if failed == 0
            else "FAIL"
        ),
    }


# ============================================================
# 16. SAVE RESULTS
# ============================================================

def save_results(
    results,
    summary,
):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_file = (
        REPORT_DIR
        / "relational_validation_results.csv"
    )

    summary_file = (
        REPORT_DIR
        / "relational_validation_summary.json"
    )

    pd.DataFrame(
        results
    ).to_csv(
        results_file,
        index=False,
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
        "\nValidation results saved to:"
    )

    print(
        results_file
    )

    print(
        "\nValidation summary saved to:"
    )

    print(
        summary_file
    )


# ============================================================
# 17. PRINT RESULTS
# ============================================================

def print_results(
    results,
    summary,
):

    print("\n" + "=" * 78)

    print(
        "FINAL RELATIONAL DATASET VALIDATION"
    )

    print("=" * 78)

    for result in results:

        print(
            f"\n{result['test_id']} "
            f"[{result['status']}]"
        )

        print(
            result[
                "description"
            ]
        )

        print(
            "Observed: "
            f"{result['observed']}"
        )

    print("\n" + "=" * 78)

    print(
        f"Tests run: "
        f"{summary['tests_run']}"
    )

    print(
        f"Passed: "
        f"{summary['tests_passed']}"
    )

    print(
        f"Failed: "
        f"{summary['tests_failed']}"
    )

    print(
        "Overall status: "
        f"{summary['overall_status']}"
    )


# ============================================================
# 18. MAIN
# ============================================================

def main():

    print("=" * 78)

    print(
        "VERSION 1 RELATIONAL DATASET VALIDATION"
    )

    print("=" * 78)

    print(
        "\nThis script validates the six final "
        "relational output tables as one system."
    )

    print(
        "It does not generate or modify entity IDs."
    )

    check_files()

    data = load_data()

    results = []

    results.extend(
        validate_primary_keys(
            data
        )
    )

    results.extend(
        validate_foreign_keys(
            data
        )
    )

    results.extend(
        validate_account_ownership(
            data
        )
    )

    results.extend(
        validate_device_ownership(
            data
        )
    )

    results.extend(
        validate_transaction_source_preservation(
            data
        )
    )

    results.extend(
        validate_identity_preservation(
            data
        )
    )

    results.extend(
        validate_lineage_consistency(
            data
        )
    )

    results.extend(
        validate_entity_population(
            data
        )
    )

    results.extend(
        validate_lineage_methods(
            data
        )
    )

    summary = create_summary(
        data,
        results,
    )

    save_results(
        results,
        summary,
    )

    print_results(
        results,
        summary,
    )

    print("\n" + "=" * 78)

    if (
        summary[
            "overall_status"
        ] == "PASS"
    ):

        print(
            "VERSION 1 RELATIONAL VALIDATION PASSED"
        )

        print(
            "\nThe generated relational dataset is "
            "internally consistent with the documented "
            "structural and source-preservation rules."
        )

    else:

        print(
            "VERSION 1 RELATIONAL VALIDATION FAILED"
        )

        print(
            "\nDo not move to PostgreSQL until all "
            "failed checks are investigated."
        )

    print("=" * 78)


if __name__ == "__main__":
    main()