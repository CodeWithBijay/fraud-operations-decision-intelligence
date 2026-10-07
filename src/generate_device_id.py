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
    / "device"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "device_id_generation"
)


# ============================================================
# 2. APPROVED DEVICE SIGNATURE
# ============================================================

DEVICE_COLUMNS = [
    "DeviceType",
    "DeviceInfo",
]


# ============================================================
# 3. CREATE DETERMINISTIC DEVICE ID
# ============================================================

def create_device_id(
    customer_id,
    device_type,
    device_info,
):
    """
    Create a deterministic project-level analytical DeviceID.

    DeviceID is nested inside CustomerID.

    Same:
        CustomerID
        + DeviceType
        + DeviceInfo

    always produces the same analytical DeviceID.

    DeviceID is NOT a recovered physical-device identifier.
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
    Confirm that all required input files exist.
    """

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
# 5. LOAD REQUIRED DATA
# ============================================================

def load_data():
    """
    Load only fields required for DeviceID generation.

    isFraud is deliberately not loaded.
    """

    print("\nLoading source transaction fields...")

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
        f"Identity rows loaded: {len(identity):,}"
    )

    return (
        transactions,
        identity,
        customer_mapping,
    )


# ============================================================
# 6. BUILD GENERATION DATASET
# ============================================================

