from pathlib import Path

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRANSACTION_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "final"
    / "transaction.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "schema"
    / "load_transaction.sql"
)


# ============================================================
# 2. SPECIAL CSV -> POSTGRESQL COLUMN NAMES
# ============================================================

# Most IEEE-CIS columns only need lowercase conversion.
#
# However, the core relational/source columns were defined
# using snake_case names in PostgreSQL, so these fields need
# explicit mappings.

SPECIAL_COLUMN_NAMES = {
    "TransactionID": "transaction_id",
    "CustomerID": "customer_id",
    "AccountID": "account_id",
    "DeviceID": "device_id",
    "isFraud": "is_fraud",
    "TransactionDT": "transaction_dt",
    "TransactionAmt": "transaction_amt",
    "ProductCD": "product_cd",
}


# ============================================================
# 3. CONVERT CSV COLUMN NAME TO POSTGRESQL COLUMN NAME
# ============================================================

def postgres_column_name(csv_column):
    """
    Convert one transaction.csv column name into the
    corresponding PostgreSQL transaction-table column.

    Examples:

        TransactionID -> transaction_id
        CustomerID    -> customer_id
        isFraud       -> is_fraud
        C1            -> c1
        D10           -> d10
        M4            -> m4
        V339          -> v339
    """

    if csv_column in SPECIAL_COLUMN_NAMES:
        return SPECIAL_COLUMN_NAMES[csv_column]

    return csv_column.lower()


# ============================================================
# 4. READ THE ACTUAL CSV HEADER
# ============================================================

def read_csv_columns():
    """
    Read only the transaction.csv header.

    nrows=0 means pandas reads the column names without
    loading the 590,540 transaction rows into memory.
    """

    if not TRANSACTION_FILE.exists():
        raise FileNotFoundError(
            "Transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    dataframe = pd.read_csv(
        TRANSACTION_FILE,
        nrows=0,
    )

    return dataframe.columns.tolist()


# ============================================================
# 5. BUILD POSTGRESQL COLUMN LIST
# ============================================================

def build_postgres_columns(csv_columns):
    """
    Convert every CSV column into the PostgreSQL column name
    that should receive that field.
    """

    postgres_columns = []

    for csv_column in csv_columns:

        database_column = postgres_column_name(
            csv_column
        )

        postgres_columns.append(
            database_column
        )

    return postgres_columns


# ============================================================
# 6. SAFETY CHECKS
# ============================================================

def run_checks(
    csv_columns,
    postgres_columns,
):
    """
    Perform basic mapping checks before generating SQL.

    These checks do not query PostgreSQL itself.

    The separate verify_transaction_schema.py script performs
    the database-side verification.
    """

    # Every CSV column must produce exactly one target column.
    if len(csv_columns) != len(postgres_columns):

        raise ValueError(
            "CSV and PostgreSQL target column counts "
            "do not match."
        )

    # Mapping must not accidentally produce duplicate
    # PostgreSQL column names.
    if len(postgres_columns) != len(
        set(postgres_columns)
    ):

        duplicates = sorted(
            {
                column
                for column in postgres_columns
                if postgres_columns.count(column) > 1
            }
        )

        raise ValueError(
            "Duplicate PostgreSQL column names "
            f"were generated: {duplicates}"
        )

    # Empty header would indicate an invalid input file.
    if len(csv_columns) == 0:

        raise ValueError(
            "transaction.csv contains no columns."
        )

    print(
        "Header mapping safety checks passed."
    )


# ============================================================
# 7. GENERATE THE TRANSACTION LOAD SQL
# ============================================================

def generate_sql(
    csv_columns,
    postgres_columns,
):
    """
    Generate one psql \\copy command.

    IMPORTANT:

    The PostgreSQL target columns are written in the exact
    order of the CSV fields.

    This means PostgreSQL's physical table-column order does
    not need to match transaction.csv.
    """

    # Create one comma-separated list:
    #
    # transaction_id, customer_id, account_id, ...
    #
    # Keeping the psql \copy command on one line avoids
    # problems with multi-line psql meta-command parsing.

    columns_sql = ", ".join(
        postgres_columns
    )

    csv_path = str(
        TRANSACTION_FILE
    )

    sql = f"""-- ============================================================
-- Load Validated Version 1 Transaction Data
-- ============================================================
--
-- Generated automatically from the actual transaction.csv
-- header.
--
-- The target column list follows the CSV field order.
-- This protects the import from differences between CSV order
-- and the PostgreSQL table's physical column order.
--
-- CSV columns: {len(csv_columns)}
-- PostgreSQL target columns: {len(postgres_columns)}
--
-- Expected transaction population: 590540 rows
--
-- This loader must only be executed when the transaction table
-- is empty.
--
-- ============================================================

\\copy transaction ({columns_sql}) FROM '{csv_path}' WITH (FORMAT csv, HEADER true)
"""

    return sql


# ============================================================
# 8. WRITE GENERATED SQL
# ============================================================

def write_output(sql):
    """
    Save the generated loader to:

        schema/load_transaction.sql
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        sql,
        encoding="utf-8",
    )

    print(
        "\nGenerated loader:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# 9. PRINT SAMPLE COLUMN MAPPINGS
# ============================================================

def print_mapping_sample(
    csv_columns,
    postgres_columns,
):
    """
    Print the beginning and end of the mapping so we can
    visually sanity-check important columns.
    """

    print(
        "\nFirst 12 column mappings:"
    )

    first_count = min(
        12,
        len(csv_columns),
    )

    for index in range(
        first_count
    ):

        print(
            f"{index + 1}: "
            f"{csv_columns[index]} "
            f"-> "
            f"{postgres_columns[index]}"
        )

    print(
        "\nLast 7 column mappings:"
    )

    start_index = max(
        0,
        len(csv_columns) - 7,
    )

    for index in range(
        start_index,
        len(csv_columns),
    ):

        print(
            f"{index + 1}: "
            f"{csv_columns[index]} "
            f"-> "
            f"{postgres_columns[index]}"
        )


# ============================================================
# 10. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 70)
    print("GENERATE TRANSACTION POSTGRESQL LOADER")
    print("=" * 70)

    print(
        "\nStep 1: Reading transaction.csv header..."
    )

    csv_columns = read_csv_columns()

    print(
        f"CSV columns found: {len(csv_columns)}"
    )

    print(
        "\nStep 2: Mapping CSV names "
        "to PostgreSQL names..."
    )

    postgres_columns = (
        build_postgres_columns(
            csv_columns
        )
    )

    print(
        "\nStep 3: Running mapping safety checks..."
    )

    run_checks(
        csv_columns,
        postgres_columns,
    )

    print(
        "\nStep 4: Generating psql loader..."
    )

    sql = generate_sql(
        csv_columns,
        postgres_columns,
    )

    print(
        "\nStep 5: Saving loader..."
    )

    write_output(
        sql
    )

    print_mapping_sample(
        csv_columns,
        postgres_columns,
    )

    print(
        "\nCSV columns: "
        f"{len(csv_columns)}"
    )

    print(
        "PostgreSQL target columns: "
        f"{len(postgres_columns)}"
    )

    print(
        "\nNo transaction data were loaded."
    )

    print(
        "PostgreSQL was not modified."
    )

    print("\n" + "=" * 70)
    print("TRANSACTION LOADER GENERATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()