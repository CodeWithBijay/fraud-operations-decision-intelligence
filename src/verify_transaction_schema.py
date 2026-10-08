from pathlib import Path
import subprocess

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRANSACTION_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "final"
    / "transaction.csv"
)


SPECIAL_COLUMN_NAMES = {
    "TransactionID": "transaction_id",
    "CustomerID": "customer_id",
    "AccountID": "account_id",
    "DeviceID": "device_id",
    "TransactionDT": "transaction_dt",
    "TransactionAmt": "transaction_amt",
    "isFraud": "is_fraud",
    "ProductCD": "product_cd",
}


def postgres_column_name(csv_column):

    if csv_column in SPECIAL_COLUMN_NAMES:
        return SPECIAL_COLUMN_NAMES[csv_column]

    return csv_column.lower()


def read_csv_columns():

    dataframe = pd.read_csv(
        TRANSACTION_FILE,
        nrows=0,
    )

    return dataframe.columns.tolist()


def read_postgres_columns():
    """
    Ask PostgreSQL for every column in the transaction table.

    -A = unaligned output
    -t = tuples only
    """

    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'transaction'
        ORDER BY ordinal_position;
    """

    command = [
        "psql",
        "-U",
        "fraud_app",
        "-d",
        "fraud_risk_db",
        "-h",
        "localhost",
        "-A",
        "-t",
        "-c",
        sql,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    columns = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    return columns


def verify_schema(
    csv_columns,
    postgres_columns,
):

    expected_postgres_columns = [
        postgres_column_name(column)
        for column in csv_columns
    ]

    csv_count = len(
        csv_columns
    )

    expected_count = len(
        expected_postgres_columns
    )

    postgres_count = len(
        postgres_columns
    )

    duplicate_expected = (
        len(
            set(
                expected_postgres_columns
            )
        )
        != expected_count
    )

    postgres_column_set = set(
        postgres_columns
    )

    expected_column_set = set(
        expected_postgres_columns
    )

    missing_in_postgres = sorted(
        expected_column_set
        - postgres_column_set
    )

    extra_in_postgres = sorted(
        postgres_column_set
        - expected_column_set
    )

    print("\n" + "=" * 70)
    print("TRANSACTION SCHEMA VERIFICATION")
    print("=" * 70)

    print(
        f"\nCSV columns: {csv_count}"
    )

    print(
        "Mapped PostgreSQL columns: "
        f"{expected_count}"
    )

    print(
        "Actual PostgreSQL columns: "
        f"{postgres_count}"
    )

    print(
        "\nDuplicate mapped column names: "
        f"{duplicate_expected}"
    )

    print(
        "\nMissing in PostgreSQL:"
    )

    if missing_in_postgres:

        for column in missing_in_postgres:
            print(
                f"  {column}"
            )

    else:

        print(
            "  None"
        )

    print(
        "\nExtra in PostgreSQL:"
    )

    if extra_in_postgres:

        for column in extra_in_postgres:
            print(
                f"  {column}"
            )

    else:

        print(
            "  None"
        )

    passed = (
        csv_count == expected_count
        and expected_count == postgres_count
        and not duplicate_expected
        and not missing_in_postgres
        and not extra_in_postgres
    )

    print("\n" + "=" * 70)

    if passed:

        print(
            "RESULT: PASS"
        )

        print(
            "All CSV columns map to existing "
            "PostgreSQL transaction columns."
        )

    else:

        print(
            "RESULT: FAIL"
        )

        print(
            "Do not load transaction.csv."
        )

    print("=" * 70)

    return passed


def main():

    if not TRANSACTION_FILE.exists():

        raise FileNotFoundError(
            f"Transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    csv_columns = (
        read_csv_columns()
    )

    postgres_columns = (
        read_postgres_columns()
    )

    passed = verify_schema(
        csv_columns,
        postgres_columns,
    )

    if not passed:

        raise SystemExit(1)


if __name__ == "__main__":
    main()