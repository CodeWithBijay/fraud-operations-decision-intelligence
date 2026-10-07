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

CUSTOMER_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "customer"
    / "transaction_customer_mapping.csv"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "customer_id_validation"
)


# ============================================================
# 2. EXPECTED CUSTOMERID METHODS
# ============================================================

VALID_METHODS = {
    "PRIMARY",
    "FALLBACK_CARD_ADDR_UNIQUE",
    "FALLBACK_CARD_EMAIL_UNIQUE",
    "UNRESOLVED_CARD_ADDR",
    "UNRESOLVED_CARD_EMAIL",
    "ISOLATED_WEAK_INFORMATION",
    "ISOLATED_SAFETY",
}


# ============================================================
# 3. CHECK INPUT FILES
# ============================================================

def check_files():

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            f"Source transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    if not CUSTOMER_MAPPING_FILE.exists():
        raise FileNotFoundError(
            f"Customer mapping file not found:\n"
            f"{CUSTOMER_MAPPING_FILE}"
        )

    print("Required files found.")


# ============================================================
# 4. LOAD DATA
# ============================================================

def load_data():

    print("\nLoading source fields...")

    source = pd.read_csv(
        TRANSACTION_FILE,
        usecols=[
            "TransactionID",
            "TransactionDT",
            "card1",
            "addr1",
            "P_emaildomain",
        ],
        low_memory=False,
    )

    print("Loading generated CustomerID mapping...")

    mapping = pd.read_csv(
        CUSTOMER_MAPPING_FILE,
        low_memory=False,
    )

    print(
        f"Source transactions: {len(source):,}"
    )

    print(
        f"Generated mapping rows: {len(mapping):,}"
    )

    return source, mapping


# ============================================================
# 5. VALIDATION RESULT HELPER
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
        "status": "PASS" if passed else "FAIL",
        "observed": observed,
    }


# ============================================================
# 6. BASIC STRUCTURAL TESTS
# ============================================================

def validate_structure(source, mapping):

    results = []

    # --------------------------------------------------------
    # Same number of rows
    # --------------------------------------------------------

    passed = len(source) == len(mapping)

    results.append(
        make_result(
            "CID-001",
            "Generated mapping row count matches source transaction count.",
            passed,
            (
                f"source={len(source)}, "
                f"mapping={len(mapping)}"
            ),
        )
    )

    # --------------------------------------------------------
    # TransactionID unique
    # --------------------------------------------------------

    duplicate_ids = int(
        mapping["TransactionID"]
        .duplicated()
        .sum()
    )

    results.append(
        make_result(
            "CID-002",
            "TransactionID is unique in the CustomerID mapping.",
            duplicate_ids == 0,
            f"duplicate_transaction_ids={duplicate_ids}",
        )
    )

    # --------------------------------------------------------
    # CustomerID missing
    # --------------------------------------------------------

    missing_customer_ids = int(
        mapping["CustomerID"]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "CID-003",
            "Every transaction has a CustomerID.",
            missing_customer_ids == 0,
            f"missing_customer_ids={missing_customer_ids}",
        )
    )

    # --------------------------------------------------------
    # CustomerID method missing
    # --------------------------------------------------------

    missing_methods = int(
        mapping["CustomerID_method"]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "CID-004",
            "Every transaction records its CustomerID assignment method.",
            missing_methods == 0,
            f"missing_methods={missing_methods}",
        )
    )

    return results


# ============================================================
# 7. SOURCE PRESERVATION TEST
# ============================================================

def validate_source_preservation(source, mapping):

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
        suffixes=("_source", "_generated"),
        indicator=True,
    )

    missing_relationships = int(
        (comparison["_merge"] != "both").sum()
    )

    results.append(
        make_result(
            "CID-005",
            "Every source TransactionID appears exactly in the generated mapping.",
            missing_relationships == 0,
            (
                "unmatched_transaction_ids="
                f"{missing_relationships}"
            ),
        )
    )

    matched = comparison[
        comparison["_merge"] == "both"
    ].copy()

    changed_dt = int(
        (
            matched["TransactionDT_source"]
            != matched["TransactionDT_generated"]
        ).sum()
    )

    results.append(
        make_result(
            "CID-006",
            "TransactionDT is preserved in the generated mapping.",
            changed_dt == 0,
            f"changed_transaction_dt={changed_dt}",
        )
    )

    return results


# ============================================================
# 8. METHOD VALIDATION
# ============================================================

def validate_methods(mapping):

    observed_methods = set(
        mapping["CustomerID_method"]
        .dropna()
        .unique()
    )

    unexpected = sorted(
        observed_methods - VALID_METHODS
    )

    return [
        make_result(
            "CID-007",
            "Only documented CustomerID assignment methods are present.",
            len(unexpected) == 0,
            f"unexpected_methods={unexpected}",
        )
    ]


# ============================================================
# 9. PRIMARY GROUPING VALIDATION
# ============================================================

