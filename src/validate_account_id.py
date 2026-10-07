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

ACCOUNT_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "account"
    / "transaction_account_mapping.csv"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "account_id_validation"
)


# ============================================================
# 2. APPROVED ACCOUNT SIGNATURE
# ============================================================

ACCOUNT_COLUMNS = [
    "card1",
    "card2",
    "card3",
    "card5",
]


# ============================================================
# 3. DOCUMENTED ACCOUNTID METHODS
# ============================================================

VALID_METHODS = {
    "PRIMARY",
    "FALLBACK_CARD1_CARD3_CARD5",
    "FALLBACK_CARD1_CARD2_CARD3",
    "FALLBACK_CARD1_CARD3",
    "FALLBACK_CARD1_CARD5",
    "UNRESOLVED_AVAILABLE_SIGNATURE",
}


# ============================================================
# 4. CHECK REQUIRED FILES
# ============================================================

def check_files():

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Source transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    if not ACCOUNT_MAPPING_FILE.exists():
        raise FileNotFoundError(
            "Generated AccountID mapping not found:\n"
            f"{ACCOUNT_MAPPING_FILE}"
        )

    print("Required files found.")


# ============================================================
# 5. LOAD DATA
# ============================================================

def load_data():

    print("\nLoading source transaction fields...")

    source = pd.read_csv(
        TRANSACTION_FILE,
        usecols=[
            "TransactionID",
            "TransactionDT",
            "card1",
            "card2",
            "card3",
            "card5",
        ],
        low_memory=False,
    )

    print("Loading generated AccountID mapping...")

    mapping = pd.read_csv(
        ACCOUNT_MAPPING_FILE,
        low_memory=False,
    )

    print(
        f"Source transactions: {len(source):,}"
    )

    print(
        f"Account mapping rows: {len(mapping):,}"
    )

    return source, mapping


# ============================================================
# 6. VALIDATION RESULT HELPER
# ============================================================

def make_result(
    test_id,
    description,
    passed,
    observed,
):

    return {
        "test_id": test_id,
        "description": description,
        "status": (
            "PASS"
            if passed
            else "FAIL"
        ),
        "observed": observed,
    }


# ============================================================
# 7. BASIC STRUCTURAL VALIDATION
# ============================================================

def validate_structure(
    source,
    mapping,
):

    results = []

    # Row count
    source_rows = len(source)
    mapping_rows = len(mapping)

    results.append(
        make_result(
            "AID-001",
            (
                "Generated AccountID mapping row count "
                "matches source transaction count."
            ),
            source_rows == mapping_rows,
            (
                f"source={source_rows}, "
                f"mapping={mapping_rows}"
            ),
        )
    )

    # TransactionID uniqueness
    duplicate_transactions = int(
        mapping[
            "TransactionID"
        ]
        .duplicated()
        .sum()
    )

    results.append(
        make_result(
            "AID-002",
            (
                "TransactionID is unique in the "
                "AccountID mapping."
            ),
            duplicate_transactions == 0,
            (
                "duplicate_transaction_ids="
                f"{duplicate_transactions}"
            ),
        )
    )

    # Missing CustomerID
    missing_customers = int(
        mapping[
            "CustomerID"
        ]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "AID-003",
            (
                "Every mapped transaction has "
                "a CustomerID."
            ),
            missing_customers == 0,
            (
                "missing_customer_ids="
                f"{missing_customers}"
            ),
        )
    )

    # Missing AccountID
    missing_accounts = int(
        mapping[
            "AccountID"
        ]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "AID-004",
            (
                "Every transaction has an "
                "AccountID."
            ),
            missing_accounts == 0,
            (
                "missing_account_ids="
                f"{missing_accounts}"
            ),
        )
    )

    # Missing method
    missing_methods = int(
        mapping[
            "AccountID_method"
        ]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "AID-005",
            (
                "Every AccountID assignment records "
                "its generation method."
            ),
            missing_methods == 0,
            (
                "missing_account_methods="
                f"{missing_methods}"
            ),
        )
    )

    return results


# ============================================================
# 8. SOURCE PRESERVATION
# ============================================================

def validate_source_preservation(
    source,
    mapping,
):

    results = []

    comparison = source[
        [
            "TransactionID",
            "TransactionDT",
        ]
    ].merge(
        mapping[
            [
                "TransactionID",
                "TransactionDT",
            ]
        ],
        on="TransactionID",
        how="outer",
        suffixes=(
            "_source",
            "_generated",
        ),
        indicator=True,
    )

    unmatched = int(
        (
            comparison["_merge"]
            != "both"
        ).sum()
    )

    results.append(
        make_result(
            "AID-006",
            (
                "Every source TransactionID is "
                "represented in the AccountID mapping."
            ),
            unmatched == 0,
            (
                "unmatched_transaction_ids="
                f"{unmatched}"
            ),
        )
    )

    matched = comparison.loc[
        comparison["_merge"]
        == "both"
    ].copy()

    changed_time = int(
        (
            matched[
                "TransactionDT_source"
            ]
            != matched[
                "TransactionDT_generated"
            ]
        ).sum()
    )

    results.append(
        make_result(
            "AID-007",
            (
                "TransactionDT is preserved in "
                "the AccountID mapping."
            ),
            changed_time == 0,
            (
                "changed_transaction_dt="
                f"{changed_time}"
            ),
        )
    )

    return results


