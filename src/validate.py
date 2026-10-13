import csv
import io
import re

EXPECTED_HEADER = [
    "table_name", "column_name", "business_meaning", "data_type", "mandatory",
    "expected_values", "documented_rules", "inferred_rules",
    "is_business_key", "is_metadata", "source_table", "source_column",
]

CITATION = re.compile(r"\s*\[\[\d+\]\]")

HEADER_LINE = ",".join(EXPECTED_HEADER)


def clean_csv(csv_text: str) -> str:
    """Remove citation markers, swap special symbols for ASCII,
    and add the header row if the agent left it out."""
    text = CITATION.sub("", csv_text)
    text = text.replace("≥", ">=").replace("≤", "<=").strip()
    text = re.sub(r'"\s*,\s*"', '","', text)   # remove spaces around separators
    first_line = text.splitlines()[0] if text else ""
    if not first_line.replace('"', "").startswith("table_name"):
        text = HEADER_LINE + "\n" + text
    return text


def validate_dictionary_csv(csv_text: str, expected_table: str,
                            expected_columns: list[str], known_columns: set[str]) -> list[str]:
    """Return a list of problems. An empty list means the CSV is valid."""
    errors = []
    rows = list(csv.reader(io.StringIO(csv_text)))



    if not rows:
        return ["CSV is empty"]

    # 1. Header must match exactly
    if rows[0] != EXPECTED_HEADER:
        errors.append("The first line must be exactly this header: " + ",".join(EXPECTED_HEADER))

    data = rows[1:]
    seen_columns = []

    for i, row in enumerate(data, start=2):          # line 2 = first data row
        # 2. Exactly 12 fields per row
        if len(row) != 12:
            errors.append(f"Line {i}: {len(row)} fields instead of 12 -> {row[:2]}")
            continue
        table_name, column_name = row[0], row[1]
        if len(row) >= 2:
            seen_columns.append(row[1])              # record the column first
        if len(row) != 12:
            errors.append(f"Line {i}: {len(row)} fields instead of 12 -> {row[:2]}")
            continue
        table_name, column_name = row[0], row[1]

        # 3. Exact table name on every row
        if table_name != expected_table:
            errors.append(f"Line {i}: table_name '{table_name}' should be '{expected_table}'")

        # 4. Y/N fields must be Y or N
        for field, value in (("mandatory", row[4]), ("is_business_key", row[8]), ("is_metadata", row[9])):
            if value not in ("Y", "N"):
                errors.append(f"Line {i}: {field} is '{value}', must be Y or N")

                # 5. Source mapping must exist in Synapse (both empty is fine: surrogate keys)
        src_table, src_col = row[10], row[11]
        if src_table or src_col:
            if f"{src_table}.{src_col}".lower() not in known_columns:
                errors.append(f"Line {i}: source '{src_table}.{src_col}' does not exist in Synapse")

    # 5. Every real column present, no invented ones
    missing = set(expected_columns) - set(seen_columns)
    extra = set(seen_columns) - set(expected_columns)
    if missing:
        errors.append(f"Missing columns: {sorted(missing)}")
    if extra:
        errors.append(f"Columns not in the table: {sorted(extra)}")

    return errors