def build_generation_dataset(
    transactions,
    identity,
    customer_mapping,
):
    """
    Attach source device information and generated CustomerID
    to the complete transaction population.

    Missing source device information remains missing.
    """

    data = transactions.merge(
        identity,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    data = data.merge(
        customer_mapping,
        on="TransactionID",
        how="left",
        validate="one_to_one",
    )

    if len(data) != len(transactions):

        raise ValueError(
            "Transaction count changed after joins."
        )

    missing_customers = int(
        data["CustomerID"]
        .isna()
        .sum()
    )

    if missing_customers != 0:

        raise ValueError(
            f"{missing_customers} transactions "
            "are missing CustomerID."
        )

    return data


# ============================================================
# 7. GENERATE DEVICE IDS
# ============================================================

def generate_device_ids(data):
    """
    Apply the approved DeviceID methodology.

    DeviceID is generated only when BOTH:

        DeviceType
        DeviceInfo

    are available.

    Otherwise DeviceID remains NULL.

    Missing device information is NOT interpreted
    as a new device.
    """

    result = data.copy()

    result["DeviceID"] = pd.NA

    result["DeviceID_method"] = (
        "INSUFFICIENT_DEVICE_EVIDENCE"
    )

    complete_device_mask = (
        result["DeviceType"].notna()
        & result["DeviceInfo"].notna()
    )

    usable = result.loc[
        complete_device_mask
    ].copy()

    usable["DeviceID"] = usable.apply(
        lambda row: create_device_id(
            row["CustomerID"],
            row["DeviceType"],
            row["DeviceInfo"],
        ),
        axis=1,
    )

    result.loc[
        usable.index,
        "DeviceID",
    ] = usable["DeviceID"]

    result.loc[
        usable.index,
        "DeviceID_method",
    ] = "CUSTOMER_NESTED_DEVICE_SIGNATURE"

    return result


# ============================================================
# 8. GENERATION SAFETY CHECKS
# ============================================================

def run_generation_checks(result):
    """
    Immediate generation-stage checks.

    These are NOT the separate DeviceID validation phase.
    """

    print("\nRunning DeviceID generation safety checks...")

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

    source_complete = (
        result["DeviceType"].notna()
        & result["DeviceInfo"].notna()
    )

    generated_present = (
        result["DeviceID"].notna()
    )

    incorrect_missing = int(
        (
            source_complete
            & ~generated_present
        ).sum()
    )

    incorrect_generated = int(
        (
            ~source_complete
            & generated_present
        ).sum()
    )

    assert incorrect_missing == 0, (
        "One or more eligible transactions "
        "did not receive DeviceID."
    )

    assert incorrect_generated == 0, (
        "DeviceID was generated without "
        "sufficient source device evidence."
    )

    # DeviceID is nested within CustomerID.
    device_customer_counts = (
        result.loc[
            result["DeviceID"].notna()
        ]
        .groupby("DeviceID")["CustomerID"]
        .nunique()
    )

    cross_customer_devices = int(
        (
            device_customer_counts > 1
        ).sum()
    )

    assert cross_customer_devices == 0, (
        "One or more DeviceIDs cross CustomerID boundaries."
    )

    print("Generation safety checks passed.")


# ============================================================
# 9. CREATE GENERATION SUMMARY
# ============================================================

def create_summary(result):
    """
    Summarize the generated analytical DeviceID population.
    """

    total_rows = len(result)

    generated_mask = (
        result["DeviceID"].notna()
    )

    missing_mask = (
        result["DeviceID"].isna()
    )

    generated_rows = int(
        generated_mask.sum()
    )

    missing_rows = int(
        missing_mask.sum()
    )

    distinct_device_ids = int(
        result["DeviceID"]
        .nunique(
            dropna=True
        )
    )

    method_counts = (
        result["DeviceID_method"]
        .value_counts(
            dropna=False
        )
        .to_dict()
    )

    device_sizes = (
        result.loc[
            generated_mask
        ]
        .groupby(
            "DeviceID"
        )
        .size()
    )

    customer_device_counts = (
        result.loc[
            generated_mask,
            [
                "CustomerID",
                "DeviceID",
            ],
        ]
        .drop_duplicates()
        .groupby(
            "CustomerID"
        )
        .size()
    )

    customers_with_device_id = int(
        len(
            customer_device_counts
        )
    )

    customers_with_multiple_devices = int(
        (
            customer_device_counts > 1
        ).sum()
    )

    def safe_stat(
        series,
        statistic,
    ):

        if len(series) == 0:

            return 0

        if statistic == "minimum":
            return int(
                series.min()
            )

        if statistic == "maximum":
            return int(
                series.max()
            )

        if statistic == "mean":
            return round(
                float(
                    series.mean()
                ),
                4,
            )

        if statistic == "median":
            return round(
                float(
                    series.median()
                ),
                4,
            )

        if statistic == "p95":
            return round(
                float(
                    series.quantile(
                        0.95
                    )
                ),
                4,
            )

        if statistic == "p99":
            return round(
                float(
                    series.quantile(
                        0.99
                    )
                ),
                4,
            )

        raise ValueError(
            "Unknown statistic."
        )

    return {
        "transaction_rows": int(
            total_rows
        ),

        "transactions_with_device_id": (
            generated_rows
        ),

        "transactions_without_device_id": (
            missing_rows
        ),

        "device_id_coverage_percent": round(
            generated_rows
            / total_rows
            * 100,
            4,
        ),

        "distinct_device_ids": (
            distinct_device_ids
        ),

        "device_id_method_counts": {
            str(key): int(value)
            for key, value
            in method_counts.items()
        },

        "device_group_size": {
            "minimum": safe_stat(
                device_sizes,
                "minimum",
            ),

            "maximum": safe_stat(
                device_sizes,
                "maximum",
            ),

            "mean": safe_stat(
                device_sizes,
                "mean",
            ),

            "median": safe_stat(
                device_sizes,
                "median",
            ),

            "percentile_95": safe_stat(
                device_sizes,
                "p95",
            ),

            "percentile_99": safe_stat(
                device_sizes,
                "p99",
            ),
        },

        "customers_with_device_id": (
            customers_with_device_id
        ),

        "customer_device_distribution": {
            "minimum": safe_stat(
                customer_device_counts,
                "minimum",
            ),

            "maximum": safe_stat(
                customer_device_counts,
                "maximum",
            ),

            "mean": safe_stat(
                customer_device_counts,
                "mean",
            ),

            "median": safe_stat(
                customer_device_counts,
                "median",
            ),

            "percentile_95": safe_stat(
                customer_device_counts,
                "p95",
            ),

            "percentile_99": safe_stat(
                customer_device_counts,
                "p99",
            ),

            "customers_with_multiple_devices": (
                customers_with_multiple_devices
            ),

            "customers_with_multiple_devices_percent": (
                round(
                    customers_with_multiple_devices
                    / customers_with_device_id
                    * 100,
                    4,
                )
                if customers_with_device_id > 0
                else 0
            ),
        },
    }


# ============================================================
# 10. SAVE OUTPUTS
# ============================================================

def save_results(
    result,
    summary,
):
    """
    Save generated DeviceID mapping and compact summary.

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
        / "transaction_device_mapping.csv"
    )

    summary_file = (
        REPORT_DIR
        / "device_id_generation_summary.json"
    )

    result[
        [
            "TransactionID",
            "TransactionDT",
            "CustomerID",
            "DeviceType",
            "DeviceInfo",
            "DeviceID",
            "DeviceID_method",
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

    print("\nDevice mapping saved to:")
    print(mapping_file)

    print("\nGeneration summary saved to:")
    print(summary_file)


# ============================================================
# 11. PRINT SUMMARY
# ============================================================

def print_summary(summary):

    print("\n" + "=" * 75)
    print("DEVICEID GENERATION SUMMARY")
    print("=" * 75)

    print(
        "Transactions: "
        f"{summary['transaction_rows']:,}"
    )

    print(
        "Transactions with DeviceID: "
        f"{summary['transactions_with_device_id']:,}"
    )

    print(
        "Transactions without DeviceID: "
        f"{summary['transactions_without_device_id']:,}"
    )

    print(
        "DeviceID coverage: "
        f"{summary['device_id_coverage_percent']}%"
    )

    print(
        "Distinct DeviceIDs: "
        f"{summary['distinct_device_ids']:,}"
    )

    print("\nDeviceID methods:")

    for method, count in (
        summary[
            "device_id_method_counts"
        ].items()
    ):

        print(
            f"  {method}: {count:,}"
        )

    print("\nDevice group sizes:")

    for key, value in (
        summary[
            "device_group_size"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )

    print(
        "\nCustomers with DeviceID evidence: "
        f"{summary['customers_with_device_id']:,}"
    )

    print("\nDeviceIDs per customer:")

    for key, value in (
        summary[
            "customer_device_distribution"
        ].items()
    ):

        print(
            f"  {key}: {value}"
        )


# ============================================================
# 12. MAIN
# ============================================================

def main():

    print("=" * 75)
    print("DEVICEID GENERATION")
    print("=" * 75)

    print(
        "\nApproved methodology:"
    )

    print(
        "CustomerID + DeviceType + DeviceInfo"
    )

    print(
        "\nDeviceID is generated only when both "
        "source device fields are available."
    )

    print(
        "isFraud is not loaded or used."
    )

    check_files()

    (
        transactions,
        identity,
        customer_mapping,
    ) = load_data()

    data = build_generation_dataset(
        transactions,
        identity,
        customer_mapping,
    )

    print(
        "\nGenerating analytical DeviceID..."
    )

    result = generate_device_ids(
        data
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

    print("\n" + "=" * 75)
    print("DEVICEID GENERATION COMPLETED")
    print("=" * 75)

    print(
        "\nNo source data were modified."
    )

    print(
        "No random DeviceID assignment was used."
    )

    print(
        "Missing device evidence remains NULL."
    )


if __name__ == "__main__":
    main()