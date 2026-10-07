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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "account_id_analysis"
)


# ============================================================
# 2. ACCOUNT SIGNATURE CANDIDATES
# ============================================================

# These are candidates only.
#
# We are NOT claiming that any combination is a true
# bank account identifier.
#
# isFraud is deliberately excluded.

CANDIDATES = {
    "card1": [
        "card1",
    ],

    "card1_card2": [
        "card1",
        "card2",
    ],

    "card1_card2_card3": [
        "card1",
        "card2",
        "card3",
    ],

    "card1_card2_card3_card4": [
        "card1",
        "card2",
        "card3",
        "card4",
    ],

    "card1_card2_card3_card5": [
        "card1",
        "card2",
        "card3",
        "card5",
    ],

    "card1_card2_card3_card4_card5_card6": [
        "card1",
        "card2",
        "card3",
        "card4",
        "card5",
        "card6",
    ],
}


# ============================================================
# 3. CHECK REQUIRED FILES
# ============================================================

def check_files():
    """
    Confirm that both the raw transaction data
    and generated CustomerID mapping exist.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    if not CUSTOMER_MAPPING_FILE.exists():
        raise FileNotFoundError(
            "Customer mapping file not found:\n"
            f"{CUSTOMER_MAPPING_FILE}"
        )

    print("Required files found.")


# ============================================================
# 4. LOAD REQUIRED DATA
# ============================================================

def load_data():
    """
    Load only the fields needed for AccountID analysis.

    isFraud is not loaded.
    """

    required_columns = {
        "TransactionID",
        "TransactionDT",
    }

    for columns in CANDIDATES.values():
        required_columns.update(columns)

    print("\nLoading required transaction columns...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=list(required_columns),
        low_memory=False,
    )

    print("Loading CustomerID mapping...")

    customer_mapping = pd.read_csv(
        CUSTOMER_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "CustomerID",
        ],
        low_memory=False,
    )

    print(
        f"Transactions loaded: {len(transactions):,}"
    )

    print(
        "Customer mapping rows: "
        f"{len(customer_mapping):,}"
    )

    return transactions, customer_mapping


# ============================================================
# 5. JOIN CUSTOMERID TO SOURCE TRANSACTIONS
# ============================================================

def join_customer_mapping(
    transactions,
    customer_mapping,
):
    """
    Attach the already generated CustomerID to each
    transaction before account analysis.
    """

    data = transactions.merge(
        customer_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    missing_customer_ids = int(
        data["CustomerID"]
        .isna()
        .sum()
    )

    if missing_customer_ids != 0:
        raise ValueError(
            "Account analysis cannot continue because "
            f"{missing_customer_ids} transactions have "
            "no CustomerID."
        )

    if len(data) != len(transactions):
        raise ValueError(
            "Transaction count changed after CustomerID join."
        )

    print(
        "CustomerID successfully joined to all transactions."
    )

    return data


# ============================================================
# 6. ANALYZE ONE ACCOUNT CANDIDATE
# ============================================================

def analyze_candidate(
    data,
    candidate_name,
    columns,
):
    """
    Evaluate one potential account signature within
    the generated CustomerID structure.

    A candidate account group is defined as:

        CustomerID + candidate card fields

    This is analysis only.
    No AccountID is generated.
    """

    working = data[
        [
            "TransactionID",
            "TransactionDT",
            "CustomerID",
        ]
        + columns
    ].copy()

    # --------------------------------------------------------
    # Candidate-field coverage
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

    total_rows = len(working)

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
    # Build temporary card signature
    # --------------------------------------------------------

    usable["card_signature"] = (
        usable[columns]
        .astype(str)
        .agg("|".join, axis=1)
    )

    # --------------------------------------------------------
    # Build temporary account-analysis key
    #
    # Account grouping is Nested within CustomerID.
    # --------------------------------------------------------

    usable["account_candidate_key"] = (
        usable["CustomerID"].astype(str)
        + "|"
        + usable["card_signature"]
    )

    # --------------------------------------------------------
    # Transactions per candidate account
    # --------------------------------------------------------

    account_sizes = (
        usable.groupby(
            "account_candidate_key"
        )
        .size()
        .rename("transaction_count")
    )

    account_count = int(
        len(account_sizes)
    )

    single_transaction_accounts = int(
        (account_sizes == 1)
        .sum()
    )

    repeated_accounts = int(
        (account_sizes > 1)
        .sum()
    )

    transactions_in_repeated_accounts = int(
        account_sizes[
            account_sizes > 1
        ].sum()
    )

    # --------------------------------------------------------
    # Accounts per analytical customer
    # --------------------------------------------------------

    customer_account_counts = (
        usable[
            [
                "CustomerID",
                "account_candidate_key",
            ]
        ]
        .drop_duplicates()
        .groupby("CustomerID")
        .size()
    )

    customers_with_usable_candidate = int(
        len(customer_account_counts)
    )

    customers_with_multiple_accounts = int(
        (customer_account_counts > 1)
        .sum()
    )

    # --------------------------------------------------------
    # Check whether the same source card signature
    # appears under multiple synthetic CustomerIDs.
    #
    # This does not automatically invalidate a candidate.
    # We are measuring it for transparency.
    # --------------------------------------------------------

    card_customer_counts = (
        usable.groupby(
            "card_signature"
        )["CustomerID"]
        .nunique()
    )

    signatures_across_multiple_customers = int(
        (card_customer_counts > 1)
        .sum()
    )

    # --------------------------------------------------------
    # Statistical helpers
    # --------------------------------------------------------

    def safe_mean(series):
        if len(series) == 0:
            return 0.0

        return round(
            float(series.mean()),
            4,
        )

    def safe_median(series):
        if len(series) == 0:
            return 0.0

        return round(
            float(series.median()),
            4,
        )

    def safe_quantile(series, q):
        if len(series) == 0:
            return 0.0

        return round(
            float(series.quantile(q)),
            4,
        )

    def safe_max(series):
        if len(series) == 0:
            return 0

        return int(
            series.max()
        )

    # --------------------------------------------------------
    # Percent calculations
    # --------------------------------------------------------

    repeated_account_percent = (
        repeated_accounts
        / account_count
        * 100
        if account_count > 0
        else 0
    )

    recurring_transaction_percent = (
        transactions_in_repeated_accounts
        / complete_rows
        * 100
        if complete_rows > 0
        else 0
    )

    multiple_account_customer_percent = (
        customers_with_multiple_accounts
        / customers_with_usable_candidate
        * 100
        if customers_with_usable_candidate > 0
        else 0
    )

    # --------------------------------------------------------
    # Return summary
    # --------------------------------------------------------

    return {
        "candidate_name": candidate_name,

        "candidate_columns": (
            " + ".join(columns)
        ),

        "total_transactions": int(
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

        "candidate_accounts": (
            account_count
        ),

        "single_transaction_accounts": (
            single_transaction_accounts
        ),

        "repeated_accounts": (
            repeated_accounts
        ),

        "repeated_account_percent": round(
            repeated_account_percent,
            4,
        ),

        "transactions_in_repeated_accounts": (
            transactions_in_repeated_accounts
        ),

        "transactions_in_repeated_accounts_percent": round(
            recurring_transaction_percent,
            4,
        ),

        "mean_transactions_per_account": (
            safe_mean(account_sizes)
        ),

        "median_transactions_per_account": (
            safe_median(account_sizes)
        ),

        "account_size_percentile_95": (
            safe_quantile(
                account_sizes,
                0.95,
            )
        ),

        "account_size_percentile_99": (
            safe_quantile(
                account_sizes,
                0.99,
            )
        ),

        "maximum_account_size": (
            safe_max(account_sizes)
        ),

        "customers_with_usable_candidate": (
            customers_with_usable_candidate
        ),

        "customers_with_multiple_candidate_accounts": (
            customers_with_multiple_accounts
        ),

        "customers_with_multiple_candidate_accounts_percent": round(
            multiple_account_customer_percent,
            4,
        ),

        "mean_accounts_per_customer": (
            safe_mean(
                customer_account_counts
            )
        ),

        "median_accounts_per_customer": (
            safe_median(
                customer_account_counts
            )
        ),

        "accounts_per_customer_percentile_95": (
            safe_quantile(
                customer_account_counts,
                0.95,
            )
        ),

        "accounts_per_customer_percentile_99": (
            safe_quantile(
                customer_account_counts,
                0.99,
            )
        ),

        "maximum_accounts_per_customer": (
            safe_max(
                customer_account_counts
            )
        ),

        "card_signatures_across_multiple_customers": (
            signatures_across_multiple_customers
        ),
    }


# ============================================================
# 7. ANALYZE ALL CANDIDATES
# ============================================================

def analyze_all_candidates(data):
    """
    Evaluate each possible card-based analytical
    account signature.
    """

    results = []

    for (
        candidate_name,
        columns,
    ) in CANDIDATES.items():

        print(
            f"\nAnalyzing AccountID candidate: "
            f"{candidate_name}"
        )

        result = analyze_candidate(
            data,
            candidate_name,
            columns,
        )

        results.append(result)

    return pd.DataFrame(
        results
    )


# ============================================================
# 8. CREATE SOURCE MISSINGNESS SUMMARY
# ============================================================

def create_card_missingness(data):
    """
    Record missingness for card1-card6 independently.
    """

    rows = []

    for column in [
        "card1",
        "card2",
        "card3",
        "card4",
        "card5",
        "card6",
    ]:

        missing_count = int(
            data[column]
            .isna()
            .sum()
        )

        missing_percent = (
            missing_count
            / len(data)
            * 100
        )

        rows.append(
            {
                "column": column,

                "missing_count": (
                    missing_count
                ),

                "missing_percent": round(
                    missing_percent,
                    4,
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# 9. SANITY CHECKS
# ============================================================

def run_sanity_checks(
    data,
    candidate_results,
):
    """
    Verify that the analysis itself is internally consistent.
    """

    print("\nRunning analysis sanity checks...")

    expected_rows = len(data)

    for _, row in candidate_results.iterrows():

        assert (
            row["total_transactions"]
            == expected_rows
        ), (
            "Candidate total transaction count "
            "does not match source."
        )

        assert (
            row["complete_candidate_rows"]
            + row["incomplete_candidate_rows"]
            == expected_rows
        ), (
            "Complete and incomplete candidate rows "
            "do not add to total transactions."
        )

        assert (
            row["transactions_in_repeated_accounts"]
            <= row["complete_candidate_rows"]
        ), (
            "Repeated-account transaction count "
            "is impossible."
        )

    print("Sanity checks passed.")


# ============================================================
# 10. SAVE OUTPUTS
# ============================================================

def save_results(
    candidate_results,
    card_missingness,
):
    """
    Save only compact analysis outputs.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_file = (
        OUTPUT_DIR
        / "account_id_candidate_analysis.csv"
    )

    missingness_file = (
        OUTPUT_DIR
        / "card_field_missingness.csv"
    )

    summary_file = (
        OUTPUT_DIR
        / "account_id_analysis_summary.json"
    )

    candidate_results.to_csv(
        candidate_file,
        index=False,
    )

    card_missingness.to_csv(
        missingness_file,
        index=False,
    )

    summary = {
        "candidates_tested": int(
            len(candidate_results)
        ),

        "source_transaction_rows": int(
            candidate_results[
                "total_transactions"
            ].iloc[0]
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

    print("\nResults saved to:")
    print(candidate_file)
    print(missingness_file)
    print(summary_file)


# ============================================================
# 11. PRINT RESULTS
# ============================================================

def print_results(
    candidate_results,
    card_missingness,
):
    """
    Print compact summaries to the terminal.
    """

    print("\n" + "=" * 80)
    print("CARD FIELD MISSINGNESS")
    print("=" * 80)

    print(
        card_missingness.to_string(
            index=False
        )
    )

    print("\n" + "=" * 80)
    print("ACCOUNTID CANDIDATE ANALYSIS")
    print("=" * 80)

    display_columns = [
        "candidate_name",
        "candidate_coverage_percent",
        "candidate_accounts",
        "repeated_account_percent",
        "transactions_in_repeated_accounts_percent",
        "median_transactions_per_account",
        "account_size_percentile_99",
        "maximum_account_size",
        "mean_accounts_per_customer",
        "median_accounts_per_customer",
        "maximum_accounts_per_customer",
    ]

    print(
        candidate_results[
            display_columns
        ].to_string(
            index=False
        )
    )


# ============================================================
# 12. MAIN
# ============================================================

def main():

    print("=" * 80)
    print("ACCOUNTID CANDIDATE ANALYSIS")
    print("=" * 80)

    print(
        "\nNo AccountID will be generated by this script."
    )

    print(
        "isFraud is not loaded or used."
    )

    check_files()

    (
        transactions,
        customer_mapping,
    ) = load_data()

    data = join_customer_mapping(
        transactions,
        customer_mapping,
    )

    card_missingness = (
        create_card_missingness(
            data
        )
    )

    candidate_results = (
        analyze_all_candidates(
            data
        )
    )

    run_sanity_checks(
        data,
        candidate_results,
    )

    save_results(
        candidate_results,
        card_missingness,
    )

    print_results(
        candidate_results,
        card_missingness,
    )

    print("\n" + "=" * 80)
    print("ACCOUNTID CANDIDATE ANALYSIS COMPLETED")
    print("=" * 80)

    print(
        "\nNo source files were modified."
    )


if __name__ == "__main__":
    main()