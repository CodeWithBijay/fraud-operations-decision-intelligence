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
    / "merchant_id_analysis"
)


# ============================================================
# 2. MERCHANT GROUPING CANDIDATES
# ============================================================

# These are analytical candidates only.
#
# None of these combinations is being claimed to represent
# a true merchant identity in IEEE-CIS.
#
# isFraud is deliberately excluded.

CANDIDATES = {
    "productcd": [
        "ProductCD",
    ],

    "productcd_r_emaildomain": [
        "ProductCD",
        "R_emaildomain",
    ],

    "productcd_p_emaildomain": [
        "ProductCD",
        "P_emaildomain",
    ],

    "productcd_r_emaildomain_addr2": [
        "ProductCD",
        "R_emaildomain",
        "addr2",
    ],

    "productcd_p_emaildomain_addr2": [
        "ProductCD",
        "P_emaildomain",
        "addr2",
    ],

    "productcd_r_emaildomain_m4": [
        "ProductCD",
        "R_emaildomain",
        "M4",
    ],
}


# ============================================================
# 3. CHECK SOURCE FILE
# ============================================================

def check_input_file():
    """
    Confirm that the original transaction source exists.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction source file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    print("Transaction source file found.")


# ============================================================
# 4. LOAD REQUIRED SOURCE DATA
# ============================================================

def load_data():
    """
    Load only the columns required for MerchantID analysis.

    isFraud is deliberately not loaded.
    """

    required_columns = {
        "TransactionID",
        "TransactionDT",
    }

    for columns in CANDIDATES.values():
        required_columns.update(columns)

    print("\nLoading required source columns...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=list(required_columns),
        low_memory=False,
    )

    print(
        f"Loaded {len(transactions):,} transactions."
    )

    return transactions


# ============================================================
# 5. ANALYZE SOURCE MISSINGNESS
# ============================================================

def analyze_source_missingness(transactions):
    """
    Measure missingness for the source fields used by the
    candidate merchant signatures.
    """

    columns = [
        "ProductCD",
        "P_emaildomain",
        "R_emaildomain",
        "addr2",
        "M4",
    ]

    results = []

    for column in columns:

        missing_count = int(
            transactions[column]
            .isna()
            .sum()
        )

        missing_percent = (
            missing_count
            / len(transactions)
            * 100
        )

        unique_non_null = int(
            transactions[column]
            .nunique(
                dropna=True
            )
        )

        results.append(
            {
                "column": column,
                "missing_count": missing_count,
                "missing_percent": round(
                    missing_percent,
                    4,
                ),
                "unique_non_null_values": (
                    unique_non_null
                ),
            }
        )

    return pd.DataFrame(results)


# ============================================================
# 6. ANALYZE ONE MERCHANT CANDIDATE
# ============================================================

def analyze_candidate(
    transactions,
    candidate_name,
    columns,
):
    """
    Evaluate one possible merchant-like source grouping.

    This function DOES NOT generate MerchantID.
    """

    working = transactions[
        [
            "TransactionID",
            "TransactionDT",
        ]
        + columns
    ].copy()

    # --------------------------------------------------------
    # COMPLETE-FIELD COVERAGE
    # --------------------------------------------------------

    complete_mask = (
        working[columns]
        .notna()
        .all(axis=1)
    )

    complete_rows = int(
        complete_mask.sum()
    )

    incomplete_rows = int(
        (~complete_mask).sum()
    )

    total_rows = int(
        len(working)
    )

    coverage_percent = (
        complete_rows
        / total_rows
        * 100
        if total_rows > 0
        else 0
    )

    usable = working.loc[
        complete_mask
    ].copy()

    # --------------------------------------------------------
    # TEMPORARY MERCHANT SIGNATURE
    # --------------------------------------------------------

    usable["candidate_key"] = (
        usable[columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    # --------------------------------------------------------
    # TRANSACTIONS PER CANDIDATE GROUP
    # --------------------------------------------------------

    group_sizes = (
        usable.groupby(
            "candidate_key"
        )
        .size()
        .rename(
            "transaction_count"
        )
    )

    number_of_groups = int(
        len(group_sizes)
    )

    single_transaction_groups = int(
        (
            group_sizes == 1
        ).sum()
    )

    repeated_groups = int(
        (
            group_sizes > 1
        ).sum()
    )

    transactions_in_repeated_groups = int(
        group_sizes[
            group_sizes > 1
        ].sum()
    )

    # --------------------------------------------------------
    # PERCENTAGES
    # --------------------------------------------------------

    repeated_group_percent = (
        repeated_groups
        / number_of_groups
        * 100
        if number_of_groups > 0
        else 0
    )

    recurring_transaction_percent = (
        transactions_in_repeated_groups
        / complete_rows
        * 100
        if complete_rows > 0
        else 0
    )

    single_group_percent = (
        single_transaction_groups
        / number_of_groups
        * 100
        if number_of_groups > 0
        else 0
    )

    # --------------------------------------------------------
    # DISTRIBUTION HELPERS
    # --------------------------------------------------------

    def safe_mean(series):
        if len(series) == 0:
            return 0.0

        return round(
            float(
                series.mean()
            ),
            4,
        )

    def safe_median(series):
        if len(series) == 0:
            return 0.0

        return round(
            float(
                series.median()
            ),
            4,
        )

    def safe_quantile(series, q):
        if len(series) == 0:
            return 0.0

        return round(
            float(
                series.quantile(q)
            ),
            4,
        )

    def safe_max(series):
        if len(series) == 0:
            return 0

        return int(
            series.max()
        )

    # --------------------------------------------------------
    # TEMPORAL SPAN OF GROUPS
    # --------------------------------------------------------

    temporal_span = (
        usable.groupby(
            "candidate_key"
        )["TransactionDT"]
        .agg(
            minimum_dt="min",
            maximum_dt="max",
        )
    )

    temporal_span[
        "span_seconds"
    ] = (
        temporal_span["maximum_dt"]
        - temporal_span["minimum_dt"]
    )

    repeated_temporal_span = (
        temporal_span.loc[
            group_sizes > 1,
            "span_seconds",
        ]
        if number_of_groups > 0
        else pd.Series(dtype=float)
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "candidate_name": (
            candidate_name
        ),

        "candidate_columns": (
            " + ".join(
                columns
            )
        ),

        "total_transactions": (
            total_rows
        ),

        "complete_candidate_rows": (
            complete_rows
        ),

        "incomplete_candidate_rows": (
            incomplete_rows
        ),

        "candidate_coverage_percent": round(
            coverage_percent,
            4,
        ),

        "candidate_groups": (
            number_of_groups
        ),

        "single_transaction_groups": (
            single_transaction_groups
        ),

        "single_transaction_group_percent": round(
            single_group_percent,
            4,
        ),

        "repeated_groups": (
            repeated_groups
        ),

        "repeated_group_percent": round(
            repeated_group_percent,
            4,
        ),

        "transactions_in_repeated_groups": (
            transactions_in_repeated_groups
        ),

        "transactions_in_repeated_groups_percent": round(
            recurring_transaction_percent,
            4,
        ),

        "mean_transactions_per_group": (
            safe_mean(
                group_sizes
            )
        ),

        "median_transactions_per_group": (
            safe_median(
                group_sizes
            )
        ),

        "group_size_percentile_95": (
            safe_quantile(
                group_sizes,
                0.95,
            )
        ),

        "group_size_percentile_99": (
            safe_quantile(
                group_sizes,
                0.99,
            )
        ),

        "maximum_group_size": (
            safe_max(
                group_sizes
            )
        ),

        "median_repeated_group_time_span_seconds": (
            safe_median(
                repeated_temporal_span
            )
        ),

        "percentile_95_repeated_group_time_span_seconds": (
            safe_quantile(
                repeated_temporal_span,
                0.95,
            )
        ),
    }


# ============================================================
# 7. ANALYZE ALL CANDIDATES
# ============================================================

def analyze_all_candidates(
    transactions,
):
    """
    Evaluate all merchant grouping candidates.
    """

    results = []

    for (
        candidate_name,
        columns,
    ) in CANDIDATES.items():

        print(
            "\nAnalyzing MerchantID candidate: "
            f"{candidate_name}"
        )

        result = analyze_candidate(
            transactions,
            candidate_name,
            columns,
        )

        results.append(
            result
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# 8. SANITY CHECKS
# ============================================================

def run_sanity_checks(
    transactions,
    results,
):
    """
    Verify that the analysis output is internally consistent.
    """

    print(
        "\nRunning analysis sanity checks..."
    )

    expected_rows = len(
        transactions
    )

    for _, row in (
        results.iterrows()
    ):

        assert (
            row[
                "total_transactions"
            ]
            == expected_rows
        ), (
            "Candidate transaction count "
            "does not match source."
        )

        assert (
            row[
                "complete_candidate_rows"
            ]
            + row[
                "incomplete_candidate_rows"
            ]
            == expected_rows
        ), (
            "Complete and incomplete rows "
            "do not add to source total."
        )

        assert (
            row[
                "transactions_in_repeated_groups"
            ]
            <= row[
                "complete_candidate_rows"
            ]
        ), (
            "Recurring transaction count "
            "is impossible."
        )

    print(
        "Sanity checks passed."
    )


# ============================================================
# 9. SAVE RESULTS
# ============================================================

def save_results(
    candidate_results,
    source_missingness,
):
    """
    Save compact analysis outputs.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_file = (
        OUTPUT_DIR
        / "merchant_id_candidate_analysis.csv"
    )

    missingness_file = (
        OUTPUT_DIR
        / "merchant_source_missingness.csv"
    )

    summary_file = (
        OUTPUT_DIR
        / "merchant_id_analysis_summary.json"
    )

    candidate_results.to_csv(
        candidate_file,
        index=False,
    )

    source_missingness.to_csv(
        missingness_file,
        index=False,
    )

    summary = {
        "source_transaction_rows": int(
            candidate_results[
                "total_transactions"
            ].iloc[0]
        ),

        "candidates_tested": int(
            len(
                candidate_results
            )
        ),

        "candidate_names": (
            candidate_results[
                "candidate_name"
            ].tolist()
        ),
    }

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
        "\nResults saved to:"
    )

    print(
        candidate_file
    )

    print(
        missingness_file
    )

    print(
        summary_file
    )


