from synapse import get_connection
from validate import clean_csv, validate_dictionary_csv

with get_connection() as conn:
    cols = [r.COLUMN_NAME for r in conn.cursor().execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = 'pres' AND TABLE_NAME = 'DimSavingsAccount'").fetchall()]

with open("dictionary/DimSavingsAccount.csv", encoding="utf-8") as f:
    text = clean_csv(f.read())

problems = validate_dictionary_csv(text, "pres.DimSavingsAccount", cols)
print("VALID" if not problems else "\n".join(problems))