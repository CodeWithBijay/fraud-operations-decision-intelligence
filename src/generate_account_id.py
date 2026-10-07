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

CUSTOMER_MAPPING_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "customer"
    / "transaction_customer_mapping.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "account"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "account_id_generation"
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
# 3. STABLE SYNTHETIC ACCOUNT ID
# ============================================================

def create_account_id(group_type, customer_id, key):
    """
    Create a deterministic synthetic AccountID.

    The CustomerID is included so accounts remain nested
    within their analytical customer.

    Same input = same AccountID.
    """

    input_value = (
        f"{group_type}|"
        f"{customer_id}|"
        f"{key}"
    )

    digest = hashlib.sha256(
        input_value.encode("utf-8")
    ).hexdigest()[:16]

    return f"ACCT_{digest.upper()}"


# ============================================================
# 4. CHECK REQUIRED FILES
# ============================================================

def check_files():

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction source file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    if not CUSTOMER_MAPPING_FILE.exists():
        raise FileNotFoundError(
            "Customer mapping file not found:\n"
            f"{CUSTOMER_MAPPING_FILE}"
        )

    print("Required files found.")


# ============================================================
# 5. LOAD SOURCE DATA
# ============================================================

def load_data():
    """
    Load only information required for AccountID generation.

    isFraud is deliberately not loaded.
    """

    print("\nLoading account source fields...")

    transactions = pd.read_csv(
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

    print("Loading validated CustomerID mapping...")

    customer_mapping = pd.read_csv(
        CUSTOMER_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "CustomerID",
        ],
        low_memory=False,
    )

    return transactions, customer_mapping


# ============================================================
# 6. JOIN CUSTOMERID
# ============================================================

