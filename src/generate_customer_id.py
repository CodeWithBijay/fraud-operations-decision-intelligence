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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "customer"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "customer_id_generation"
)


# ============================================================
# 2. APPROVED CUSTOMER GROUPING FIELDS
# ============================================================

PRIMARY_COLUMNS = [
    "card1",
    "addr1",
    "P_emaildomain",
]


# ============================================================
# 3. STABLE SYNTHETIC ID FUNCTION
# ============================================================

def create_customer_id(group_type, key):
    """
    Create a stable synthetic CustomerID from a grouping key.

    The generated identifier does not expose the original
    grouping values directly.

    Same group_type + same key = same CustomerID.
    """

    input_value = f"{group_type}|{key}"

    digest = hashlib.sha256(
        input_value.encode("utf-8")
    ).hexdigest()[:16]

    return f"CUST_{digest.upper()}"


# ============================================================
# 4. CHECK INPUT FILE
# ============================================================

def check_input_file():
    """
    Confirm that the original transaction file exists.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction file was not found:\n"
            f"{TRANSACTION_FILE}"
        )

    print("Transaction source file found.")


# ============================================================
# 5. LOAD REQUIRED SOURCE COLUMNS
# ============================================================

def load_data():
    """
    Load only the source fields required by the approved
    CustomerID methodology.

    isFraud is deliberately NOT loaded.
    """

    columns = [
        "TransactionID",
        "TransactionDT",
        "card1",
        "addr1",
        "P_emaildomain",
    ]

    print("\nLoading CustomerID source columns...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=columns,
        low_memory=False,
    )

    print(
        f"Loaded {len(transactions):,} transactions."
    )

    return transactions


# ============================================================
# 6. BUILD PRIMARY CUSTOMER REFERENCE
# ============================================================

def build_primary_reference(transactions):
    """
    Create primary analytical customer groups from:

        card1 + addr1 + P_emaildomain

    Only transactions containing all three fields are used
    to establish primary groups.
    """

    primary_complete_mask = (
        transactions[PRIMARY_COLUMNS]
        .notna()
        .all(axis=1)
    )

    primary = transactions.loc[
        primary_complete_mask
    ].copy()

    primary["source_group_key"] = (
        primary[PRIMARY_COLUMNS]
        .astype(str)
        .agg("|".join, axis=1)
    )

    primary["CustomerID"] = (
        primary["source_group_key"]
        .map(
            lambda key:
            create_customer_id(
                "PRIMARY",
                key,
            )
        )
    )

    primary["CustomerID_method"] = (
        "PRIMARY"
    )

    return primary


# ============================================================
# 7. CREATE UNIQUE FALLBACK MAP
# ============================================================

def build_unique_fallback_map(
    primary,
    fallback_columns,
):
    """
    Create mappings from a weaker source signature to an
    existing primary CustomerID.

    A fallback is allowed ONLY when one fallback key maps to
    exactly one primary CustomerID.
    """

    reference = primary.copy()

    reference["fallback_key"] = (
        reference[fallback_columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    customer_counts = (
        reference
        .groupby("fallback_key")["CustomerID"]
        .nunique()
    )

    unique_keys = customer_counts[
        customer_counts == 1
    ].index

    unique_reference = (
        reference[
            reference["fallback_key"]
            .isin(unique_keys)
        ][
            [
                "fallback_key",
                "CustomerID",
            ]
        ]
        .drop_duplicates(
            subset=["fallback_key"]
        )
    )

    return dict(
        zip(
            unique_reference["fallback_key"],
            unique_reference["CustomerID"],
        )
    )


# ============================================================
# 8. GENERATE CUSTOMER IDS
# ============================================================

def generate_customer_ids(
    transactions,
    primary,
):
    """
    Apply the documented CustomerID hierarchy.

    Rule 1:
        Complete card1 + addr1 + P_emaildomain
        -> primary analytical group

    Rule 2:
        Missing P_emaildomain
        -> try unique card1 + addr1 mapping
        -> otherwise create separate unresolved group

    Rule 3:
        Missing addr1
        -> try unique card1 + P_emaildomain mapping
        -> otherwise create separate unresolved group

    Rule 4:
        Missing both addr1 and P_emaildomain
        -> isolated analytical identity

    No random assignment is performed.
    """

    result = transactions.copy()

    result["CustomerID"] = pd.NA

    result["CustomerID_method"] = pd.NA


    # ========================================================
    # PRIMARY GROUPS
    # ========================================================

    primary_id_map = dict(
        zip(
            primary["TransactionID"],
            primary["CustomerID"],
        )
    )

    primary_mask = (
        result["TransactionID"]
        .isin(primary_id_map)
    )

    result.loc[
        primary_mask,
        "CustomerID",
    ] = (
        result.loc[
            primary_mask,
            "TransactionID",
        ]
        .map(primary_id_map)
    )

    result.loc[
        primary_mask,
        "CustomerID_method",
    ] = "PRIMARY"


    # ========================================================
    # BUILD DEFINED UNIQUE FALLBACK MAPS
    # ========================================================

    card_addr_map = (
        build_unique_fallback_map(
            primary,
            [
                "card1",
                "addr1",
            ],
        )
    )

    card_email_map = (
        build_unique_fallback_map(
            primary,
            [
                "card1",
                "P_emaildomain",
            ],
        )
    )


    # ========================================================
    # MISSING EMAIL ONLY
    # ========================================================

    missing_email_mask = (
        result["CustomerID"].isna()
        & result["card1"].notna()
        & result["addr1"].notna()
        & result["P_emaildomain"].isna()
    )

    missing_email = result.loc[
        missing_email_mask
    ].copy()

    missing_email["fallback_key"] = (
        missing_email[
            [
                "card1",
                "addr1",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    unique_existing_id = (
        missing_email["fallback_key"]
        .map(card_addr_map)
    )

    unique_match_mask = (
        unique_existing_id.notna()
    )

    matched_indices = (
        missing_email.index[
            unique_match_mask
        ]
    )

    result.loc[
        matched_indices,
        "CustomerID",
    ] = unique_existing_id.loc[
        unique_match_mask
    ]

    result.loc[
        matched_indices,
        "CustomerID_method",
    ] = "FALLBACK_CARD_ADDR_UNIQUE"


    # ========================================================
    # UNRESOLVED EMAIL-MISSING GROUPS
    # ========================================================

    unresolved_email = (
        missing_email.loc[
            ~unique_match_mask
        ].copy()
    )

    unresolved_email[
        "unresolved_key"
    ] = (
        unresolved_email[
            [
                "card1",
                "addr1",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    unresolved_email_ids = (
        unresolved_email[
            "unresolved_key"
        ]
        .map(
            lambda key:
            create_customer_id(
                "UNRESOLVED_MISSING_EMAIL",
                key,
            )
        )
    )

    result.loc[
        unresolved_email.index,
        "CustomerID",
    ] = unresolved_email_ids

    result.loc[
        unresolved_email.index,
        "CustomerID_method",
    ] = "UNRESOLVED_CARD_ADDR"


    # ========================================================
    # MISSING ADDRESS ONLY
    # ========================================================

    missing_addr_mask = (
        result["CustomerID"].isna()
        & result["card1"].notna()
        & result["addr1"].isna()
        & result["P_emaildomain"].notna()
    )

    missing_addr = result.loc[
        missing_addr_mask
    ].copy()

    missing_addr["fallback_key"] = (
        missing_addr[
            [
                "card1",
                "P_emaildomain",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    unique_existing_id = (
        missing_addr["fallback_key"]
        .map(card_email_map)
    )

    unique_match_mask = (
        unique_existing_id.notna()
    )

    matched_indices = (
        missing_addr.index[
            unique_match_mask
        ]
    )

    result.loc[
        matched_indices,
        "CustomerID",
    ] = unique_existing_id.loc[
        unique_match_mask
    ]

    result.loc[
        matched_indices,
        "CustomerID_method",
    ] = "FALLBACK_CARD_EMAIL_UNIQUE"


    # ========================================================
    # UNRESOLVED ADDRESS-MISSING GROUPS
    # ========================================================

    unresolved_addr = (
        missing_addr.loc[
            ~unique_match_mask
        ].copy()
    )

    unresolved_addr[
        "unresolved_key"
    ] = (
        unresolved_addr[
            [
                "card1",
                "P_emaildomain",
            ]
        ]
        .astype(str)
        .agg("|".join, axis=1)
    )

    unresolved_addr_ids = (
        unresolved_addr[
            "unresolved_key"
        ]
        .map(
            lambda key:
            create_customer_id(
                "UNRESOLVED_MISSING_ADDR",
                key,
            )
        )
    )

    result.loc[
        unresolved_addr.index,
        "CustomerID",
    ] = unresolved_addr_ids

    result.loc[
        unresolved_addr.index,
        "CustomerID_method",
    ] = "UNRESOLVED_CARD_EMAIL"


    # ========================================================
    # MISSING BOTH ADDRESS AND EMAIL
    # ========================================================

    weak_information_mask = (
        result["CustomerID"].isna()
        & result["card1"].notna()
        & result["addr1"].isna()
        & result["P_emaildomain"].isna()
    )

    weak_records = result.loc[
        weak_information_mask
    ].copy()

    # IMPORTANT:
    #
    # card1 alone was shown to be too ambiguous.
    #
    # Therefore these transactions do not share a CustomerID
    # simply because they have the same card1.
    #
    # TransactionID is included so each record receives an
    # isolated analytical identity.

    isolated_ids = (
        weak_records["TransactionID"]
        .astype(str)
        .map(
            lambda transaction_id:
            create_customer_id(
                "ISOLATED",
                transaction_id,
            )
        )
    )

    result.loc[
        weak_records.index,
        "CustomerID",
    ] = isolated_ids

    result.loc[
        weak_records.index,
        "CustomerID_method",
    ] = "ISOLATED_WEAK_INFORMATION"


    # ========================================================
    # FINAL SAFETY FALLBACK
    # ========================================================

    # We do not expect unresolved records because card1 had
    # complete coverage in the audited source data.
    #
    # If a future source version differs, we still refuse to
    # randomly assign the transaction to another customer.

    still_unresolved_mask = (
        result["CustomerID"].isna()
    )

    unresolved_records = result.loc[
        still_unresolved_mask
    ].copy()

    if len(unresolved_records) > 0:

        safety_ids = (
            unresolved_records[
                "TransactionID"
            ]
            .astype(str)
            .map(
                lambda transaction_id:
                create_customer_id(
                    "ISOLATED_SAFETY",
                    transaction_id,
                )
            )
        )

        result.loc[
            unresolved_records.index,
            "CustomerID",
        ] = safety_ids

        result.loc[
            unresolved_records.index,
            "CustomerID_method",
        ] = "ISOLATED_SAFETY"

    return result


# ============================================================
# 9. VALIDATE GENERATED CUSTOMER IDS
# ============================================================

def validate_generated_ids(result):
    """
    Run immediate integrity checks.

    This is generation-stage safety validation.
    Formal project validation comes later.
    """

    print("\nRunning CustomerID integrity checks...")

    assert len(result) > 0, (
        "Generated output is empty."
    )

    assert (
        result["TransactionID"]
        .notna()
        .all()
    ), (
        "TransactionID contains missing values."
    )

    assert (
        result["TransactionID"]
        .is_unique
    ), (
        "TransactionID is not unique."
    )

    assert (
        result["CustomerID"]
        .notna()
        .all()
    ), (
        "One or more transactions have no CustomerID."
    )

    assert (
        result["CustomerID_method"]
        .notna()
        .all()
    ), (
        "One or more transactions have no CustomerID method."
    )

    valid_methods = {
        "PRIMARY",
        "FALLBACK_CARD_ADDR_UNIQUE",
        "UNRESOLVED_CARD_ADDR",
        "FALLBACK_CARD_EMAIL_UNIQUE",
        "UNRESOLVED_CARD_EMAIL",
        "ISOLATED_WEAK_INFORMATION",
        "ISOLATED_SAFETY",
    }

    observed_methods = set(
        result["CustomerID_method"]
        .unique()
    )

    unexpected_methods = (
        observed_methods
        - valid_methods
    )

    assert not unexpected_methods, (
        "Unexpected CustomerID methods found: "
        f"{unexpected_methods}"
    )

    print("CustomerID integrity checks passed.")


# ============================================================
# 10. CREATE GENERATION SUMMARY
# ============================================================

def create_summary(result):
    """
    Summarize the generated CustomerID population.
    """

    method_counts = (
        result["CustomerID_method"]
        .value_counts()
        .to_dict()
    )

    customer_sizes = (
        result.groupby("CustomerID")
        .size()
    )

    summary = {
        "transaction_rows": int(
            len(result)
        ),

        "distinct_customer_ids": int(
            result["CustomerID"]
            .nunique()
        ),

        "missing_customer_ids": int(
            result["CustomerID"]
            .isna()
            .sum()
        ),

        "customer_id_method_counts": {
            key: int(value)
            for key, value
            in method_counts.items()
        },

        "customer_group_size": {
            "minimum": int(
                customer_sizes.min()
            ),

            "maximum": int(
                customer_sizes.max()
            ),

            "mean": round(
                float(
                    customer_sizes.mean()
                ),
                4,
            ),

            "median": round(
                float(
                    customer_sizes.median()
                ),
                4,
            ),

            "percentile_95": round(
                float(
                    customer_sizes.quantile(
                        0.95
                    )
                ),
                4,
            ),

            "percentile_99": round(
                float(
                    customer_sizes.quantile(
                        0.99
                    )
                ),
                4,
            ),
        },
    }

    return summary


# ============================================================
# 11. SAVE OUTPUTS
# ============================================================

def save_results(
    result,
    summary,
):
    """
    Save generated CustomerID mapping and summary.

    Raw source data are not modified.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    mapping_file = (
        OUTPUT_DIR
        / "transaction_customer_mapping.csv"
    )

    summary_file = (
        REPORT_DIR
        / "customer_id_generation_summary.json"
    )

    # Save only the generated relationship/provenance output.
    #
    # We do not create another unnecessary copy of all
    # IEEE-CIS transaction columns here.

    result[
        [
            "TransactionID",
            "TransactionDT",
            "CustomerID",
            "CustomerID_method",
        ]
    ].to_csv(
        mapping_file,
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

    print("\nGenerated mapping saved to:")
    print(mapping_file)

    print("\nGeneration summary saved to:")
    print(summary_file)


# ============================================================
# 12. PRINT SUMMARY
# ============================================================

def print_summary(summary):
    """
    Display the key generation results.
    """

    print("\n" + "=" * 70)
    print("CUSTOMERID GENERATION SUMMARY")
    print("=" * 70)

    print(
        "\nTransactions:"
    )

    print(
        f"{summary['transaction_rows']:,}"
    )

    print(
        "\nDistinct CustomerIDs:"
    )

    print(
        f"{summary['distinct_customer_ids']:,}"
    )

    print(
        "\nMissing CustomerIDs:"
    )

    print(
        f"{summary['missing_customer_ids']:,}"
    )

    print(
        "\nCustomerID methods:"
    )

    for method, count in (
        summary[
            "customer_id_method_counts"
        ].items()
    ):

        print(
            f"  {method}: {count:,}"
        )

    print(
        "\nCustomer group sizes:"
    )

    for name, value in (
        summary[
            "customer_group_size"
        ].items()
    ):

        print(
            f"  {name}: {value}"
        )


# ============================================================
# 13. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("CUSTOMERID GENERATION")
    print("=" * 70)

    print(
        "\nMethod:"
    )

    print(
        "Source-informed deterministic analytical grouping"
    )

    print(
        "\nisFraud is NOT loaded or used."
    )

    check_input_file()

    transactions = load_data()

    print(
        "\nBuilding primary customer reference..."
    )

    primary = build_primary_reference(
        transactions
    )

    print(
        "\nGenerating CustomerID..."
    )

    result = generate_customer_ids(
        transactions,
        primary,
    )

    validate_generated_ids(
        result
    )

    summary = create_summary(
        result
    )

    save_results(
        result,
        summary,
    )

    print_summary(
        summary
    )

    print("\n" + "=" * 70)
    print("CUSTOMERID GENERATION COMPLETED")
    print("=" * 70)

    print(
        "\nThe original IEEE-CIS file was not modified."
    )

    print(
        "No random CustomerID assignment was used."
    )

    print(
        "Generated CustomerIDs are analytical identifiers,"
    )

    print(
        "not recovered real-world customer identities."
    )


if __name__ == "__main__":
    main()