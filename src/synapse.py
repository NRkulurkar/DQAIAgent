import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={os.getenv('SYNAPSE_SERVER')};"
        f"DATABASE={os.getenv('SYNAPSE_DB')};"
        f"UID={os.getenv('SYNAPSE_USER')};"
        f"PWD={os.getenv('SYNAPSE_PASSWORD')};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def get_columns(schema: str, table: str) -> str:
    """Return the column list as 'Col (type), Col (type), ...'."""
    sql = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """
    with get_connection() as conn:
        rows = conn.cursor().execute(sql, schema, table).fetchall()
    return ", ".join(f"{r.COLUMN_NAME} ({r.DATA_TYPE})" for r in rows)

def load_dictionary(table_name: str, file_url: str) -> int:
    """Replace one table's rows in dq.data_dictionary with the CSV at file_url.
    Returns the number of rows loaded."""
    with get_connection() as conn:
        cur = conn.cursor()

        # 1. Remove this table's old rows (so reloads never create duplicates)
        cur.execute("DELETE FROM dq.data_dictionary WHERE table_name = ?", table_name)

        # 2. Load the new file
        cur.execute(f"""
            COPY INTO dq.data_dictionary
            FROM '{file_url}'
            WITH (FILE_TYPE = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', ENCODING = 'UTF8',
                  CREDENTIAL = (IDENTITY = 'Managed Identity'))
        """)

        # 3. Confirm what was loaded
        count = cur.execute(
            "SELECT COUNT(*) FROM dq.data_dictionary WHERE table_name = ?", table_name
        ).fetchone()[0]
    return count

if __name__ == "__main__":
    print(get_columns("pres", "DimSavingsAccount"))