def attach_customer_id(
    transactions,
    customer_mapping,
):
    """
    Attach CustomerID to each transaction.

    AccountID is always generated within CustomerID.
    """

    data = transactions.merge(
        customer_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    if len(data) != len(transactions):
        raise ValueError(
            "Transaction count changed after CustomerID join."
        )

    missing_customers = int(
        data["CustomerID"].isna().sum()
    )

    if missing_customers != 0:
        raise ValueError(
            f"{missing_customers} transactions "
            "have no CustomerID."
        )

    print(
        f"CustomerID joined to {len(data):,} transactions."
    )

    return data


# ============================================================
# 7. BUILD PRIMARY ACCOUNTS
# ============================================================

def build_primary_accounts(data):
    """
    Create primary analytical accounts from:

    CustomerID
        +
    card1 + card2 + card3 + card5
    """

    complete_mask = (
        data[ACCOUNT_COLUMNS]
        .notna()
        .all(axis=1)
    )

    primary = data.loc[
        complete_mask
    ].copy()

    primary["account_source_key"] = (
        primary[ACCOUNT_COLUMNS]
        .astype(str)
        .agg("|".join, axis=1)
    )

    primary["AccountID"] = primary.apply(
        lambda row: create_account_id(
            "PRIMARY",
            row["CustomerID"],
            row["account_source_key"],
        ),
        axis=1,
    )

    primary["AccountID_method"] = "PRIMARY"

    print(
        "\nPrimary-complete transactions: "
        f"{len(primary):,}"
    )

    print(
        "Primary analytical accounts: "
        f"{primary['AccountID'].nunique():,}"
    )

    return primary


# ============================================================
# 8. BUILD WITHIN-CUSTOMER FALLBACK REFERENCE
# ============================================================

def build_unique_fallback_map(
    primary,
    fallback_columns,
):
    """
    Build a fallback mapping that is valid only when:

    CustomerID + available fallback fields

    maps to exactly ONE existing AccountID.

    This prevents fallback linking across customers.
    """

    reference = primary.copy()

    reference["fallback_source_key"] = (
        reference[fallback_columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    reference["fallback_key"] = (
        reference["CustomerID"].astype(str)
        + "|"
        + reference["fallback_source_key"]
    )

    account_counts = (
        reference.groupby(
            "fallback_key"
        )["AccountID"]
        .nunique()
    )

    unique_keys = account_counts[
        account_counts == 1
    ].index

    unique_reference = (
        reference[
            reference["fallback_key"]
            .isin(unique_keys)
        ][
            [
                "fallback_key",
                "AccountID",
            ]
        ]
        .drop_duplicates(
            subset=["fallback_key"]
        )
    )

    return dict(
        zip(
            unique_reference["fallback_key"],
            unique_reference["AccountID"],
        )
    )


# ============================================================
# 9. CREATE AVAILABLE-FIELD SIGNATURE
# ============================================================

def build_available_signature(row):
    """
    Build a deterministic signature from the available
    approved account fields.

    Missing values are explicitly represented.

    This is used only when a transaction cannot safely
    reuse an existing analytical account.
    """

    parts = []

    for column in ACCOUNT_COLUMNS:

        value = row[column]

        if pd.isna(value):
            parts.append(
                f"{column}=MISSING"
            )
        else:
            parts.append(
                f"{column}={value}"
            )

    return "|".join(parts)


# ============================================================
# 10. GENERATE ACCOUNT IDS
# ============================================================

def generate_account_ids(
    data,
    primary,
):
    """
    Apply the AccountID methodology.

    Complete signature:
        -> PRIMARY

    Incomplete signature:
        -> test increasingly weaker within-customer mappings

    Unique existing account:
        -> reuse AccountID

    No unique match:
        -> separate unresolved analytical account

    No random account assignment occurs.
    """

    result = data.copy()

    result["AccountID"] = pd.NA
    result["AccountID_method"] = pd.NA

    # --------------------------------------------------------
    # PRIMARY
    # --------------------------------------------------------

    primary_map = dict(
        zip(
            primary["TransactionID"],
            primary["AccountID"],
        )
    )

    primary_mask = (
        result["TransactionID"]
        .isin(primary_map)
    )

    result.loc[
        primary_mask,
        "AccountID",
    ] = (
        result.loc[
            primary_mask,
            "TransactionID",
        ]
        .map(primary_map)
    )

    result.loc[
        primary_mask,
        "AccountID_method",
    ] = "PRIMARY"

    # --------------------------------------------------------
    # BUILD FALLBACK HIERARCHY
    # --------------------------------------------------------

    fallback_definitions = [
        (
            "FALLBACK_CARD1_CARD2_CARD3",
            [
                "card1",
                "card2",
                "card3",
            ],
        ),
        (
            "FALLBACK_CARD1_CARD2_CARD5",
            [
                "card1",
                "card2",
                "card5",
            ],
        ),
        (
            "FALLBACK_CARD1_CARD3_CARD5",
            [
                "card1",
                "card3",
                "card5",
            ],
        ),
        (
            "FALLBACK_CARD1_CARD2",
            [
                "card1",
                "card2",
            ],
        ),
        (
            "FALLBACK_CARD1_CARD3",
            [
                "card1",
                "card3",
            ],
        ),
        (
            "FALLBACK_CARD1_CARD5",
            [
                "card1",
                "card5",
            ],
        ),
    ]

    # --------------------------------------------------------
    # APPLY FALLBACKS ONE AT A TIME
    # --------------------------------------------------------

    for (
        method_name,
        fallback_columns,
    ) in fallback_definitions:

        fallback_map = (
            build_unique_fallback_map(
                primary,
                fallback_columns,
            )
        )

        unresolved_mask = (
            result["AccountID"].isna()
            & result[fallback_columns]
            .notna()
            .all(axis=1)
        )

        if not unresolved_mask.any():
            continue

        candidate = result.loc[
            unresolved_mask
        ].copy()

        candidate[
            "fallback_source_key"
        ] = (
            candidate[fallback_columns]
            .astype(str)
            .agg("|".join, axis=1)
        )

        candidate["fallback_key"] = (
            candidate["CustomerID"].astype(str)
            + "|"
            + candidate["fallback_source_key"]
        )

        matched_account = (
            candidate["fallback_key"]
            .map(fallback_map)
        )

        matched_mask = (
            matched_account.notna()
        )

        matched_indices = (
            candidate.index[
                matched_mask
            ]
        )

        result.loc[
            matched_indices,
            "AccountID",
        ] = matched_account.loc[
            matched_mask
        ]

        result.loc[
            matched_indices,
            "AccountID_method",
        ] = method_name

    # --------------------------------------------------------
    # UNRESOLVED ACCOUNTS
    # --------------------------------------------------------

    unresolved_mask = (
        result["AccountID"].isna()
    )

    unresolved = result.loc[
        unresolved_mask
    ].copy()

    if len(unresolved) > 0:

        unresolved[
            "available_signature"
        ] = unresolved.apply(
            build_available_signature,
            axis=1,
        )

        unresolved["generated_account_id"] = (
            unresolved.apply(
                lambda row: create_account_id(
                    "UNRESOLVED",
                    row["CustomerID"],
                    row[
                        "available_signature"
                    ],
                ),
                axis=1,
            )
        )

        result.loc[
            unresolved.index,
            "AccountID",
        ] = unresolved[
            "generated_account_id"
        ]

        result.loc[
            unresolved.index,
            "AccountID_method",
        ] = "UNRESOLVED_AVAILABLE_SIGNATURE"

    return result


# ============================================================
# 11. GENERATION-STAGE SAFETY CHECKS
# ============================================================

def run_generation_checks(result):
    """
    These are immediate generator safety checks.

    They are NOT the separate AccountID validation phase.
    """

    print("\nRunning generation safety checks...")

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
        "Missing CustomerID found."
    )

    assert (
        result["AccountID"]
        .notna()
        .all()
    ), (
        "Missing AccountID found."
    )

    assert (
        result["AccountID_method"]
        .notna()
        .all()
    ), (
        "Missing AccountID method found."
    )

    # Every AccountID must belong to one CustomerID.
    account_customer_counts = (
        result.groupby(
            "AccountID"
        )["CustomerID"]
        .nunique()
    )

    cross_customer_accounts = int(
        (
            account_customer_counts > 1
        ).sum()
    )

    assert cross_customer_accounts == 0, (
        "One or more AccountIDs belong to "
        "multiple CustomerIDs."
    )

    print("Generation safety checks passed.")


# ============================================================
# 12. CREATE GENERATION SUMMARY
# ============================================================

def create_summary(result):
    """
    Summarize the generated analytical account population.
    """

    method_counts = (
        result[
            "AccountID_method"
        ]
        .value_counts()
        .to_dict()
    )

    account_sizes = (
        result.groupby(
            "AccountID"
        )
        .size()
    )

    customer_account_counts = (
        result[
            [
                "CustomerID",
                "AccountID",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "CustomerID"
        )
        .size()
    )

    customers_with_multiple_accounts = int(
        (
            customer_account_counts > 1
        ).sum()
    )

    return {
        "transaction_rows": int(
            len(result)
        ),

        "distinct_customer_ids": int(
            result[
                "CustomerID"
            ].nunique()
        ),

        "distinct_account_ids": int(
            result[
                "AccountID"
            ].nunique()
        ),

        "missing_account_ids": int(
            result[
                "AccountID"
            ].isna()
            .sum()
        ),

        "account_id_method_counts": {
            key: int(value)
            for key, value
            in method_counts.items()
        },

        "account_group_size": {
            "minimum": int(
                account_sizes.min()
            ),

            "maximum": int(
                account_sizes.max()
            ),

            "mean": round(
                float(
                    account_sizes.mean()
                ),
                4,
            ),

            "median": round(
                float(
                    account_sizes.median()
                ),
                4,
            ),

            "percentile_95": round(
                float(
                    account_sizes.quantile(
                        0.95
                    )
                ),
                4,
            ),

            "percentile_99": round(
                float(
                    account_sizes.quantile(
                        0.99
                    )
                ),
                4,
            ),
        },

        "accounts_per_customer": {
            "minimum": int(
                customer_account_counts.min()
            ),

            "maximum": int(
                customer_account_counts.max()
            ),

            "mean": round(
                float(
                    customer_account_counts.mean()
                ),
                4,
            ),

            "median": round(
                float(
                    customer_account_counts.median()
                ),
                4,
            ),

            "percentile_95": round(
                float(
                    customer_account_counts.quantile(
                        0.95
                    )
                ),
                4,
            ),

            "percentile_99": round(
                float(
                    customer_account_counts.quantile(
                        0.99
                    )
                ),
                4,
            ),

            "customers_with_multiple_accounts": (
                customers_with_multiple_accounts
            ),

            "customers_with_multiple_accounts_percent": round(
                customers_with_multiple_accounts
                / len(
                    customer_account_counts
                )
                * 100,
                4,
            ),
        },
    }


# ============================================================
# 13. SAVE OUTPUTS
# ============================================================

def save_results(
    result,
    summary,
):
    """
    Save transaction-to-account mapping and compact summary.

    Raw source files are not modified.
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
        / "transaction_account_mapping.csv"
    )

    summary_file = (
        REPORT_DIR
        / "account_id_generation_summary.json"
    )

    result[
        [
            "TransactionID",
            "TransactionDT",
            "CustomerID",
            "AccountID",
            "AccountID_method",
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

    print("\nAccount mapping saved to:")
    print(mapping_file)

    print("\nGeneration summary saved to:")
    print(summary_file)


# ============================================================
# 14. PRINT SUMMARY
# ============================================================

def print_summary(summary):

    print("\n" + "=" * 70)
    print("ACCOUNTID GENERATION SUMMARY")
    print("=" * 70)

    print(
        "\nTransactions: "
        f"{summary['transaction_rows']:,}"
    )

    print(
        "Distinct CustomerIDs: "
        f"{summary['distinct_customer_ids']:,}"
    )

    print(
        "Distinct AccountIDs: "
        f"{summary['distinct_account_ids']:,}"
    )

    print(
        "Missing AccountIDs: "
        f"{summary['missing_account_ids']:,}"
    )

    print("\nAccountID methods:")

    for method, count in (
        summary[
            "account_id_method_counts"
        ].items()
    ):

        print(
            f"  {method}: {count:,}"
        )

    print("\nAccount group sizes:")

    for key, value in (
        summary[
            "account_group_size"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )

    print("\nAccounts per customer:")

    for key, value in (
        summary[
            "accounts_per_customer"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )


# ============================================================
# 15. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("ACCOUNTID GENERATION")
    print("=" * 70)

    print(
        "\nSource-informed deterministic "
        "analytical account generation"
    )

    print(
        "isFraud is not loaded or used."
    )

    check_files()

    (
        transactions,
        customer_mapping,
    ) = load_data()

    data = attach_customer_id(
        transactions,
        customer_mapping,
    )

    print(
        "\nBuilding primary analytical accounts..."
    )

    primary = build_primary_accounts(
        data
    )

    print(
        "\nGenerating AccountID..."
    )

    result = generate_account_ids(
        data,
        primary,
    )

    run_generation_checks(
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
    print("ACCOUNTID GENERATION COMPLETED")
    print("=" * 70)

    print(
        "\nNo source file was modified."
    )

    print(
        "No random AccountID assignment was used."
    )

    print(
        "Generated AccountIDs are project-level "
        "analytical identifiers."
    )


if __name__ == "__main__":
    main()