# ============================================================
# 10. PRINT SUMMARY
# ============================================================

def print_summary(
    candidate_results,
    source_missingness,
):
    """
    Print only the fields needed for our methodology decision.
    """

    print("\n" + "=" * 85)
    print("MERCHANT SOURCE MISSINGNESS")
    print("=" * 85)

    print(
        source_missingness
        .to_string(
            index=False
        )
    )

    print("\n" + "=" * 85)
    print("MERCHANTID CANDIDATE RESULTS")
    print("=" * 85)

    display_columns = [
        "candidate_name",
        "candidate_coverage_percent",
        "candidate_groups",
        "repeated_group_percent",
        "transactions_in_repeated_groups_percent",
        "median_transactions_per_group",
        "group_size_percentile_95",
        "group_size_percentile_99",
        "maximum_group_size",
    ]

    print(
        candidate_results[
            display_columns
        ].to_string(
            index=False
        )
    )


# ============================================================
# 11. MAIN
# ============================================================

def main():

    print("=" * 85)
    print("MERCHANTID CANDIDATE ANALYSIS")
    print("=" * 85)

    print(
        "\nThis script does not generate MerchantID."
    )

    print(
        "isFraud is not loaded or used."
    )

    check_input_file()

    transactions = (
        load_data()
    )

    source_missingness = (
        analyze_source_missingness(
            transactions
        )
    )

    candidate_results = (
        analyze_all_candidates(
            transactions
        )
    )

    run_sanity_checks(
        transactions,
        candidate_results,
    )

    save_results(
        candidate_results,
        source_missingness,
    )

    print_summary(
        candidate_results,
        source_missingness,
    )

    print("\n" + "=" * 85)
    print("MERCHANTID CANDIDATE ANALYSIS COMPLETED")
    print("=" * 85)

    print(
        "\nNo MerchantID was generated."
    )

    print(
        "No source data were modified."
    )


if __name__ == "__main__":
    main()