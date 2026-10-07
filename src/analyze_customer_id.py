from pathlib import Path

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
# 2. CANDIDATE CUSTOMER GROUPINGS
# ============================================================

# These are candidates for analysis only.
#
# We are NOT claiming that any combination is a true customer
# identifier.
#
# isFraud is deliberately excluded.

CANDIDATES = {
    "card1": [
        "card1"
    ],

    "card1_addr1": [
        "card1",
        "addr1"
    ],

    "card1_addr1_p_emaildomain": [
        "card1",
        "addr1",
        "P_emaildomain"
    ],

    "card1_card2_addr1": [
        "card1",
        "card2",
        "addr1"
    ],

    "card1_card2_addr1_p_emaildomain": [
        "card1",
        "card2",
        "addr1",
        "P_emaildomain"
    ],
}


# ============================================================
# 3. CHECK SOURCE FILE
# ============================================================

def check_input_file():
    """
    Confirm that the transaction source file exists.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            f"Transaction file not found:\n{TRANSACTION_FILE}"
        )

    print("Transaction source file found.")


# ============================================================
# 4. LOAD ONLY REQUIRED COLUMNS
# ============================================================

def load_data():
    """
    Load only the columns required for CustomerID analysis.

    This avoids loading all 394 transaction columns into memory.
    """

    required_columns = {
        "TransactionID",
        "TransactionDT",
    }

    for columns in CANDIDATES.values():
        required_columns.update(columns)

    required_columns = list(required_columns)

    print("\nLoading required transaction columns...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=required_columns,
        low_memory=False,
    )

    print(
        f"Loaded {len(transactions):,} transaction records."
    )

    return transactions


# ============================================================
# 5. ANALYZE ONE CANDIDATE
# ============================================================

def analyze_candidate(
    transactions,
    candidate_name,
    columns
):
    """
    Evaluate one possible source-informed grouping.

    The function does NOT create the final CustomerID.
    """

    working = transactions[
        ["TransactionID", "TransactionDT"] + columns
    ].copy()

    # --------------------------------------------------------
    # Missingness
    # --------------------------------------------------------

    complete_mask = working[columns].notna().all(axis=1)

    complete_rows = int(complete_mask.sum())
    incomplete_rows = int((~complete_mask).sum())

    coverage_percent = (
        complete_rows / len(working) * 100
    )

    usable = working.loc[complete_mask].copy()

    # --------------------------------------------------------
    # Create a temporary grouping key
    # --------------------------------------------------------

    #
    # This key exists ONLY for analysis.
    # It is not the final synthetic CustomerID.
    #

    usable["candidate_key"] = (
        usable[columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    # --------------------------------------------------------
    # Count transactions in each candidate group
    # --------------------------------------------------------

    group_sizes = (
        usable.groupby("candidate_key")
        .size()
        .rename("transaction_count")
    )

    number_of_groups = int(len(group_sizes))

    repeated_groups = int(
        (group_sizes > 1).sum()
    )

    single_transaction_groups = int(
        (group_sizes == 1).sum()
    )

    if number_of_groups > 0:

        repeated_group_percent = (
            repeated_groups
            / number_of_groups
            * 100
        )

        single_group_percent = (
            single_transaction_groups
            / number_of_groups
            * 100
        )

        median_transactions_per_group = float(
            group_sizes.median()
        )

        mean_transactions_per_group = float(
            group_sizes.mean()
        )

        percentile_95_group_size = float(
            group_sizes.quantile(0.95)
        )

        percentile_99_group_size = float(
            group_sizes.quantile(0.99)
        )

        maximum_group_size = int(
            group_sizes.max()
        )

    else:

        repeated_group_percent = 0
        single_group_percent = 0
        median_transactions_per_group = 0
        mean_transactions_per_group = 0
        percentile_95_group_size = 0
        percentile_99_group_size = 0
        maximum_group_size = 0

    # --------------------------------------------------------
    # How many transactions belong to recurring groups?
    # --------------------------------------------------------

    recurring_transaction_count = int(
        group_sizes[
            group_sizes > 1
        ].sum()
    )

    if complete_rows > 0:

        recurring_transaction_percent = (
            recurring_transaction_count
            / complete_rows
            * 100
        )

    else:

        recurring_transaction_percent = 0

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {
        "candidate_name": candidate_name,

        "columns": " + ".join(columns),

        "total_transactions": int(
            len(working)
        ),

        "complete_candidate_rows": complete_rows,

        "incomplete_candidate_rows": incomplete_rows,

        "candidate_coverage_percent": round(
            coverage_percent,
            4
        ),

        "candidate_groups": number_of_groups,

        "single_transaction_groups": (
            single_transaction_groups
        ),

        "single_transaction_group_percent": round(
            single_group_percent,
            4
        ),

        "repeated_groups": repeated_groups,

        "repeated_group_percent": round(
            repeated_group_percent,
            4
        ),

        "transactions_in_recurring_groups": (
            recurring_transaction_count
        ),

        "transactions_in_recurring_groups_percent": round(
            recurring_transaction_percent,
            4
        ),

        "mean_transactions_per_group": round(
            mean_transactions_per_group,
            4
        ),

        "median_transactions_per_group": round(
            median_transactions_per_group,
            4
        ),

        "group_size_percentile_95": round(
            percentile_95_group_size,
            4
        ),

        "group_size_percentile_99": round(
            percentile_99_group_size,
            4
        ),

        "maximum_group_size": maximum_group_size,
    }


# ============================================================
# 6. RUN ALL CANDIDATES
# ============================================================

def analyze_all_candidates(transactions):
    """
    Evaluate every candidate grouping definition.
    """

    results = []

    for candidate_name, columns in CANDIDATES.items():

        print(
            f"\nAnalyzing: "
            f"{candidate_name}"
        )

        result = analyze_candidate(
            transactions,
            candidate_name,
            columns,
        )

        results.append(result)

    return pd.DataFrame(results)


# ============================================================
# 7. SAVE RESULTS
# ============================================================

def save_results(results):
    """
    Save results for review before any CustomerID
    generation methodology is approved.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        OUTPUT_DIR
        / "customer_id_candidate_analysis.csv"
    )

    results.to_csv(
        output_file,
        index=False
    )

    print("\nAnalysis saved to:")
    print(output_file)


# ============================================================
# 8. MAIN
# ============================================================

def main():

    print("=" * 65)
    print("CUSTOMER ID CANDIDATE ANALYSIS")
    print("=" * 65)

    check_input_file()

    transactions = load_data()

    results = analyze_all_candidates(
        transactions
    )

    save_results(results)

    print("\nCandidate summary:")
    print(
        results.to_string(
            index=False
        )
    )

    print("\n" + "=" * 65)
    print("CUSTOMER ID ANALYSIS COMPLETED")
    print("=" * 65)

    print(
        "\nNo CustomerID was generated."
    )

    print(
        "No source data were modified."
    )

    print(
        "isFraud was not used in the analysis."
    )


if __name__ == "__main__":
    main()