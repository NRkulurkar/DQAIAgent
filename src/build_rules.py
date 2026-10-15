import os
import re
import sys
import hashlib
from synapse import (get_dictionary_rows, get_dictionary_tables, get_references,
                     load_rules, dry_run, get_approved_descriptions,last_dictionary_hash, log_generation)
from Agents import call_agent
from validate_rules import parse_rules, validate_rules

MAX_ATTEMPTS = 3


def extract_json(text: str) -> str:
    match = re.search(r"```[a-zA-Z]*\s*\n(.*?)```", text, re.S)
    return (match.group(1) if match else text).strip()


def build_message(table_name: str) -> tuple[str, list[str], str]:
    """Message for the agent, the tables its rules may reference, and a fingerprint
    of the dictionary input (used to detect documentation changes)."""
    message = (f"Table: {table_name}\n"
               "Dictionary rows (column_name | business_meaning | data_type | mandatory | "
               "expected_values | documented_rules | inferred_rules | is_business_key | is_metadata):\n"
               f"{get_dictionary_rows(table_name)}")
    allowed = [table_name]

    refs = get_references(table_name)
    if refs:
        message += "\n\nRelated tables:"
        for col, ref_table, ref_col in refs:
            message += (f"\n- Join: {table_name}.{col} = {ref_table}.{ref_col}\n"
                        f"  Dictionary rows for {ref_table}:\n{get_dictionary_rows(ref_table)}")
            allowed.append(ref_table)

    # Fingerprint only the dictionary part, not the approved-rules list
    dictionary_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()

    approved = get_approved_descriptions(table_name)
    if approved:
        message += ("\n\nThese rules are already approved for this table:\n- "
                    + "\n- ".join(approved)
                    + "\n\nReturn ONLY rules that check something NOT already covered above. "
                      "If nothing new is needed, return an empty JSON array: []")

    return message, allowed, dictionary_hash


def build_rules(table_name: str, force: bool = False) -> tuple[int, int]:
    prefix = table_name.split(".", 1)[1] + "-"
    base_message, allowed, dictionary_hash = build_message(table_name)

    # Skip if the dictionary hasn't changed since the last generation
    if not force and dictionary_hash == last_dictionary_hash(table_name):
        print("  No dictionary change since last generation: nothing to do.")
        return 0, 0

    message = base_message
    version = os.getenv("RULE_AGENT_VERSION")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  Attempt {attempt}: calling rule-generator...", flush=True)
        try:
            reply = call_agent("rule-generator", version, message)
            rules = parse_rules(extract_json(reply))
            for r in rules:
                if r.get("origin") == "Inferred":
                    r["severity"] = "Warning"
            errors = validate_rules(rules, table_name, allowed)
        except Exception as e:
            reply, rules, errors = str(e), [], [f"No valid JSON array: {e}"]

        if not errors:
            for r in rules:
                err = dry_run(r["rule_sql"])
                if err:
                    errors.append(f"{r['rule_id']}: SQL does not run in Synapse: {err}")

        if not errors:
            print(f"  Valid: {len(rules)} rules.", flush=True)
            break

        print(f"  {len(errors)} problem(s), e.g. {errors[:2]}", flush=True)
        # Retry: same message as before, plus the problems to fix
        message = (base_message
                   + "\n\nYour previous output had these problems. Return the full corrected JSON array:\n- "
                   + "\n- ".join(errors))
    else:
        raise ValueError(f"{table_name}: still invalid after {MAX_ATTEMPTS} attempts")

    os.makedirs("rules", exist_ok=True)
    with open(f"rules/{table_name.replace('.', '_')}.json", "w", encoding="utf-8") as f:
        f.write(extract_json(reply))

    log_generation(table_name, dictionary_hash)
    return load_rules(table_name, prefix, rules)


if __name__ == "__main__":
    from synapse import has_reviewed_rules

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refresh = "--refresh" in sys.argv
    force = "--force" in sys.argv
    targets = args if args else get_dictionary_tables()

    for table_name in targets:
        print(f"\n{table_name}")
        if has_reviewed_rules(table_name) and not (refresh or force):
            print("  Skipped: already reviewed (use --refresh after a documentation change)")
            continue
        try:
            loaded, skipped = build_rules(table_name, force=force)
            print(f"  Loaded {loaded} Proposed rules ({skipped} skipped as already reviewed)")
        except Exception as e:
            print(f"  FAILED: {e}")