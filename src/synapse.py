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


if __name__ == "__main__":
    print(get_columns("pres", "DimSavingsAccount"))