# ============================================================
# 9. METHOD VALIDATION
# ============================================================

def validate_methods(mapping):

    observed_methods = set(
        mapping[
            "AccountID_method"
        ]
        .dropna()
        .unique()
    )

    unexpected_methods = sorted(
        observed_methods
        - VALID_METHODS
    )

    return [
        make_result(
            "AID-008",
            (
                "Only documented AccountID "
                "assignment methods are present."
            ),
            len(
                unexpected_methods
            ) == 0,
            (
                "unexpected_methods="
                f"{unexpected_methods}"
            ),
        )
    ]


# ============================================================
# 10. CUSTOMER-ACCOUNT OWNERSHIP
# ============================================================

def validate_account_ownership(mapping):

    account_customer_counts = (
        mapping.groupby(
            "AccountID"
        )["CustomerID"]
        .nunique()
    )

    multi_customer_accounts = int(
        (
            account_customer_counts > 1
        ).sum()
    )

    return [
        make_result(
            "AID-009",
            (
                "Every AccountID belongs to exactly "
                "one CustomerID."
            ),
            multi_customer_accounts == 0,
            (
                "accounts_linked_to_multiple_customers="
                f"{multi_customer_accounts}"
            ),
        )
    ]


# ============================================================
# 11. PRIMARY ACCOUNT SIGNATURE VALIDATION
# ============================================================

