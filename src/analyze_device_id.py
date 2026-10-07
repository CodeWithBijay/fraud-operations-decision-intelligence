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

IDENTITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "ieee_cis"
    / "train_identity.csv"
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
    / "device_id_analysis"
)


# ============================================================
# 2. CHECK REQUIRED FILES
# ============================================================

def check_files():

    required_files = [
        TRANSACTION_FILE,
        IDENTITY_FILE,
        CUSTOMER_MAPPING_FILE,
    ]

    for file_path in required_files:

        if not file_path.exists():

            raise FileNotFoundError(
                "Required file not found:\n"
                f"{file_path}"
            )

    print("Required files found.")


# ============================================================
# 3. LOAD DATA
# ============================================================

def load_data():
    """
    Load only fields required for DeviceID analysis.

    isFraud is deliberately not loaded.
    """

    print("\nLoading transaction information...")

    transactions = pd.read_csv(
        TRANSACTION_FILE,
        usecols=[
            "TransactionID",
            "TransactionDT",
        ],
        low_memory=False,
    )

    print("Loading source identity/device information...")

    identity = pd.read_csv(
        IDENTITY_FILE,
        usecols=[
            "TransactionID",
            "DeviceType",
            "DeviceInfo",
        ],
        low_memory=False,
    )

    print("Loading generated CustomerID mapping...")

    customers = pd.read_csv(
        CUSTOMER_MAPPING_FILE,
        usecols=[
            "TransactionID",
            "CustomerID",
        ],
        low_memory=False,
    )

    print(
        f"Transactions: {len(transactions):,}"
    )

    print(
        f"Identity records: {len(identity):,}"
    )

    return (
        transactions,
        identity,
        customers,
    )


# ============================================================
# 4. BUILD AUDIT DATASET
# ============================================================

