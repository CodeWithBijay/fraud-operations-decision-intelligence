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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "customer_id_analysis"
)


# ============================================================
# 2. CURRENT PRIMARY CUSTOMER GROUPING CANDIDATE
# ============================================================

# This is the leading candidate identified by the previous
# CustomerID candidate analysis.
#
# IMPORTANT:
# This is NOT being declared as the true IEEE-CIS customer.
# It is a project-level analytical grouping candidate.

PRIMARY_COLUMNS = [
    "card1",
    "addr1",
    "P_emaildomain",
]


# ============================================================
# 3. FALLBACK CANDIDATES
# ============================================================

# These weaker combinations are being evaluated ONLY as
# possible fallback mechanisms.
#
# No fallback is approved simply because it appears here.

FALLBACK_CANDIDATES = {
    "card1_addr1": [
        "card1",
        "addr1",
    ],

    "card1_p_emaildomain": [
        "card1",
        "P_emaildomain",
    ],

    "card1_only": [
        "card1",
    ],
}


# ============================================================
# 4. CHECK SOURCE FILE
# ============================================================

def check_input_file():
    """
    Confirm that the source transaction file exists.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction source file was not found:\n"
            f"{TRANSACTION_FILE}"
        )

    print("Transaction source file found.")


# ============================================================
# 5. LOAD ONLY REQUIRED DATA
# ============================================================

def load_data():
    """
    Load only the columns needed for CustomerID fallback analysis.

    isFraud is deliberately excluded.
    """

    required_columns = [
        "TransactionID",
        "TransactionDT",
        "card1",
        "addr1",
        "P_emaildomain",
    ]

    print("\nLoading required source columns...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=required_columns,
        low_memory=False,
    )

    print(
        f"Loaded {len(transactions):,} transactions."
    )

    return transactions


# ============================================================
# 6. IDENTIFY PRIMARY COMPLETE / INCOMPLETE RECORDS
# ============================================================

def identify_primary_status(transactions):
    """
    Mark whether each transaction contains all fields required
    by the current primary CustomerID grouping candidate.
    """

    data = transactions.copy()

    data["primary_complete"] = (
        data[PRIMARY_COLUMNS]
        .notna()
        .all(axis=1)
    )

    return data


# ============================================================
# 7. ANALYZE MISSING-FIELD PATTERNS
# ============================================================

def analyze_missing_patterns(transactions):
    """
    Determine exactly why transactions cannot use the
    primary grouping:
        card1 + addr1 + P_emaildomain
    """

    missing_card1 = transactions["card1"].isna()
    missing_addr1 = transactions["addr1"].isna()
    missing_email = transactions["P_emaildomain"].isna()

    complete = (
        ~missing_card1
        & ~missing_addr1
        & ~missing_email
    )

    patterns = {
        "total_transactions": int(
            len(transactions)
        ),

        "primary_complete_transactions": int(
            complete.sum()
        ),

        "primary_incomplete_transactions": int(
            (~complete).sum()
        ),

        "missing_card1_total": int(
            missing_card1.sum()
        ),

        "missing_addr1_total": int(
            missing_addr1.sum()
        ),

        "missing_p_emaildomain_total": int(
            missing_email.sum()
        ),

        "missing_only_card1": int(
            (
                missing_card1
                & ~missing_addr1
                & ~missing_email
            ).sum()
        ),

        "missing_only_addr1": int(
            (
                ~missing_card1
                & missing_addr1
                & ~missing_email
            ).sum()
        ),

        "missing_only_p_emaildomain": int(
            (
                ~missing_card1
                & ~missing_addr1
                & missing_email
            ).sum()
        ),

        "missing_card1_and_addr1_only": int(
            (
                missing_card1
                & missing_addr1
                & ~missing_email
            ).sum()
        ),

        "missing_card1_and_p_emaildomain_only": int(
            (
                missing_card1
                & ~missing_addr1
                & missing_email
            ).sum()
        ),

        "missing_addr1_and_p_emaildomain_only": int(
            (
                ~missing_card1
                & missing_addr1
                & missing_email
            ).sum()
        ),

        "missing_all_three": int(
            (
                missing_card1
                & missing_addr1
                & missing_email
            ).sum()
        ),
    }

    # Sanity check.
    pattern_total = (
        patterns["missing_only_card1"]
        + patterns["missing_only_addr1"]
        + patterns["missing_only_p_emaildomain"]
        + patterns["missing_card1_and_addr1_only"]
        + patterns[
            "missing_card1_and_p_emaildomain_only"
        ]
        + patterns[
            "missing_addr1_and_p_emaildomain_only"
        ]
        + patterns["missing_all_three"]
    )

    patterns["missing_pattern_total"] = int(
        pattern_total
    )

    patterns["missing_pattern_matches_incomplete_total"] = bool(
        pattern_total
        == patterns["primary_incomplete_transactions"]
    )

    return patterns


# ============================================================
# 8. BUILD THE COMPLETE PRIMARY REFERENCE POPULATION
# ============================================================

def build_primary_reference(transactions):
    """
    Build temporary primary grouping keys only for transactions
    where all three primary fields are available.

    These temporary keys are for analysis only.
    """

    primary = transactions.loc[
        transactions["primary_complete"]
    ].copy()

    primary["primary_group_key"] = (
        primary[PRIMARY_COLUMNS]
        .astype(str)
        .agg("|".join, axis=1)
    )

    print(
        "\nPrimary complete transactions: "
        f"{len(primary):,}"
    )

    print(
        "Distinct primary candidate groups: "
        f"{primary['primary_group_key'].nunique():,}"
    )

    return primary


# ============================================================
# 9. BUILD FALLBACK-TO-PRIMARY MAPPING
# ============================================================

def build_fallback_mapping(
    primary_reference,
    fallback_columns,
):
    """
    Determine how a weaker fallback key behaves inside the
    complete primary population.

    A fallback key is:

    UNIQUE
        if it maps to exactly one primary group.

    AMBIGUOUS
        if it maps to more than one primary group.
    """

    reference = primary_reference.copy()

    valid_mask = (
        reference[fallback_columns]
        .notna()
        .all(axis=1)
    )

    reference = reference.loc[
        valid_mask
    ].copy()

    reference["fallback_key"] = (
        reference[fallback_columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    mapping = (
        reference.groupby("fallback_key")
        ["primary_group_key"]
        .nunique()
        .rename("primary_group_count")
        .reset_index()
    )

    unique_mapping = mapping.loc[
        mapping["primary_group_count"] == 1
    ].copy()

    ambiguous_mapping = mapping.loc[
        mapping["primary_group_count"] > 1
    ].copy()

    return (
        mapping,
        unique_mapping,
        ambiguous_mapping,
    )


# ============================================================
# 10. ANALYZE ONE FALLBACK
# ============================================================

def analyze_fallback(
    transactions,
    primary_reference,
    fallback_name,
    fallback_columns,
):
    """
    Test whether incomplete transactions can be linked to an
    existing primary group using a weaker fallback key.
    """

    print(
        f"\nAnalyzing fallback: {fallback_name}"
    )

    (
        mapping,
        unique_mapping,
        ambiguous_mapping,
    ) = build_fallback_mapping(
        primary_reference,
        fallback_columns,
    )

    unique_keys = set(
        unique_mapping["fallback_key"]
    )

    ambiguous_keys = set(
        ambiguous_mapping["fallback_key"]
    )

    incomplete = transactions.loc[
        ~transactions["primary_complete"]
    ].copy()

    fallback_usable_mask = (
        incomplete[fallback_columns]
        .notna()
        .all(axis=1)
    )

    usable = incomplete.loc[
        fallback_usable_mask
    ].copy()

    unusable = incomplete.loc[
        ~fallback_usable_mask
    ].copy()

    usable["fallback_key"] = (
        usable[fallback_columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    usable["fallback_status"] = "NO_MATCH"

    usable.loc[
        usable["fallback_key"].isin(unique_keys),
        "fallback_status",
    ] = "UNIQUE_MATCH"

    usable.loc[
        usable["fallback_key"].isin(ambiguous_keys),
        "fallback_status",
    ] = "AMBIGUOUS_MATCH"

    unique_matches = usable.loc[
        usable["fallback_status"] == "UNIQUE_MATCH"
    ]

    ambiguous_matches = usable.loc[
        usable["fallback_status"] == "AMBIGUOUS_MATCH"
    ]

    no_matches = usable.loc[
        usable["fallback_status"] == "NO_MATCH"
    ]

    total_incomplete = len(incomplete)

    def percent_of_incomplete(count):
        if total_incomplete == 0:
            return 0.0

        return round(
            count / total_incomplete * 100,
            4,
        )

    summary = {
        "fallback_name": fallback_name,

        "fallback_columns": (
            " + ".join(fallback_columns)
        ),

        "primary_incomplete_transactions": int(
            total_incomplete
        ),

        "fallback_usable_transactions": int(
            len(usable)
        ),

        "fallback_unusable_transactions": int(
            len(unusable)
        ),

        "unique_existing_group_matches": int(
            len(unique_matches)
        ),

        "ambiguous_existing_group_matches": int(
            len(ambiguous_matches)
        ),

        "no_existing_group_match": int(
            len(no_matches)
        ),

        "unique_match_percent_of_incomplete": (
            percent_of_incomplete(
                len(unique_matches)
            )
        ),

        "ambiguous_match_percent_of_incomplete": (
            percent_of_incomplete(
                len(ambiguous_matches)
            )
        ),

        "no_match_percent_of_incomplete": (
            percent_of_incomplete(
                len(no_matches)
            )
        ),

        "unusable_percent_of_incomplete": (
            percent_of_incomplete(
                len(unusable)
            )
        ),

        "known_fallback_keys": int(
            len(mapping)
        ),

        "known_unique_fallback_keys": int(
            len(unique_mapping)
        ),

        "known_ambiguous_fallback_keys": int(
            len(ambiguous_mapping)
        ),
    }

    detail_columns = [
        "TransactionID",
        "TransactionDT",
        "card1",
        "addr1",
        "P_emaildomain",
        "fallback_key",
        "fallback_status",
    ]

    detail = usable[
        detail_columns
    ].copy()

    return summary, detail


# ============================================================
# 11. ANALYZE ALL FALLBACKS
# ============================================================

def analyze_all_fallbacks(
    transactions,
    primary_reference,
):
    """
    Evaluate all fallback candidates.
    """

    summaries = []
    details = {}

    for (
        fallback_name,
        fallback_columns,
    ) in FALLBACK_CANDIDATES.items():

        summary, detail = analyze_fallback(
            transactions,
            primary_reference,
            fallback_name,
            fallback_columns,
        )

        summaries.append(summary)

        details[fallback_name] = detail

    summary_df = pd.DataFrame(
        summaries
    )

    return summary_df, details


# ============================================================
# 12. CREATE OVERALL UNRESOLVED RECORD REPORT
# ============================================================

def create_unresolved_report(
    transactions,
    fallback_details,
):
    """
    Create a transaction-level view showing whether each
    incomplete transaction obtains a unique match from any
    tested fallback.

    This does NOT assign a CustomerID.
    """

    incomplete = transactions.loc[
        ~transactions["primary_complete"]
    ][
        [
            "TransactionID",
            "TransactionDT",
            "card1",
            "addr1",
            "P_emaildomain",
        ]
    ].copy()

    incomplete["resolved_by_any_tested_fallback"] = False

    incomplete["unique_fallback_options"] = 0

    for fallback_name, detail in fallback_details.items():

        unique_ids = set(
            detail.loc[
                detail["fallback_status"]
                == "UNIQUE_MATCH",
                "TransactionID",
            ]
        )

        match_column = (
            f"{fallback_name}_unique_match"
        )

        incomplete[match_column] = (
            incomplete["TransactionID"]
            .isin(unique_ids)
        )

        incomplete[
            "unique_fallback_options"
        ] += incomplete[
            match_column
        ].astype(int)

        incomplete.loc[
            incomplete[match_column],
            "resolved_by_any_tested_fallback",
        ] = True

    unresolved = incomplete.loc[
        ~incomplete[
            "resolved_by_any_tested_fallback"
        ]
    ].copy()

    return incomplete, unresolved


# ============================================================
# 13. SAVE OUTPUTS
# ============================================================

def save_results(
    missing_patterns,
    fallback_summary,
    fallback_details,
    incomplete_summary,
    unresolved,
):
    """
    Save every analysis output.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Missingness summary.
    missing_json = (
        OUTPUT_DIR
        / "customer_missing_patterns.json"
    )

    with missing_json.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            missing_patterns,
            file,
            indent=4,
        )

    # Fallback summary.
    fallback_summary_file = (
        OUTPUT_DIR
        / "customer_fallback_analysis.csv"
    )

    fallback_summary.to_csv(
        fallback_summary_file,
        index=False,
    )

    # Detail file for every tested fallback.
    for (
        fallback_name,
        detail,
    ) in fallback_details.items():

        detail_file = (
            OUTPUT_DIR
            / f"{fallback_name}_details.csv"
        )

        detail.to_csv(
            detail_file,
            index=False,
        )

    # All incomplete transactions.
    incomplete_file = (
        OUTPUT_DIR
        / "customer_incomplete_transactions.csv"
    )

    incomplete_summary.to_csv(
        incomplete_file,
        index=False,
    )

    # Still unresolved after all tested fallbacks.
    unresolved_file = (
        OUTPUT_DIR
        / "customer_unresolved_transactions.csv"
    )

    unresolved.to_csv(
        unresolved_file,
        index=False,
    )

    print("\nResults saved under:")
    print(OUTPUT_DIR)


