import json
import re


CATEGORIES = {"Completeness", "Domain & format", "Business-key duplicates", "Referential integrity",
              "Temporal & SCD", "Load metadata", "Conditional business rule"}
SEVERITIES = {"Critical", "High", "Warning"}
ORIGINS = {"Documented", "Standard", "Inferred"}
REQUIRED_KEYS = {"rule_id", "table_name", "description", "category", "severity", "origin", "rule_sql"}
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|CREATE|EXEC|EXECUTE|GRANT)\b", re.I)
TABLE_REF = re.compile(r"\b(curate|pres|dq)\.(\w+)", re.I)


def parse_rules(text: str) -> list[dict]:
    """Parse the agent's JSON array of rules."""
    rules = json.loads(text)
    if not isinstance(rules, list):
        raise ValueError("Output must be a JSON array of rules")
    return rules


def validate_rules(rules: list[dict], expected_table: str, allowed_tables: list[str]) -> list[str]:
    """Return a list of problems. Empty list = all rules valid."""
    errors, seen_ids = [], set()
    for r in rules:
        rid = r.get("rule_id", "?")
        missing = REQUIRED_KEYS - r.keys()
        if missing:
            errors.append(f"{rid}: missing fields {sorted(missing)}")
            continue
        if rid in seen_ids:
            errors.append(f"{rid}: duplicate rule_id")
        seen_ids.add(rid)
        if r["table_name"] != expected_table:
            errors.append(f"{rid}: table_name '{r['table_name']}' should be '{expected_table}'")
        if r["category"] not in CATEGORIES:
            errors.append(f"{rid}: category '{r['category']}' not allowed")
        if r["severity"] not in SEVERITIES:
            errors.append(f"{rid}: severity '{r['severity']}' not allowed")
        if r["origin"] not in ORIGINS:
            errors.append(f"{rid}: origin '{r['origin']}' not allowed")
        if r["origin"] == "Inferred" and r["severity"] != "Warning":
            errors.append(f"{rid}: inferred rules must have severity Warning")

        sql = r["rule_sql"].strip()
        if not sql.upper().startswith("SELECT"):
            errors.append(f"{rid}: rule_sql must start with SELECT")
        if ";" in sql:
            errors.append(f"{rid}: rule_sql must not contain semicolons")
        if FORBIDDEN.search(sql):
            errors.append(f"{rid}: rule_sql contains a forbidden keyword")

        allowed = {t.lower() for t in allowed_tables}
        for schema, table in TABLE_REF.findall(sql):
            if f"{schema}.{table}".lower() not in allowed:
                errors.append(f"{rid}: references unknown table '{schema}.{table}'")
    return errors