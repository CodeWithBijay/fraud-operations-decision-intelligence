from pathlib import Path

import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IDENTITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "generated"
    / "final"
    / "transaction_identity.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "schema"
    / "load_transaction_identity.sql"
)


# ============================================================
# 2. SPECIAL CSV -> POSTGRESQL NAMES
# ============================================================

SPECIAL_COLUMN_NAMES = {
    "TransactionID": "transaction_id",
    "DeviceType": "device_type",
    "DeviceInfo": "device_info",
}


# ============================================================
# 3. MAP COLUMN NAME
# ============================================================

def postgres_column_name(csv_column):
    """
    Convert a CSV column name to its PostgreSQL column name.

    Examples:

    TransactionID -> transaction_id
    id_01         -> id_01
    DeviceType    -> device_type
    DeviceInfo    -> device_info
    """

    if csv_column in SPECIAL_COLUMN_NAMES:
        return SPECIAL_COLUMN_NAMES[csv_column]

    return csv_column.lower()


# ============================================================
# 4. READ CSV HEADER
# ============================================================

def read_csv_columns():
    """
    Read only the CSV header.

    nrows=0 prevents loading the 144,233 identity records.
    """

    if not IDENTITY_FILE.exists():
        raise FileNotFoundError(
            "Identity file not found:\n"
            f"{IDENTITY_FILE}"
        )

    dataframe = pd.read_csv(
        IDENTITY_FILE,
        nrows=0,
    )

    return dataframe.columns.tolist()


# ============================================================
# 5. BUILD POSTGRESQL COLUMN LIST
# ============================================================

def build_postgres_columns(csv_columns):

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

    if len(csv_columns) == 0:
        raise ValueError(
            "Identity CSV contains no columns."
        )

    if len(csv_columns) != len(postgres_columns):
        raise ValueError(
            "CSV and PostgreSQL target "
            "column counts do not match."
        )

    if len(postgres_columns) != len(
        set(postgres_columns)
    ):
        raise ValueError(
            "Duplicate PostgreSQL column names "
            "were generated."
        )

    print(
        "Header mapping safety checks passed."
    )


# ============================================================
# 7. GENERATE SQL
# ============================================================

def generate_sql(
    csv_columns,
    postgres_columns,
):
    """
    Generate a single-line psql \copy command.

    The PostgreSQL target list follows the exact CSV order.
    """

    columns_sql = ", ".join(
        postgres_columns
    )

    csv_path = str(
        IDENTITY_FILE
    )

    sql = f"""-- ============================================================
-- Load Validated Version 1 Transaction Identity Data
-- ============================================================
--
-- Generated from transaction_identity.csv.
--
-- CSV columns: {len(csv_columns)}
-- PostgreSQL target columns: {len(postgres_columns)}
--
-- Expected identity population: 144233 rows
--
-- Execute only when transaction_identity is empty.
--
-- ============================================================

\\copy transaction_identity ({columns_sql}) FROM '{csv_path}' WITH (FORMAT csv, HEADER true)
"""

    return sql


# ============================================================
# 8. WRITE OUTPUT
# ============================================================

def write_output(sql):

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
# 9. DISPLAY COLUMN MAPPINGS
# ============================================================

def print_mappings(
    csv_columns,
    postgres_columns,
):

    print(
        "\nIdentity column mappings:"
    )

    for index, (
        csv_column,
        postgres_column,
    ) in enumerate(
        zip(
            csv_columns,
            postgres_columns,
        ),
        start=1,
    ):

        print(
            f"{index}: "
            f"{csv_column} "
            f"-> "
            f"{postgres_column}"
        )


# ============================================================
# 10. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("GENERATE TRANSACTION IDENTITY LOADER")
    print("=" * 70)

    print(
        "\nStep 1: Reading identity CSV header..."
    )

    csv_columns = read_csv_columns()

    print(
        f"CSV columns found: {len(csv_columns)}"
    )

    print(
        "\nStep 2: Mapping column names..."
    )

    postgres_columns = (
        build_postgres_columns(
            csv_columns
        )
    )

    print(
        "\nStep 3: Running safety checks..."
    )

    run_checks(
        csv_columns,
        postgres_columns,
    )

    print(
        "\nStep 4: Generating loader..."
    )

    sql = generate_sql(
        csv_columns,
        postgres_columns,
    )

    write_output(
        sql
    )

    print_mappings(
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
        "\nNo identity data were loaded."
    )

    print(
        "PostgreSQL was not modified."
    )

    print("\n" + "=" * 70)
    print("IDENTITY LOADER GENERATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()