import os
import sys
from synapse import get_connection, get_columns, load_dictionary
from Agents import call_agent, extract_code_block
from validate import clean_csv, validate_dictionary_csv
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

    base_message = f"Table: {full_name}\nColumns: {get_columns(schema, table)}"
    message = base_message
    version = os.getenv("DICT_AGENT_VERSION")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  Attempt {attempt}: calling dictionary-builder...", flush=True)
        reply = call_agent("dictionary-builder", version, message)
        try:
            csv_text = clean_csv(extract_code_block(reply))
            errors = validate_dictionary_csv(csv_text, full_name, cols)
        except ValueError as e:
            errors = [str(e)]

        if not errors:
            print("  Valid.", flush=True)
            break

        print(f"  {len(errors)} problem(s), e.g. {errors[:2]}", flush=True)
        # Send the problems back so the agent can correct its own output
        message = (base_message
                   + "\n\nYour previous CSV had these problems. Return the full corrected CSV:\n- "
                   + "\n- ".join(errors))
    else:
        raise ValueError(f"{full_name}: still invalid after {MAX_ATTEMPTS} attempts")

    # Save a local copy (for Git and review)
    file_name = f"{schema}_{table}.csv"
    os.makedirs("dictionary", exist_ok=True)
    with open(os.path.join("dictionary", file_name), "w", encoding="utf-8", newline="") as f:
        f.write(csv_text + "\n")

    # Upload and load
    url = upload_text(f"dictionary/{file_name}", csv_text + "\n")
    return load_dictionary(full_name, url)


if __name__ == "__main__":
    # Run for one table:  python src/build_dictionary.py pres.DimSavingsAccount
    # Run for all tables: python src/build_dictionary.py
    if len(sys.argv) > 1:
        targets = [tuple(sys.argv[1].split(".", 1))]
    else:
        targets = TABLES

    for schema, table in targets:
        print(f"\n{schema}.{table}")
        try:
            rows = build_dictionary(schema, table)
            print(f"  Loaded {rows} rows into dq.data_dictionary")
        except Exception as e:
            print(f"  FAILED: {e}")