# ============================================================
# 14. SANITY CHECKS
# ============================================================

def run_sanity_checks(
    transactions,
    missing_patterns,
    fallback_summary,
    incomplete_summary,
    unresolved,
):
    """
    Verify that the analysis itself is internally consistent.
    """

    print("\nRunning sanity checks...")

    total_transactions = (
        missing_patterns["total_transactions"]
    )

    expected_incomplete = (
        missing_patterns[
            "primary_incomplete_transactions"
        ]
    )

    assert total_transactions == len(
        transactions
    ), (
        "Total transaction count does not match."
    )

    assert (
        missing_patterns[
            "missing_pattern_matches_incomplete_total"
        ]
        is True
    ), (
        "Missingness pattern counts do not add up "
        "to the incomplete transaction count."
    )

    assert len(incomplete_summary) == (
        expected_incomplete
    ), (
        "Incomplete transaction count does not match."
    )

    assert len(unresolved) <= (
        expected_incomplete
    ), (
        "Unresolved transaction count is impossible."
    )

    for _, row in (
        fallback_summary.iterrows()
    ):

        category_total = (
            row[
                "fallback_unusable_transactions"
            ]
            + row[
                "unique_existing_group_matches"
            ]
            + row[
                "ambiguous_existing_group_matches"
            ]
            + row[
                "no_existing_group_match"
            ]
        )

        assert category_total == (
            expected_incomplete
        ), (
            f"Fallback counts do not add up for "
            f"{row['fallback_name']}."
        )

    print("Sanity checks passed.")


