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
    / "source_columns.sql"
)


# ============================================================
# 2. COLUMNS ALREADY DEFINED IN schema.sql
# ============================================================

TRANSACTION_EXISTING_COLUMNS = {
    "transactionid",
    "customerid",
    "accountid",
    "deviceid",
    "transactiondt",
    "transactionamt",
    "isfraud",
    "productcd",
    "card1",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
    "addr1",
    "addr2",
    "dist1",
    "dist2",
    "p_emaildomain",
    "r_emaildomain",
}


IDENTITY_EXISTING_COLUMNS = {
    "transactionid",
    "devicetype",
    "deviceinfo",
}


# ============================================================
# 3. NORMALIZE COLUMN NAME
# ============================================================

def normalize_column_name(column):
    """
    Convert source column names to lowercase PostgreSQL
    column names.

    Examples:

    C1 -> c1
    V339 -> v339
    id_01 -> id_01
    """

    return column.lower()


# ============================================================
# 4. MAP PANDAS TYPE TO POSTGRESQL TYPE
# ============================================================

def pandas_dtype_to_postgres(dtype):
    """
    Translate observed pandas data types into conservative
    PostgreSQL data types.
    """

    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"

    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"

    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"

    return "TEXT"


# ============================================================
# 5. READ ACTUAL CSV DATA TYPES
# ============================================================

def read_observed_dtypes(csv_file):
    """
    Read the final validated CSV and return the observed
    pandas data types.

    Reading the actual final CSV means the SQL definitions
    are based on our real generated dataset.
    """

    print(f"\nReading: {csv_file}")

    data = pd.read_csv(
        csv_file,
        low_memory=False,
    )

    print(
        f"Rows: {len(data):,}"
    )

    print(
        f"Columns: {len(data.columns):,}"
    )

    return data.dtypes


# ============================================================
# 6. BUILD SQL STATEMENTS
# ============================================================

def build_alter_statements(
    table_name,
    dtypes,
    existing_columns,
):
    """
    Create ALTER TABLE statements for source columns that
    are not already defined in schema/schema.sql.
    """

    statements = []

    for original_column, dtype in dtypes.items():

        normalized_column = (
            normalize_column_name(
                original_column
            )
        )

        if normalized_column in existing_columns:
            continue

        postgres_type = (
            pandas_dtype_to_postgres(
                dtype
            )
        )

        statement = (
            f"ALTER TABLE {table_name}\n"
            f"    ADD COLUMN IF NOT EXISTS "
            f"{normalized_column} "
            f"{postgres_type};"
        )

        statements.append(
            statement
        )

    return statements


# ============================================================
# 7. WRITE source_columns.sql
# ============================================================

def write_sql(
    transaction_statements,
    identity_statements,
):
    """
    Write the generated PostgreSQL statements into
    schema/source_columns.sql.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    sections = []

    sections.append(
        """-- ============================================================
-- IEEE-CIS Complete Source Columns
-- ============================================================
--
-- Generated from the validated Version 1 relational CSV files.
--
-- This file extends the core relational tables defined in:
--
-- schema/schema.sql
--
-- No data are loaded by this file.
-- ============================================================"""
    )

    sections.append(
        """-- ============================================================
-- TRANSACTION SOURCE COLUMNS
-- ============================================================"""
    )

    sections.extend(
        transaction_statements
    )

    sections.append(
        """-- ============================================================
-- TRANSACTION IDENTITY SOURCE COLUMNS
-- ============================================================"""
    )

    sections.extend(
        identity_statements
    )

    sections.append(
        """-- ============================================================
-- END OF GENERATED SOURCE COLUMN DEFINITIONS
-- ============================================================"""
    )

    OUTPUT_FILE.write_text(
        "\n\n".join(sections) + "\n",
        encoding="utf-8",
    )

    print(
        "\nGenerated SQL file:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# 8. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 70)

    print(
        "GENERATE POSTGRESQL SOURCE COLUMN DEFINITIONS"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Check required files
    # --------------------------------------------------------

    if not TRANSACTION_FILE.exists():

        raise FileNotFoundError(
            f"Transaction file not found:\n"
            f"{TRANSACTION_FILE}"
        )

    if not IDENTITY_FILE.exists():

        raise FileNotFoundError(
            f"Identity file not found:\n"
            f"{IDENTITY_FILE}"
        )

    # --------------------------------------------------------
    # Read actual dtypes
    # --------------------------------------------------------

    transaction_dtypes = (
        read_observed_dtypes(
            TRANSACTION_FILE
        )
    )

    identity_dtypes = (
        read_observed_dtypes(
            IDENTITY_FILE
        )
    )

    # --------------------------------------------------------
    # Generate additional transaction columns
    # --------------------------------------------------------

    transaction_statements = (
        build_alter_statements(
            "transaction",
            transaction_dtypes,
            TRANSACTION_EXISTING_COLUMNS,
        )
    )

    # --------------------------------------------------------
    # Generate additional identity columns
    # --------------------------------------------------------

    identity_statements = (
        build_alter_statements(
            "transaction_identity",
            identity_dtypes,
            IDENTITY_EXISTING_COLUMNS,
        )
    )

    # --------------------------------------------------------
    # Write SQL
    # --------------------------------------------------------

    write_sql(
        transaction_statements,
        identity_statements,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\nTransaction columns added: "
        f"{len(transaction_statements)}"
    )

    print(
        "Identity columns added: "
        f"{len(identity_statements)}"
    )

    print(
        "\nNo PostgreSQL data were loaded."
    )

    print(
        "No source CSV files were modified."
    )


if __name__ == "__main__":
    main()