def validate_primary_grouping(source, mapping):

    results = []

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "CustomerID",
                "CustomerID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
    )

    primary = combined[
        combined["CustomerID_method"]
        == "PRIMARY"
    ].copy()

    primary["expected_signature"] = (
        primary[
            [
                "card1",
                "addr1",
                "P_emaildomain",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    # --------------------------------------------------------
    # Same primary signature should never produce
    # multiple CustomerIDs.
    # --------------------------------------------------------

    signature_customer_counts = (
        primary.groupby(
            "expected_signature"
        )["CustomerID"]
        .nunique()
    )

    inconsistent_signatures = int(
        (
            signature_customer_counts > 1
        ).sum()
    )

    results.append(
        make_result(
            "CID-008",
            (
                "Each primary source signature maps to exactly "
                "one CustomerID."
            ),
            inconsistent_signatures == 0,
            (
                "inconsistent_primary_signatures="
                f"{inconsistent_signatures}"
            ),
        )
    )

    # --------------------------------------------------------
    # One primary CustomerID should not represent
    # multiple distinct primary signatures.
    # --------------------------------------------------------

    customer_signature_counts = (
        primary.groupby(
            "CustomerID"
        )["expected_signature"]
        .nunique()
    )

    collisions = int(
        (
            customer_signature_counts > 1
        ).sum()
    )

    results.append(
        make_result(
            "CID-009",
            (
                "Each primary CustomerID corresponds to only "
                "one primary source signature."
            ),
            collisions == 0,
            f"primary_customer_collisions={collisions}",
        )
    )

    return results


# ============================================================
# 10. WEAK-INFORMATION ISOLATION TEST
# ============================================================

def validate_isolated_records(source, mapping):

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "CustomerID",
                "CustomerID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
    )

    isolated = combined[
        combined["CustomerID_method"]
        == "ISOLATED_WEAK_INFORMATION"
    ].copy()

    duplicate_customer_ids = int(
        isolated["CustomerID"]
        .duplicated()
        .sum()
    )

    return [
        make_result(
            "CID-010",
            (
                "Weak-information isolated transactions do not "
                "share CustomerIDs with each other."
            ),
            duplicate_customer_ids == 0,
            (
                "duplicate_isolated_customer_ids="
                f"{duplicate_customer_ids}"
            ),
        )
    ]


# ============================================================
# 11. GLOBAL CUSTOMERID COLLISION CHECK
# ============================================================

def validate_method_collisions(mapping):

    method_counts = (
        mapping.groupby(
            "CustomerID"
        )["CustomerID_method"]
        .nunique()
    )

    # Sharing PRIMARY and UNIQUE FALLBACK is legitimate because
    # a fallback may intentionally link to an established
    # primary CustomerID.
    #
    # Therefore we inspect only CustomerIDs used by incompatible
    # unresolved or isolated methodologies.

    grouped = (
        mapping.groupby("CustomerID")
        ["CustomerID_method"]
        .agg(
            lambda x: set(x)
        )
    )

    problematic = 0

    for methods in grouped:

        unresolved_methods = {
            method
            for method in methods
            if method.startswith(
                "UNRESOLVED"
            )
            or method.startswith(
                "ISOLATED"
            )
        }

        if len(unresolved_methods) > 1:
            problematic += 1

        if (
            unresolved_methods
            and "PRIMARY" in methods
        ):
            problematic += 1

    return [
        make_result(
            "CID-011",
            (
                "Unresolved or isolated CustomerIDs do not "
                "collide with incompatible assignment methods."
            ),
            problematic == 0,
            (
                "problematic_method_collisions="
                f"{problematic}"
            ),
        )
    ]


# ============================================================
# 12. CREATE SUMMARY
# ============================================================

def create_summary(
    source,
    mapping,
    results,
):

    passed = sum(
        result["status"] == "PASS"
        for result in results
    )

    failed = sum(
        result["status"] == "FAIL"
        for result in results
    )

    summary = {
        "source_transaction_rows": int(
            len(source)
        ),

        "mapping_rows": int(
            len(mapping)
        ),

        "distinct_customer_ids": int(
            mapping["CustomerID"]
            .nunique()
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

    return summary


# ============================================================
# 13. SAVE VALIDATION RESULTS
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
        / "customer_id_validation_results.csv"
    )

    summary_file = (
        REPORT_DIR
        / "customer_id_validation_summary.json"
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

    print("\nValidation results saved to:")
    print(results_file)

    print("\nValidation summary saved to:")
    print(summary_file)


# ============================================================
# 14. PRINT VALIDATION RESULTS
# ============================================================

def print_results(results, summary):

    print("\n" + "=" * 70)
    print("CUSTOMERID VALIDATION RESULTS")
    print("=" * 70)

    for result in results:

        symbol = (
            "PASS"
            if result["status"]
            == "PASS"
            else "FAIL"
        )

        print(
            f"\n{result['test_id']} "
            f"[{symbol}]"
        )

        print(
            result["description"]
        )

        print(
            f"Observed: "
            f"{result['observed']}"
        )

    print("\n" + "=" * 70)

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
        f"Overall status: "
        f"{summary['overall_status']}"
    )


# ============================================================
# 15. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("CUSTOMERID VALIDATION")
    print("=" * 70)

    check_files()

    source, mapping = load_data()

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
        validate_primary_grouping(
            source,
            mapping,
        )
    )

    results.extend(
        validate_isolated_records(
            source,
            mapping,
        )
    )

    results.extend(
        validate_method_collisions(
            mapping
        )
    )

    summary = create_summary(
        source,
        mapping,
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

    print("\n" + "=" * 70)

    if summary["overall_status"] == "PASS":

        print(
            "CUSTOMERID VALIDATION PASSED"
        )

    else:

        print(
            "CUSTOMERID VALIDATION FAILED"
        )

        print(
            "Do not move to AccountID "
            "until the failure is resolved."
        )

    print("=" * 70)


if __name__ == "__main__":
    main()