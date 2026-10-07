from pathlib import Path
import hashlib
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

DEVICE_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "device"
    / "transaction_device_mapping.csv"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "device_id_validation"
)


# ============================================================
# 2. VALID DEVICEID METHODS
# ============================================================

VALID_METHODS = {
    "CUSTOMER_NESTED_DEVICE_SIGNATURE",
    "INSUFFICIENT_DEVICE_EVIDENCE",
}


# ============================================================
# 3. EXPECTED DEVICEID FUNCTION
# ============================================================

def expected_device_id(
    customer_id,
    device_type,
    device_info,
):
    """
    Independently reconstruct the expected deterministic
    DeviceID using the documented generation rule.

    This duplicates the rule intentionally.

    The validator does not import the generation function,
    because validation should independently verify that the
    generator produced the expected identifier.
    """

    source_signature = (
        f"{customer_id}|"
        f"{device_type}|"
        f"{device_info}"
    )

    digest = hashlib.sha256(
        source_signature.encode("utf-8")
    ).hexdigest()[:16]

    return f"DEV_{digest.upper()}"


# ============================================================
# 4. CHECK REQUIRED FILES
# ============================================================

def check_files():
    """
    Confirm all required source and generated files exist.
    """

    required_files = [
        TRANSACTION_FILE,
        IDENTITY_FILE,
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
# 5. LOAD SOURCE AND GENERATED DATA
# ============================================================

def load_data():
    """
    Load only fields needed for DeviceID validation.

    isFraud is deliberately not loaded.
    """

    print("\nLoading source transaction information...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=[
            "TransactionID",
            "TransactionDT",
        ],
        low_memory=False,
    )

    print("Loading source device information...")

    identity = pd.read_csv(
        IDENTITY_FILE,
        usecols=[
            "TransactionID",
            "DeviceType",
            "DeviceInfo",
        ],
        low_memory=False,
    )

    print("Loading generated DeviceID mapping...")

    mapping = pd.read_csv(
        DEVICE_MAPPING_FILE,
        low_memory=False,
    )

    source = transactions.merge(
        identity,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    if len(source) != len(transactions):

        raise ValueError(
            "Source transaction count changed "
            "after identity join."
        )

    print(
        f"Source transactions: {len(source):,}"
    )

    print(
        f"Generated mapping rows: {len(mapping):,}"
    )

    return source, mapping


# ============================================================
# 6. RESULT HELPER
# ============================================================

def make_result(
    test_id,
    description,
    passed,
    observed,
):
    """
    Create a standardized validation result.
    """

    return {
        "test_id": test_id,
        "description": description,
        "status": (
            "PASS"
            if passed
            else "FAIL"
        ),
        "observed": str(observed),
    }


# ============================================================
# 7. STRUCTURAL VALIDATION
# ============================================================

def validate_structure(
    source,
    mapping,
):

    results = []

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    results.append(
        make_result(
            "DID-001",
            (
                "Generated DeviceID mapping row count "
                "matches the source transaction count."
            ),
            len(source) == len(mapping),
            (
                f"source={len(source)}, "
                f"mapping={len(mapping)}"
            ),
        )
    )

    # --------------------------------------------------------
    # TransactionID uniqueness
    # --------------------------------------------------------

    duplicate_transaction_ids = int(
        mapping[
            "TransactionID"
        ]
        .duplicated()
        .sum()
    )

    results.append(
        make_result(
            "DID-002",
            (
                "TransactionID is unique in the "
                "DeviceID mapping."
            ),
            duplicate_transaction_ids == 0,
            (
                "duplicate_transaction_ids="
                f"{duplicate_transaction_ids}"
            ),
        )
    )

    # --------------------------------------------------------
    # CustomerID completeness
    # --------------------------------------------------------

    missing_customer_ids = int(
        mapping[
            "CustomerID"
        ]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "DID-003",
            (
                "Every transaction retains "
                "a CustomerID."
            ),
            missing_customer_ids == 0,
            (
                "missing_customer_ids="
                f"{missing_customer_ids}"
            ),
        )
    )

    # --------------------------------------------------------
    # Method completeness
    # --------------------------------------------------------

    missing_methods = int(
        mapping[
            "DeviceID_method"
        ]
        .isna()
        .sum()
    )

    results.append(
        make_result(
            "DID-004",
            (
                "Every transaction records its "
                "DeviceID assignment method."
            ),
            missing_methods == 0,
            (
                "missing_device_methods="
                f"{missing_methods}"
            ),
        )
    )

    return results


