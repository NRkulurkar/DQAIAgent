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
            (table_name, column_name, business_meaning, data_type, mandatory, expected_values,
             documented_rules, inferred_rules, is_business_key, is_metadata,
             source_table, source_column)
            FROM '{file_url}'
            WITH (FILE_TYPE = 'CSV', FIRSTROW = 2, FIELDQUOTE = '"', ENCODING = 'UTF8',
                  CREDENTIAL = (IDENTITY = 'Managed Identity'))
        """)

        # 3. Confirm what was loaded
        count = cur.execute(
            "SELECT COUNT(*) FROM dq.data_dictionary WHERE table_name = ?", table_name
        ).fetchone()[0]
    return count

def dry_run(rule_sql: str) -> str | None:
    """Return None if the SQL compiles and runs, else the error message."""
    try:
        with get_connection() as conn:
            conn.cursor().execute(f"SELECT COUNT(*) FROM ({rule_sql}) t WHERE 1 = 0").fetchone()
        return None
    except Exception as e:
        return str(e)[:300]
    
def get_dictionary_rows(table_name: str) -> str:
    """Dictionary rows for one table as pipe-separated text, one line per column."""
    sql = """
        SELECT CONCAT_WS(' | ', column_name, business_meaning, data_type, mandatory,
                         expected_values, documented_rules, inferred_rules,
                         is_business_key, is_metadata)
        FROM dq.data_dictionary
        WHERE table_name = ?
    """
    with get_connection() as conn:
        rows = conn.cursor().execute(sql, table_name).fetchall()
    return "\n".join(r[0] for r in rows)


def load_rules(table_name: str, prefix: str, rules: list[dict]) -> int:
    """Replace this table's Proposed rules in dq.rule_catalog. Returns rows loaded."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM dq.rule_catalog WHERE table_name = ? AND status = 'Proposed'",
                    table_name)
        for r in rules:
            cur.execute("""
                INSERT INTO dq.rule_catalog
                (rule_id, table_name, column_name, description, category, severity,
                 origin, rule_sql, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Proposed', GETDATE())
            """, prefix + r["rule_id"], r["table_name"], r.get("column_name"),
                 r["description"], r["category"], r["severity"], r["origin"], r["rule_sql"])
        return cur.execute(
            "SELECT COUNT(*) FROM dq.rule_catalog WHERE table_name = ? AND status = 'Proposed'",
            table_name).fetchone()[0]

def get_known_columns(schema: str = "curate") -> set[str]:
    """All columns in a schema as lowercase 'schema.table.column' strings."""
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = ?", schema).fetchall()
    return {f"{r[0]}.{r[1]}.{r[2]}".lower() for r in rows}
    
if __name__ == "__main__":
    print(get_columns("pres", "DimSavingsAccount"))