def build_audit_dataset(
    transactions,
    identity,
    customers,
):
    """
    Attach identity and CustomerID information to the
    transaction population.

    Missing identity data remain missing.
    """

    data = transactions.merge(
        identity,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    data = data.merge(
        customers,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    if len(data) != len(transactions):

        raise ValueError(
            "Transaction count changed after joins."
        )

    missing_customer_ids = int(
        data["CustomerID"]
        .isna()
        .sum()
    )

    if missing_customer_ids != 0:

        raise ValueError(
            f"{missing_customer_ids} transactions "
            "are missing CustomerID."
        )

    return data


# ============================================================
# 5. BASIC DEVICE COVERAGE
# ============================================================

def analyze_device_coverage(data):

    total = len(data)

    device_type_present = int(
        data["DeviceType"]
        .notna()
        .sum()
    )

    device_info_present = int(
        data["DeviceInfo"]
        .notna()
        .sum()
    )

    both_present = int(
        (
            data["DeviceType"].notna()
            & data["DeviceInfo"].notna()
        ).sum()
    )

    type_only = int(
        (
            data["DeviceType"].notna()
            & data["DeviceInfo"].isna()
        ).sum()
    )

    info_only = int(
        (
            data["DeviceType"].isna()
            & data["DeviceInfo"].notna()
        ).sum()
    )

    neither_present = int(
        (
            data["DeviceType"].isna()
            & data["DeviceInfo"].isna()
        ).sum()
    )

    def percent(count):
        return round(
            count / total * 100,
            4,
        )

    return {
        "total_transactions": int(
            total
        ),

        "device_type_present": (
            device_type_present
        ),

        "device_type_coverage_percent": (
            percent(
                device_type_present
            )
        ),

        "device_info_present": (
            device_info_present
        ),

        "device_info_coverage_percent": (
            percent(
                device_info_present
            )
        ),

        "both_device_fields_present": (
            both_present
        ),

        "both_device_fields_percent": (
            percent(
                both_present
            )
        ),

        "device_type_only": (
            type_only
        ),

        "device_info_only": (
            info_only
        ),

        "neither_device_field_present": (
            neither_present
        ),

        "neither_device_field_percent": (
            percent(
                neither_present
            )
        ),
    }


# ============================================================
# 6. ANALYZE INDIVIDUAL DEVICE FIELDS
# ============================================================

def analyze_device_fields(data):

    rows = []

    for column in [
        "DeviceType",
        "DeviceInfo",
    ]:

        non_null = data[
            column
        ].dropna()

        missing_count = int(
            data[column]
            .isna()
            .sum()
        )

        unique_values = int(
            non_null.nunique()
        )

        value_counts = (
            non_null.value_counts()
        )

        repeated_values = int(
            (
                value_counts > 1
            ).sum()
        )

        transactions_in_repeated_values = int(
            value_counts[
                value_counts > 1
            ].sum()
        )

        maximum_frequency = (
            int(
                value_counts.max()
            )
            if len(value_counts) > 0
            else 0
        )

        rows.append(
            {
                "field": column,

                "missing_count": (
                    missing_count
                ),

                "missing_percent": round(
                    missing_count
                    / len(data)
                    * 100,
                    4,
                ),

                "non_null_count": int(
                    len(non_null)
                ),

                "unique_values": (
                    unique_values
                ),

                "repeated_values": (
                    repeated_values
                ),

                "transactions_in_repeated_values": (
                    transactions_in_repeated_values
                ),

                "maximum_value_frequency": (
                    maximum_frequency
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# 7. DEVICE SIGNATURE ANALYSIS
# ============================================================

def analyze_device_signature(data):
    """
    Evaluate DeviceType + DeviceInfo as a possible
    source-informed device signature.

    This is NOT yet DeviceID generation.
    """

    usable_mask = (
        data["DeviceType"].notna()
        & data["DeviceInfo"].notna()
    )

    usable = data.loc[
        usable_mask
    ].copy()

    usable[
        "device_signature"
    ] = (
        usable[
            [
                "DeviceType",
                "DeviceInfo",
            ]
        ]
        .astype(str)
        .agg(
            "|".join,
            axis=1,
        )
    )

    group_sizes = (
        usable.groupby(
            "device_signature"
        )
        .size()
    )

    customer_counts = (
        usable.groupby(
            "device_signature"
        )["CustomerID"]
        .nunique()
    )

    signatures_one_customer = int(
        (
            customer_counts == 1
        ).sum()
    )

    signatures_multiple_customers = int(
        (
            customer_counts > 1
        ).sum()
    )

    transactions_in_repeated_signatures = int(
        group_sizes[
            group_sizes > 1
        ].sum()
    )

    recurring_transaction_percent = (
        transactions_in_repeated_signatures
        / len(usable)
        * 100
        if len(usable) > 0
        else 0
    )

    return {
        "usable_transactions": int(
            len(usable)
        ),

        "device_signatures": int(
            len(group_sizes)
        ),

        "single_transaction_signatures": int(
            (
                group_sizes == 1
            ).sum()
        ),

        "repeated_signatures": int(
            (
                group_sizes > 1
            ).sum()
        ),

        "transactions_in_repeated_signatures": (
            transactions_in_repeated_signatures
        ),

        "transactions_in_repeated_signatures_percent": round(
            recurring_transaction_percent,
            4,
        ),

        "median_transactions_per_signature": (
            round(
                float(
                    group_sizes.median()
                ),
                4,
            )
            if len(group_sizes) > 0
            else 0
        ),

        "mean_transactions_per_signature": (
            round(
                float(
                    group_sizes.mean()
                ),
                4,
            )
            if len(group_sizes) > 0
            else 0
        ),

        "percentile_95_signature_size": (
            round(
                float(
                    group_sizes.quantile(
                        0.95
                    )
                ),
                4,
            )
            if len(group_sizes) > 0
            else 0
        ),

        "percentile_99_signature_size": (
            round(
                float(
                    group_sizes.quantile(
                        0.99
                    )
                ),
                4,
            )
            if len(group_sizes) > 0
            else 0
        ),

        "maximum_signature_size": (
            int(
                group_sizes.max()
            )
            if len(group_sizes) > 0
            else 0
        ),

        "signatures_linked_to_one_customer": (
            signatures_one_customer
        ),

        "signatures_linked_to_multiple_customers": (
            signatures_multiple_customers
        ),
    }


# ============================================================
# 8. CUSTOMER-NESTED DEVICE SIGNATURE
# ============================================================

def analyze_customer_device_signature(data):
    """
    Evaluate device signatures inside CustomerID.

    This is important because a general DeviceInfo value
    may appear across many customers.
    """

    usable_mask = (
        data["DeviceType"].notna()
        & data["DeviceInfo"].notna()
    )

    usable = data.loc[
        usable_mask
    ].copy()

    usable[
        "device_signature"
    ] = (
        usable[
            [
                "DeviceType",
                "DeviceInfo",
            ]
        ]
        .astype(str)
        .agg(
            "|".join,
            axis=1,
        )
    )

    usable[
        "customer_device_key"
    ] = (
        usable["CustomerID"]
        .astype(str)
        + "|"
        + usable[
            "device_signature"
        ]
    )

    device_sizes = (
        usable.groupby(
            "customer_device_key"
        )
        .size()
    )

    customer_device_counts = (
        usable[
            [
                "CustomerID",
                "customer_device_key",
            ]
        ]
        .drop_duplicates()
        .groupby(
            "CustomerID"
        )
        .size()
    )

    customers_with_multiple_devices = int(
        (
            customer_device_counts > 1
        ).sum()
    )

    return {
        "customer_device_groups": int(
            len(device_sizes)
        ),

        "repeated_customer_device_groups": int(
            (
                device_sizes > 1
            ).sum()
        ),

        "median_transactions_per_customer_device": (
            round(
                float(
                    device_sizes.median()
                ),
                4,
            )
            if len(device_sizes) > 0
            else 0
        ),

        "percentile_95_transactions_per_customer_device": (
            round(
                float(
                    device_sizes.quantile(
                        0.95
                    )
                ),
                4,
            )
            if len(device_sizes) > 0
            else 0
        ),

        "maximum_transactions_per_customer_device": (
            int(
                device_sizes.max()
            )
            if len(device_sizes) > 0
            else 0
        ),

        "customers_with_device_information": int(
            len(
                customer_device_counts
            )
        ),

        "customers_with_multiple_device_signatures": (
            customers_with_multiple_devices
        ),

        "customers_with_multiple_device_signatures_percent": (
            round(
                customers_with_multiple_devices
                / len(
                    customer_device_counts
                )
                * 100,
                4,
            )
            if len(
                customer_device_counts
            ) > 0
            else 0
        ),

        "mean_device_signatures_per_customer": (
            round(
                float(
                    customer_device_counts.mean()
                ),
                4,
            )
            if len(
                customer_device_counts
            ) > 0
            else 0
        ),

        "median_device_signatures_per_customer": (
            round(
                float(
                    customer_device_counts.median()
                ),
                4,
            )
            if len(
                customer_device_counts
            ) > 0
            else 0
        ),

        "maximum_device_signatures_per_customer": (
            int(
                customer_device_counts.max()
            )
            if len(
                customer_device_counts
            ) > 0
            else 0
        ),
    }


# ============================================================
# 9. MOST COMMON DEVICEINFO VALUES
# ============================================================

def create_device_info_frequency(data):
    """
    Save the most frequently observed source DeviceInfo
    values for review.

    These values are source observations, not generated data.
    """

    frequency = (
        data["DeviceInfo"]
        .dropna()
        .value_counts()
        .rename_axis(
            "DeviceInfo"
        )
        .reset_index(
            name="transaction_count"
        )
    )

    return frequency.head(50)


# ============================================================
# 10. SANITY CHECKS
# ============================================================

def run_sanity_checks(
    data,
    coverage,
):
    """
    Verify internal consistency of the audit.
    """

    print(
        "\nRunning DeviceID audit sanity checks..."
    )

    assert (
        coverage[
            "total_transactions"
        ]
        == len(data)
    )

    classification_total = (
        coverage[
            "both_device_fields_present"
        ]
        + coverage[
            "device_type_only"
        ]
        + coverage[
            "device_info_only"
        ]
        + coverage[
            "neither_device_field_present"
        ]
    )

    assert (
        classification_total
        == len(data)
    ), (
        "Device availability categories "
        "do not sum to total transactions."
    )

    print(
        "Sanity checks passed."
    )


# ============================================================
# 11. SAVE RESULTS
# ============================================================

def save_results(
    coverage,
    field_analysis,
    signature_analysis,
    customer_device_analysis,
    device_frequency,
):
    """
    Save compact DeviceID audit outputs.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    coverage_file = (
        OUTPUT_DIR
        / "device_coverage_summary.json"
    )

    fields_file = (
        OUTPUT_DIR
        / "device_field_analysis.csv"
    )

    signature_file = (
        OUTPUT_DIR
        / "device_signature_analysis.json"
    )

    customer_device_file = (
        OUTPUT_DIR
        / "customer_device_analysis.json"
    )

    frequency_file = (
        OUTPUT_DIR
        / "device_info_top_values.csv"
    )

    with coverage_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            coverage,
            file,
            indent=4,
        )

    field_analysis.to_csv(
        fields_file,
        index=False,
    )

    with signature_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            signature_analysis,
            file,
            indent=4,
        )

    with customer_device_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            customer_device_analysis,
            file,
            indent=4,
        )

    device_frequency.to_csv(
        frequency_file,
        index=False,
    )

    print("\nDevice audit outputs saved to:")
    print(OUTPUT_DIR)


# ============================================================
# 12. PRINT SUMMARY
# ============================================================

def print_summary(
    coverage,
    signature_analysis,
    customer_device_analysis,
):
    """
    Print the key information needed for the DeviceID
    generation decision.
    """

    print("\n" + "=" * 75)
    print("DEVICE COVERAGE")
    print("=" * 75)

    for key, value in coverage.items():
        print(
            f"{key}: {value}"
        )

    print("\n" + "=" * 75)
    print("SOURCE DEVICE SIGNATURE")
    print("=" * 75)

    for (
        key,
        value,
    ) in signature_analysis.items():
        print(
            f"{key}: {value}"
        )

    print("\n" + "=" * 75)
    print("CUSTOMER-NESTED DEVICE ANALYSIS")
    print("=" * 75)

    for (
        key,
        value,
    ) in customer_device_analysis.items():
        print(
            f"{key}: {value}"
        )


# ============================================================
# 13. MAIN
# ============================================================

def main():

    print("=" * 75)
    print("DEVICEID SOURCE AUDIT")
    print("=" * 75)

    print(
        "\nNo DeviceID will be generated by this script."
    )

    print(
        "isFraud is not loaded or used."
    )

    check_files()

    (
        transactions,
        identity,
        customers,
    ) = load_data()

    data = build_audit_dataset(
        transactions,
        identity,
        customers,
    )

    coverage = analyze_device_coverage(
        data
    )

    field_analysis = (
        analyze_device_fields(
            data
        )
    )

    signature_analysis = (
        analyze_device_signature(
            data
        )
    )

    customer_device_analysis = (
        analyze_customer_device_signature(
            data
        )
    )

    device_frequency = (
        create_device_info_frequency(
            data
        )
    )

    run_sanity_checks(
        data,
        coverage,
    )

    save_results(
        coverage,
        field_analysis,
        signature_analysis,
        customer_device_analysis,
        device_frequency,
    )

    print_summary(
        coverage,
        signature_analysis,
        customer_device_analysis,
    )

    print("\n" + "=" * 75)
    print("DEVICEID SOURCE AUDIT COMPLETED")
    print("=" * 75)

    print(
        "\nNo source files were modified."
    )


if __name__ == "__main__":
    main()