# ============================================================
# 8. SOURCE RECORD PRESERVATION
# ============================================================

def validate_source_preservation(
    source,
    mapping,
):

    results = []

    comparison = source.merge(
        mapping,
        on="TransactionID",
        how="outer",
        suffixes=(
            "_source",
            "_mapping",
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
            "DID-005",
            (
                "Every source TransactionID is represented "
                "exactly in the DeviceID mapping."
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
                "TransactionDT_mapping"
            ]
        ).sum()
    )

    results.append(
        make_result(
            "DID-006",
            (
                "TransactionDT is preserved in "
                "the generated mapping."
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
# 9. SOURCE DEVICE-FIELD PRESERVATION
# ============================================================

def validate_device_field_preservation(
    source,
    mapping,
):

    results = []

    comparison = source[
        [
            "TransactionID",
            "DeviceType",
            "DeviceInfo",
        ]
    ].merge(
        mapping[
            [
                "TransactionID",
                "DeviceType",
                "DeviceInfo",
            ]
        ],
        on="TransactionID",
        how="inner",
        suffixes=(
            "_source",
            "_mapping",
        ),
        validate="one_to_one",
    )

    # pandas considers NaN != NaN, so compare after
    # normalizing missing values to the same marker.

    device_type_source = (
        comparison[
            "DeviceType_source"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    device_type_mapping = (
        comparison[
            "DeviceType_mapping"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    changed_device_type = int(
        (
            device_type_source
            != device_type_mapping
        ).sum()
    )

    results.append(
        make_result(
            "DID-007",
            (
                "Source DeviceType values are preserved "
                "without modification."
            ),
            changed_device_type == 0,
            (
                "changed_device_type_values="
                f"{changed_device_type}"
            ),
        )
    )

    device_info_source = (
        comparison[
            "DeviceInfo_source"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    device_info_mapping = (
        comparison[
            "DeviceInfo_mapping"
        ]
        .fillna("__MISSING__")
        .astype(str)
    )

    changed_device_info = int(
        (
            device_info_source
            != device_info_mapping
        ).sum()
    )

    results.append(
        make_result(
            "DID-008",
            (
                "Source DeviceInfo values are preserved "
                "without modification."
            ),
            changed_device_info == 0,
            (
                "changed_device_info_values="
                f"{changed_device_info}"
            ),
        )
    )

    return results


# ============================================================
# 10. METHOD VALIDATION
# ============================================================

def validate_methods(mapping):

    observed_methods = set(
        mapping[
            "DeviceID_method"
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
            "DID-009",
            (
                "Only documented DeviceID assignment "
                "methods are present."
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
# 11. DEVICE EVIDENCE ELIGIBILITY
# ============================================================

def validate_device_evidence_policy(
    source,
    mapping,
):

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "CustomerID",
                "DeviceID",
                "DeviceID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
        validate="one_to_one",
    )

    complete_evidence = (
        combined[
            "DeviceType"
        ].notna()
        & combined[
            "DeviceInfo"
        ].notna()
    )

    has_device_id = (
        combined[
            "DeviceID"
        ].notna()
    )

    eligible_without_device_id = int(
        (
            complete_evidence
            & ~has_device_id
        ).sum()
    )

    insufficient_with_device_id = int(
        (
            ~complete_evidence
            & has_device_id
        ).sum()
    )

    results = []

    results.append(
        make_result(
            "DID-010",
            (
                "Every transaction with both DeviceType "
                "and DeviceInfo receives a DeviceID."
            ),
            eligible_without_device_id == 0,
            (
                "eligible_without_device_id="
                f"{eligible_without_device_id}"
            ),
        )
    )

    results.append(
        make_result(
            "DID-011",
            (
                "No DeviceID is generated when either "
                "required source device field is missing."
            ),
            insufficient_with_device_id == 0,
            (
                "insufficient_evidence_with_device_id="
                f"{insufficient_with_device_id}"
            ),
        )
    )

    return results


# ============================================================
# 12. METHOD / EVIDENCE CONSISTENCY
# ============================================================

def validate_method_evidence_consistency(
    source,
    mapping,
):

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "DeviceID",
                "DeviceID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
        validate="one_to_one",
    )

    complete_evidence = (
        combined[
            "DeviceType"
        ].notna()
        & combined[
            "DeviceInfo"
        ].notna()
    )

    generated_method = (
        combined[
            "DeviceID_method"
        ]
        ==
        "CUSTOMER_NESTED_DEVICE_SIGNATURE"
    )

    insufficient_method = (
        combined[
            "DeviceID_method"
        ]
        ==
        "INSUFFICIENT_DEVICE_EVIDENCE"
    )

    wrong_generated_method = int(
        (
            complete_evidence
            & ~generated_method
        ).sum()
    )

    wrong_insufficient_method = int(
        (
            ~complete_evidence
            & ~insufficient_method
        ).sum()
    )

    results = []

    results.append(
        make_result(
            "DID-012",
            (
                "Transactions with complete device evidence "
                "use CUSTOMER_NESTED_DEVICE_SIGNATURE."
            ),
            wrong_generated_method == 0,
            (
                "incorrect_complete_evidence_methods="
                f"{wrong_generated_method}"
            ),
        )
    )

    results.append(
        make_result(
            "DID-013",
            (
                "Transactions with incomplete device evidence "
                "use INSUFFICIENT_DEVICE_EVIDENCE."
            ),
            wrong_insufficient_method == 0,
            (
                "incorrect_insufficient_evidence_methods="
                f"{wrong_insufficient_method}"
            ),
        )
    )

    return results


# ============================================================
# 13. NULL POLICY
# ============================================================

def validate_null_policy(
    source,
    mapping,
):

    combined = source.merge(
        mapping[
            [
                "TransactionID",
                "DeviceID",
                "DeviceID_method",
            ]
        ],
        on="TransactionID",
        how="inner",
        validate="one_to_one",
    )

    null_device_ids = (
        combined[
            "DeviceID"
        ].isna()
    )

    incomplete_evidence = (
        combined[
            "DeviceType"
        ].isna()
        | combined[
            "DeviceInfo"
        ].isna()
    )

    unsupported_nulls = int(
        (
            null_device_ids
            & ~incomplete_evidence
        ).sum()
    )

    incorrect_null_method = int(
        (
            null_device_ids
            & (
                combined[
                    "DeviceID_method"
                ]
                !=
                "INSUFFICIENT_DEVICE_EVIDENCE"
            )
        ).sum()
    )

    return [
        make_result(
            "DID-014",
            (
                "NULL DeviceID occurs only when source "
                "device evidence is insufficient."
            ),
            unsupported_nulls == 0,
            (
                "unsupported_null_device_ids="
                f"{unsupported_nulls}"
            ),
        ),

        make_result(
            "DID-015",
            (
                "Every NULL DeviceID records "
                "INSUFFICIENT_DEVICE_EVIDENCE."
            ),
            incorrect_null_method == 0,
            (
                "incorrect_null_methods="
                f"{incorrect_null_method}"
            ),
        ),
    ]


# ============================================================
# 14. CUSTOMERID BOUNDARY VALIDATION
# ============================================================

def validate_customer_boundary(mapping):

    usable = mapping.loc[
        mapping[
            "DeviceID"
        ].notna()
    ].copy()

    device_customer_counts = (
        usable.groupby(
            "DeviceID"
        )[
            "CustomerID"
        ]
        .nunique()
    )

    cross_customer_devices = int(
        (
            device_customer_counts > 1
        ).sum()
    )

    return [
        make_result(
            "DID-016",
            (
                "Every generated DeviceID belongs to "
                "exactly one CustomerID."
            ),
            cross_customer_devices == 0,
            (
                "device_ids_crossing_customer_boundary="
                f"{cross_customer_devices}"
            ),
        )
    ]


# ============================================================
# 15. SIGNATURE CONSISTENCY
# ============================================================

def validate_signature_consistency(mapping):

    usable = mapping.loc[
        mapping[
            "DeviceID"
        ].notna()
    ].copy()

    usable[
        "customer_device_signature"
    ] = (
        usable[
            "CustomerID"
        ].astype(str)
        + "|"
        + usable[
            "DeviceType"
        ].astype(str)
        + "|"
        + usable[
            "DeviceInfo"
        ].astype(str)
    )

    # --------------------------------------------------------
    # Same signature -> one DeviceID
    # --------------------------------------------------------

    signature_device_counts = (
        usable.groupby(
            "customer_device_signature"
        )[
            "DeviceID"
        ]
        .nunique()
    )

    inconsistent_signatures = int(
        (
            signature_device_counts > 1
        ).sum()
    )

    # --------------------------------------------------------
    # One DeviceID -> one signature
    # --------------------------------------------------------

    device_signature_counts = (
        usable.groupby(
            "DeviceID"
        )[
            "customer_device_signature"
        ]
        .nunique()
    )

    collisions = int(
        (
            device_signature_counts > 1
        ).sum()
    )

    results = []

    results.append(
        make_result(
            "DID-017",
            (
                "The same CustomerID + DeviceType + DeviceInfo "
                "signature always maps to one DeviceID."
            ),
            inconsistent_signatures == 0,
            (
                "inconsistent_signatures="
                f"{inconsistent_signatures}"
            ),
        )
    )

    results.append(
        make_result(
            "DID-018",
            (
                "Each DeviceID corresponds to only one "
                "customer-device signature."
            ),
            collisions == 0,
            (
                "device_signature_collisions="
                f"{collisions}"
            ),
        )
    )

    return results


# ============================================================
# 16. DETERMINISTIC HASH VALIDATION
# ============================================================

def validate_deterministic_id(mapping):
    """
    Independently recalculate DeviceID from the documented
    signature and compare it with the generated DeviceID.
    """

    usable = mapping.loc[
        mapping[
            "DeviceID"
        ].notna()
    ].copy()

    usable[
        "expected_device_id"
    ] = usable.apply(
        lambda row:
        expected_device_id(
            row[
                "CustomerID"
            ],
            row[
                "DeviceType"
            ],
            row[
                "DeviceInfo"
            ],
        ),
        axis=1,
    )

    mismatches = int(
        (
            usable[
                "DeviceID"
            ]
            != usable[
                "expected_device_id"
            ]
        ).sum()
    )

    return [
        make_result(
            "DID-019",
            (
                "Every generated DeviceID matches the "
                "documented deterministic hash rule."
            ),
            mismatches == 0,
            (
                "deterministic_id_mismatches="
                f"{mismatches}"
            ),
        )
    ]


# ============================================================
# 17. GENERATED DEVICE COUNT RECONCILIATION
# ============================================================

def validate_count_reconciliation(
    source,
    mapping,
):

    complete_evidence_count = int(
        (
            source[
                "DeviceType"
            ].notna()
            & source[
                "DeviceInfo"
            ].notna()
        ).sum()
    )

    generated_count = int(
        mapping[
            "DeviceID"
        ]
        .notna()
        .sum()
    )

    incomplete_evidence_count = int(
        len(source)
        - complete_evidence_count
    )

    null_device_count = int(
        mapping[
            "DeviceID"
        ]
        .isna()
        .sum()
    )

    results = []

    results.append(
        make_result(
            "DID-020",
            (
                "Generated DeviceID count matches the "
                "number of transactions with complete "
                "source device evidence."
            ),
            (
                generated_count
                == complete_evidence_count
            ),
            (
                "eligible="
                f"{complete_evidence_count}, "
                "generated="
                f"{generated_count}"
            ),
        )
    )

    results.append(
        make_result(
            "DID-021",
            (
                "NULL DeviceID count matches the number "
                "of transactions with incomplete device evidence."
            ),
            (
                null_device_count
                == incomplete_evidence_count
            ),
            (
                "incomplete_evidence="
                f"{incomplete_evidence_count}, "
                "null_device_ids="
                f"{null_device_count}"
            ),
        )
    )

    return results


# ============================================================
# 18. IDENTIFY HIGH-DEVICE CUSTOMERS
# ============================================================

def analyze_high_device_customers(mapping):
    """
    Investigate unusually large customer-device counts.

    This analysis does NOT automatically fail validation.
    It produces evidence for interpretation.
    """

    usable = mapping.loc[
        mapping[
            "DeviceID"
        ].notna()
    ].copy()

    customer_device_counts = (
        usable[
            [
                "CustomerID",
                "DeviceID",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "CustomerID"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    if len(
        customer_device_counts
    ) == 0:

        summary = {
            "maximum_devices_per_customer": 0,
            "customers_over_10_devices": 0,
            "customers_over_25_devices": 0,
            "customers_over_50_devices": 0,
            "customers_over_100_devices": 0,
        }

        details = pd.DataFrame(
            columns=[
                "CustomerID",
                "distinct_device_ids",
                "transaction_count_with_device_evidence",
            ]
        )

        return summary, details

    maximum_devices = int(
        customer_device_counts.max()
    )

    summary = {
        "maximum_devices_per_customer": (
            maximum_devices
        ),

        "customers_over_10_devices": int(
            (
                customer_device_counts > 10
            ).sum()
        ),

        "customers_over_25_devices": int(
            (
                customer_device_counts > 25
            ).sum()
        ),

        "customers_over_50_devices": int(
            (
                customer_device_counts > 50
            ).sum()
        ),

        "customers_over_100_devices": int(
            (
                customer_device_counts > 100
            ).sum()
        ),
    }

    high_customer_ids = (
        customer_device_counts[
            customer_device_counts > 10
        ]
        .index
    )

    high_device_transactions = (
        usable[
            usable[
                "CustomerID"
            ].isin(
                high_customer_ids
            )
        ]
    )

    transaction_counts = (
        high_device_transactions
        .groupby(
            "CustomerID"
        )[
            "TransactionID"
        ]
        .count()
    )

    details = (
        customer_device_counts.loc[
            high_customer_ids
        ]
        .rename(
            "distinct_device_ids"
        )
        .to_frame()
    )

    details[
        "transaction_count_with_device_evidence"
    ] = (
        transaction_counts
    )

    details = (
        details
        .reset_index()
        .sort_values(
            by="distinct_device_ids",
            ascending=False,
        )
    )

    return summary, details


# ============================================================
# 19. INVESTIGATE MAXIMUM-DEVICE CUSTOMER
# ============================================================

def investigate_max_device_customer(mapping):
    """
    Produce detailed evidence for the customer with the
    highest number of analytical DeviceIDs.

    This lets us inspect the previously observed
    448-device customer without automatically labeling it
    as an error.
    """

    usable = mapping.loc[
        mapping[
            "DeviceID"
        ].notna()
    ].copy()

    customer_device_counts = (
        usable[
            [
                "CustomerID",
                "DeviceID",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "CustomerID"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    if len(
        customer_device_counts
    ) == 0:

        return {
            "customer_id": None,
            "distinct_device_ids": 0,
            "transactions_with_device_evidence": 0,
            "distinct_device_type_values": 0,
            "distinct_device_info_values": 0,
        }

    customer_id = str(
        customer_device_counts
        .index[0]
    )

    customer_data = (
        usable[
            usable[
                "CustomerID"
            ].astype(str)
            == customer_id
        ]
        .copy()
    )

    return {
        "customer_id": customer_id,

        "distinct_device_ids": int(
            customer_data[
                "DeviceID"
            ]
            .nunique()
        ),

        "transactions_with_device_evidence": int(
            len(
                customer_data
            )
        ),

        "distinct_device_type_values": int(
            customer_data[
                "DeviceType"
            ]
            .nunique(
                dropna=True
            )
        ),

        "distinct_device_info_values": int(
            customer_data[
                "DeviceInfo"
            ]
            .nunique(
                dropna=True
            )
        ),
    }


# ============================================================
# 20. CREATE VALIDATION SUMMARY
# ============================================================

def create_summary(
    source,
    mapping,
    results,
    high_device_summary,
    max_customer_analysis,
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

        "transactions_with_device_id": int(
            mapping[
                "DeviceID"
            ]
            .notna()
            .sum()
        ),

        "transactions_without_device_id": int(
            mapping[
                "DeviceID"
            ]
            .isna()
            .sum()
        ),

        "distinct_device_ids": int(
            mapping[
                "DeviceID"
            ]
            .nunique(
                dropna=True
            )
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

        "high_device_customer_analysis": (
            high_device_summary
        ),

        "maximum_device_customer_analysis": (
            max_customer_analysis
        ),
    }


# ============================================================
# 21. SAVE RESULTS
# ============================================================

def save_results(
    results,
    summary,
    high_device_details,
):

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_file = (
        REPORT_DIR
        / "device_id_validation_results.csv"
    )

    summary_file = (
        REPORT_DIR
        / "device_id_validation_summary.json"
    )

    high_device_file = (
        REPORT_DIR
        / "high_device_customer_analysis.csv"
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

    high_device_details.to_csv(
        high_device_file,
        index=False,
    )

    print(
        "\nValidation outputs saved to:"
    )

    print(
        results_file
    )

    print(
        summary_file
    )

    print(
        high_device_file
    )


# ============================================================
# 22. PRINT RESULTS
# ============================================================

def print_results(
    results,
    summary,
):

    print("\n" + "=" * 78)
    print("DEVICEID VALIDATION RESULTS")
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
        "Tests run: "
        f"{summary['tests_run']}"
    )

    print(
        "Passed: "
        f"{summary['tests_passed']}"
    )

    print(
        "Failed: "
        f"{summary['tests_failed']}"
    )

    print(
        "Overall status: "
        f"{summary['overall_status']}"
    )

    print(
        "\nHigh-device customer analysis:"
    )

    for key, value in (
        summary[
            "high_device_customer_analysis"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )

    print(
        "\nMaximum-device customer:"
    )

    for key, value in (
        summary[
            "maximum_device_customer_analysis"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )


# ============================================================
# 23. MAIN
# ============================================================

def main():

    print("=" * 78)
    print("DEVICEID VALIDATION")
    print("=" * 78)

    print(
        "\nThis validator independently checks "
        "the generated DeviceID mapping."
    )

    print(
        "No DeviceID is generated by this script."
    )

    print(
        "isFraud is not loaded or used."
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
        validate_device_field_preservation(
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
        validate_device_evidence_policy(
            source,
            mapping,
        )
    )

    results.extend(
        validate_method_evidence_consistency(
            source,
            mapping,
        )
    )

    results.extend(
        validate_null_policy(
            source,
            mapping,
        )
    )

    results.extend(
        validate_customer_boundary(
            mapping
        )
    )

    results.extend(
        validate_signature_consistency(
            mapping
        )
    )

    results.extend(
        validate_deterministic_id(
            mapping
        )
    )

    results.extend(
        validate_count_reconciliation(
            source,
            mapping,
        )
    )

    (
        high_device_summary,
        high_device_details,
    ) = analyze_high_device_customers(
        mapping
    )

    max_customer_analysis = (
        investigate_max_device_customer(
            mapping
        )
    )

    summary = create_summary(
        source,
        mapping,
        results,
        high_device_summary,
        max_customer_analysis,
    )

    save_results(
        results,
        summary,
        high_device_details,
    )

    print_results(
        results,
        summary,
    )

    print("\n" + "=" * 78)

    if (
        summary[
            "overall_status"
        ]
        == "PASS"
    ):

        print(
            "DEVICEID VALIDATION PASSED"
        )

        print(
            "\nNote: PASS confirms implementation "
            "and integrity rules."
        )

        print(
            "It does not prove that analytical "
            "DeviceIDs are verified physical devices."
        )

    else:

        print(
            "DEVICEID VALIDATION FAILED"
        )

        print(
            "\nDo not continue until the failed "
            "tests are investigated."
        )

    print("=" * 78)


if __name__ == "__main__":
    main()