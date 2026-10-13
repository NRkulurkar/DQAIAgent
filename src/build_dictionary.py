import json
import os
import sys
from synapse import get_connection, get_columns, load_dictionary, get_known_columns, fill_references
from Agents import call_agent, extract_code_block
from validate import validate_dictionary_rows, rows_to_csv
from storage import upload_text

TABLES = [
    ("curate", "SavingsAccount"),
    ("pres", "DimSavingsAccount"),
    ("pres", "FactSavingsAccount"),
]
MAX_ATTEMPTS = 3


def column_names(schema: str, table: str) -> list[str]:
    with get_connection() as conn:
        rows = conn.cursor().execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?", schema, table).fetchall()
    return [r.COLUMN_NAME for r in rows]


def build_dictionary(schema: str, table: str) -> int:
    full_name = f"{schema}.{table}"
    cols = column_names(schema, table)
    if not cols:
        raise ValueError(f"{full_name} not found in Synapse")
    known = get_known_columns("curate")

    base_message = f"Table: {full_name}\nColumns: {get_columns(schema, table)}"
    message = base_message
    version = os.getenv("DICT_AGENT_VERSION")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  Attempt {attempt}: calling dictionary-builder...", flush=True)
        try:
            reply = call_agent("dictionary-builder", version, message)
            rows = json.loads(extract_code_block(reply))
            errors = validate_dictionary_rows(rows, full_name, cols, known)
        except Exception as e:          # timeout, no code block, invalid JSON
            reply, rows, errors = str(e), None, [f"No valid JSON array: {e}"]

        if not errors:
            print("  Valid.", flush=True)
            break

        print(f"  {len(errors)} problem(s), e.g. {errors[:2]}", flush=True)
        os.makedirs("dictionary", exist_ok=True)
        with open(f"dictionary/_rejected_{schema}_{table}_attempt{attempt}.json", "w", encoding="utf-8") as f:
            f.write(reply)
        message = (base_message
                   + "\n\nYour previous output had these problems. Return the full corrected JSON array:\n- "
                   + "\n- ".join(errors))
    else:
        raise ValueError(f"{full_name}: still invalid after {MAX_ATTEMPTS} attempts")

    csv_text = rows_to_csv(rows)
    file_name = f"{schema}_{table}.csv"
    with open(os.path.join("dictionary", file_name), "w", encoding="utf-8", newline="") as f:
        f.write(csv_text)

    url = upload_text(f"dictionary/{file_name}", csv_text)
    return load_dictionary(full_name, url)


if __name__ == "__main__":
    # One table:  python src/build_dictionary.py pres.DimSavingsAccount
    # All tables: python src/build_dictionary.py
    targets = [tuple(sys.argv[1].split(".", 1))] if len(sys.argv) > 1 else TABLES

    for schema, table in targets:
        print(f"\n{schema}.{table}")
        try:
            print(f"  Loaded {build_dictionary(schema, table)} rows into dq.data_dictionary")
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\nLinked {fill_references()} column(s) to their Dim tables")