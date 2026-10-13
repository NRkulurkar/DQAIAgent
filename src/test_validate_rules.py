from validate_rules import parse_rules, validate_rules
from synapse import dry_run

with open("docs/Dictionary/rules/DimSavingsAccount.json", encoding="utf-8") as f:
    rules = parse_rules(f.read())

problems = validate_rules(rules, "pres.DimSavingsAccount")
print("Checks:", "OK" if not problems else "\n  " + "\n  ".join(problems))

for r in rules:
    err = dry_run(r["rule_sql"])
    print(f"{r['rule_id']}: {'OK' if not err else 'SQL ERROR - ' + err}")