def validate_primary_accounts(
    source,
    mapping,
):

    results = []

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "CustomerID",
                "AccountID",
                "AccountID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
        validate="one_to_one",
    )

    primary = combined.loc[
        combined[
            "AccountID_method"
        ]
        == "PRIMARY"
    ].copy()

    # Make sure primary transactions really have
    # complete signature fields.
    incomplete_primary = int(
        primary[
            ACCOUNT_COLUMNS
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    results.append(
        make_result(
            "AID-010",
            (
                "PRIMARY AccountID assignments contain "
                "all approved source-signature fields."
            ),
            incomplete_primary == 0,
            (
                "incomplete_primary_assignments="
                f"{incomplete_primary}"
            ),
        )
    )

    primary[
        "expected_signature"
    ] = (
        primary[
            ACCOUNT_COLUMNS
        ]
        .astype(str)
        .agg(
            "|".join,
            axis=1,
        )
    )

    primary[
        "customer_account_signature"
    ] = (
        primary[
            "CustomerID"
        ].astype(str)
        + "|"
        + primary[
            "expected_signature"
        ]
    )

    # Same customer/signature should always
    # yield one AccountID.
    signature_account_counts = (
        primary.groupby(
            "customer_account_signature"
        )["AccountID"]
        .nunique()
    )

    inconsistent_signatures = int(
        (
            signature_account_counts > 1
        ).sum()
    )

    results.append(
        make_result(
            "AID-011",
            (
                "Each CustomerID plus primary account "
                "signature maps to exactly one AccountID."
            ),
            inconsistent_signatures == 0,
            (
                "inconsistent_primary_signatures="
                f"{inconsistent_signatures}"
            ),
        )
    )

    # Each PRIMARY AccountID should represent only
    # one customer/signature.
    account_signature_counts = (
        primary.groupby(
            "AccountID"
        )[
            "customer_account_signature"
        ]
        .nunique()
    )

    collisions = int(
        (
            account_signature_counts > 1
        ).sum()
    )

    results.append(
        make_result(
            "AID-012",
            (
                "Each PRIMARY AccountID represents "
                "only one approved customer/account signature."
            ),
            collisions == 0,
            (
                "primary_account_collisions="
                f"{collisions}"
            ),
        )
    )

    return results


# ============================================================
# 12. FALLBACK CUSTOMER BOUNDARY TEST
# ============================================================

def validate_fallback_customer_boundary(
    mapping,
):

    fallback_mask = (
        mapping[
            "AccountID_method"
        ]
        .astype(str)
        .str.startswith(
            "FALLBACK_"
        )
    )

    fallback = mapping.loc[
        fallback_mask
    ].copy()

    if len(fallback) == 0:

        cross_customer = 0

    else:

        account_customer_counts = (
            fallback.groupby(
                "AccountID"
            )["CustomerID"]
            .nunique()
        )

        cross_customer = int(
            (
                account_customer_counts
                > 1
            ).sum()
        )

    return [
        make_result(
            "AID-013",
            (
                "Fallback AccountID assignments do "
                "not cross CustomerID boundaries."
            ),
            cross_customer == 0,
            (
                "fallback_accounts_crossing_customers="
                f"{cross_customer}"
            ),
        )
    ]


# ============================================================
# 13. UNRESOLVED ACCOUNT OWNERSHIP TEST
# ============================================================

def validate_unresolved_accounts(mapping):

    unresolved = mapping.loc[
        mapping[
            "AccountID_method"
        ]
        == "UNRESOLVED_AVAILABLE_SIGNATURE"
    ].copy()

    if len(unresolved) == 0:

        problematic = 0

    else:

        account_customer_counts = (
            unresolved.groupby(
                "AccountID"
            )["CustomerID"]
            .nunique()
        )

        problematic = int(
            (
                account_customer_counts > 1
            ).sum()
        )

    return [
        make_result(
            "AID-014",
            (
                "Unresolved AccountIDs remain nested "
                "within exactly one CustomerID."
            ),
            problematic == 0,
            (
                "unresolved_accounts_crossing_customers="
                f"{problematic}"
            ),
        )
    ]


# ============================================================
# 14. METHOD COLLISION TEST
# ============================================================

def validate_method_collisions(mapping):

    grouped = (
        mapping.groupby(
            "AccountID"
        )["AccountID_method"]
        .agg(
            lambda x: set(x)
        )
    )

    problematic = 0

    for methods in grouped:

        has_primary = (
            "PRIMARY"
            in methods
        )

        has_unresolved = (
            "UNRESOLVED_AVAILABLE_SIGNATURE"
            in methods
        )

        # FALLBACK + PRIMARY is allowed because
        # fallback intentionally reuses an existing
        # primary account.
        #
        # PRIMARY + UNRESOLVED should not occur.

        if (
            has_primary
            and has_unresolved
        ):
            problematic += 1

        # An unresolved account should not also be
        # acting as a fallback account.
        if (
            has_unresolved
            and any(
                method.startswith(
                    "FALLBACK_"
                )
                for method
                in methods
            )
        ):
            problematic += 1

    return [
        make_result(
            "AID-015",
            (
                "Unresolved AccountIDs do not collide "
                "with primary or fallback accounts."
            ),
            problematic == 0,
            (
                "problematic_method_collisions="
                f"{problematic}"
            ),
        )
    ]


# ============================================================
# 15. CREATE VALIDATION SUMMARY
# ============================================================

def create_summary(
    source,
    mapping,
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

    return {
        "source_transaction_rows": int(
            len(source)
        ),

        "mapping_rows": int(
            len(mapping)
        ),

        "distinct_customer_ids": int(
            mapping[
                "CustomerID"
            ].nunique()
        ),

        "distinct_account_ids": int(
            mapping[
                "AccountID"
            ].nunique()
        ),

        "tests_run": int(
            len(results)
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
# 16. SAVE VALIDATION OUTPUTS
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
        / "account_id_validation_results.csv"
    )

    summary_file = (
        REPORT_DIR
        / "account_id_validation_summary.json"
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

    print("\n" + "=" * 72)
    print("ACCOUNTID VALIDATION RESULTS")
    print("=" * 72)

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

    print("\n" + "=" * 72)

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

    print("=" * 72)
    print("ACCOUNTID VALIDATION")
    print("=" * 72)

    print(
        "\nThis script independently validates "
        "the generated AccountID relationships."
    )

    print(
        "It does not generate new AccountIDs."
    )

    check_files()

    source, mapping = (
        load_data()
    )

    results = []

    results.extend(
        validate_structure(
            source,
            mapping,
        )
    )

    results.extend(
        validate_source_preservation(
            source,
            mapping,
        )
    )

    results.extend(
        validate_methods(
            mapping
        )
    )

    results.extend(
        validate_account_ownership(
            mapping
        )
    )

    results.extend(
        validate_primary_accounts(
            source,
            mapping,
        )
    )

    results.extend(
        validate_fallback_customer_boundary(
            mapping
        )
    )

    results.extend(
        validate_unresolved_accounts(
            mapping
        )
    )

    results.extend(
        validate_method_collisions(
            mapping
        )
    )

    summary = (
        create_summary(
            source,
            mapping,
            results,
        )
    )

    save_results(
        results,
        summary,
    )

    print_results(
        results,
        summary,
    )

    print("\n" + "=" * 72)

    if (
        summary[
            "overall_status"
        ]
        == "PASS"
    ):

        print(
            "ACCOUNTID VALIDATION PASSED"
        )

    else:

        print(
            "ACCOUNTID VALIDATION FAILED"
        )

        print(
            "Do not continue to the next "
            "synthetic entity until failures "
            "are investigated."
        )

    print("=" * 72)


if __name__ == "__main__":
    main()