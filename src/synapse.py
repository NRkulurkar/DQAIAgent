import os
import pyodbc
from dotenv import load_dotenv
import re

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





def _normalize(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower())


def get_approved_descriptions(table_name: str) -> list[str]:
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT description FROM dq.rule_catalog WHERE table_name = ? AND status = 'Approved'",
            table_name).fetchall()
    return [r[0] for r in rows]


def load_rules(table_name: str, prefix: str, rules: list[dict]) -> tuple[int, int]:
    """Replace this table's Proposed rules. Never touches Approved/Rejected rules.
    Returns (rules loaded, rules skipped as duplicates of reviewed ones)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM dq.rule_catalog WHERE table_name = ? AND status = 'Proposed'",
                    table_name)

        # What's already been reviewed for this table
        reviewed = cur.execute(
            "SELECT rule_id, rule_sql FROM dq.rule_catalog WHERE table_name = ?",
            table_name).fetchall()
        reviewed_sql = {_normalize(r.rule_sql) for r in reviewed}

        # New IDs continue after the highest existing number, so they never clash
        numbers = [int(m.group(1)) for r in reviewed if (m := re.search(r"-R(\d+)$", r.rule_id))]
        next_no = max(numbers, default=0) + 1

        loaded = skipped = 0
        for r in rules:
            if _normalize(r["rule_sql"]) in reviewed_sql:
                skipped += 1
                continue
            cur.execute("""
                INSERT INTO dq.rule_catalog
                (rule_id, table_name, column_name, description, category, severity,
                 origin, rule_sql, status, created_at)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, 'Proposed', GETDATE()
            """, f"{prefix}R{next_no:03d}", r["table_name"], r.get("column_name"),
                 r["description"], r["category"], r["severity"], r["origin"], r["rule_sql"])
            next_no += 1
            loaded += 1
    return loaded, skipped

def has_reviewed_rules(table_name: str) -> bool:
    with get_connection() as conn:
        n = conn.cursor().execute(
            "SELECT COUNT(*) FROM dq.rule_catalog WHERE table_name = ? AND status IN ('Approved', 'Rejected')",
            table_name).fetchone()[0]
    return n > 0

def get_known_columns(schema: str = "curate") -> set[str]:
    """All columns in a schema as lowercase 'schema.table.column' strings."""
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = ?", schema).fetchall()
    return {f"{r[0]}.{r[1]}.{r[2]}".lower() for r in rows}

def fill_references() -> int:
    """Link Fact/Bridge columns to the Dim whose surrogate key has the same name.
    Returns the number of dictionary rows updated."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Each Dim's surrogate key = its first column, if it ends in SK
        dim_keys = cur.execute("""
            SELECT TABLE_SCHEMA + '.' + TABLE_NAME AS dim_table, COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'pres' AND TABLE_NAME LIKE 'Dim%'
              AND ORDINAL_POSITION = 1 AND COLUMN_NAME LIKE '%SK'
        """).fetchall()
        key_to_dim = {r.COLUMN_NAME: r.dim_table for r in dim_keys}

        # Clear old links, then set new ones (safe to rerun)
        cur.execute("UPDATE dq.data_dictionary SET references_table = NULL, references_column = NULL")

        updated = 0
        rows = cur.execute("""
            SELECT table_name, column_name FROM dq.data_dictionary
            WHERE table_name NOT LIKE 'pres.Dim%' AND column_name LIKE '%SK'
        """).fetchall()
        for r in rows:
            dim = key_to_dim.get(r.column_name)
            if dim:
                cur.execute("""
                    UPDATE dq.data_dictionary
                    SET references_table = ?, references_column = ?
                    WHERE table_name = ? AND column_name = ?
                """, dim, r.column_name, r.table_name, r.column_name)
                updated += 1
    return updated

def get_dictionary_tables() -> list[str]:
    """All tables that have dictionary rows."""
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT DISTINCT table_name FROM dq.data_dictionary").fetchall()
    return sorted(r[0] for r in rows)


def get_references(table_name: str) -> list[tuple]:
    """(column, referenced table, referenced column) links for one table."""
    with get_connection() as conn:
        return conn.cursor().execute("""
            SELECT column_name, references_table, references_column
            FROM dq.data_dictionary
            WHERE table_name = ? AND references_table IS NOT NULL
        """, table_name).fetchall()

def last_dictionary_hash(table_name: str) -> str | None:
    with get_connection() as conn:
        row = conn.cursor().execute("""
            SELECT TOP 1 dictionary_hash FROM dq.rule_generation_log
            WHERE table_name = ? ORDER BY generated_at DESC
        """, table_name).fetchone()
    return row[0] if row else None


def log_generation(table_name: str, dictionary_hash: str) -> None:
    with get_connection() as conn:
        conn.cursor().execute("""
            INSERT INTO dq.rule_generation_log (table_name, dictionary_hash, generated_at)
            SELECT ?, ?, GETDATE()
        """, table_name, dictionary_hash)
    
if __name__ == "__main__":
    print(get_columns("pres", "DimSavingsAccount"))