# ============================================================
# 15. PRINT HUMAN-READABLE SUMMARY
# ============================================================

def print_summary(
    missing_patterns,
    fallback_summary,
    unresolved,
):
    """
    Print the most important results.
    """

    print("\n" + "=" * 70)
    print("MISSING-FIELD PATTERNS")
    print("=" * 70)

    for key, value in missing_patterns.items():

        if isinstance(value, bool):
            print(
                f"{key}: {value}"
            )

        else:
            print(
                f"{key}: {value:,}"
            )

    print("\n" + "=" * 70)
    print("FALLBACK CANDIDATE SUMMARY")
    print("=" * 70)

    print(
        fallback_summary.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("OVERALL UNRESOLVED STATUS")
    print("=" * 70)

    print(
        "Primary-incomplete transactions: "
        f"{missing_patterns['primary_incomplete_transactions']:,}"
    )

    print(
        "Transactions unresolved by all "
        "tested fallbacks: "
        f"{len(unresolved):,}"
    )

    print(
        "\nThese unresolved records have NOT been "
        "assigned to an invented customer."
    )


# ============================================================
# 16. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 70)
    print("CUSTOMERID FALLBACK ANALYSIS")
    print("=" * 70)

    check_input_file()

    transactions = load_data()

    transactions = (
        identify_primary_status(
            transactions
        )
    )

    print(
        "\nAnalyzing missing-field patterns..."
    )

    missing_patterns = (
        analyze_missing_patterns(
            transactions
        )
    )

    print(
        "\nBuilding complete primary reference..."
    )

    primary_reference = (
        build_primary_reference(
            transactions
        )
    )

    (
        fallback_summary,
        fallback_details,
    ) = analyze_all_fallbacks(
        transactions,
        primary_reference,
    )

    (
        incomplete_summary,
        unresolved,
    ) = create_unresolved_report(
        transactions,
        fallback_details,
    )

    run_sanity_checks(
        transactions,
        missing_patterns,
        fallback_summary,
        incomplete_summary,
        unresolved,
    )

    save_results(
        missing_patterns,
        fallback_summary,
        fallback_details,
        incomplete_summary,
        unresolved,
    )

    print_summary(
        missing_patterns,
        fallback_summary,
        unresolved,
    )

    print("\n" + "=" * 70)
    print("CUSTOMERID FALLBACK ANALYSIS COMPLETED")
    print("=" * 70)

    print(
        "\nNo CustomerID was generated."
    )

    print(
        "No source data were modified."
    )

    print(
        "isFraud was not loaded or used."
    )


if __name__ == "__main__":
    main()